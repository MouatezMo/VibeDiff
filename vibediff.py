#!/usr/bin/env python3
"""
VibeDiff 0.3.1 - Precision Version Tracker for Termux & Linux
Live search in visual diff, q = full exit, b = back, unified (y/n) confirms.
"""

import os
import sys
import shutil
import hashlib
import json
import subprocess
import datetime
import difflib
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

try:
    import termios
    import tty
    import select
    _HAS_TTY = True
except Exception:
    _HAS_TTY = False

APP_VERSION = "0.3.1"
APP_NAME = "VibeDiff"
APP_TAGLINE = "Precision Version Tracker"

DEFAULT_STORAGE_ROOTS = [
    "/sdcard/VibeDiff",
    "/storage/emulated/0/VibeDiff",
    os.path.expanduser("~/VibeDiff"),
    os.path.expanduser("~/.vibediff"),
]

# =============================================================================
# CONTROL FLOW
# =============================================================================

class VibeQuit(Exception):
    """Global quit: exit the whole tool."""

class VibeBack(Exception):
    """Global back: return one level."""

# =============================================================================
# COLORS
# =============================================================================

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    ROW_DEL = "\033[48;2;46;27;30m"
    ROW_ADD = "\033[48;2;27;42;32m"
    SEG_DEL = "\033[48;2;102;44;50m"
    SEG_ADD = "\033[48;2;40;84;50m"

ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def visible_len(s: str) -> int:
    return len(ANSI_RE.sub('', s))

def get_terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80

def truncate_to_width(text: str, max_width: int) -> str:
    if visible_len(text) <= max_width:
        return text
    out = []
    vis = 0
    i = 0
    limit = max_width - 1
    while i < len(text) and vis < limit:
        m = ANSI_RE.match(text, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        out.append(text[i])
        vis += 1
        i += 1
    out.append("…")
    out.append(C.RESET)
    return ''.join(out)

# =============================================================================
# UI
# =============================================================================

class UI:
    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def gap():
        print()

    @staticmethod
    def banner():
        width = min(get_terminal_width(), 80)
        if width < 40:
            print(f"{C.BRIGHT_CYAN}═══ {C.BOLD}{APP_NAME}{C.RESET} {C.DIM}v{APP_VERSION}{C.RESET}")
            print(f"{C.DIM}{APP_TAGLINE}{C.RESET}")
            print()
            return
        name_line = f"{C.BOLD}{C.BRIGHT_CYAN}{APP_NAME}{C.RESET}"
        tag_line = f"{C.DIM}{APP_TAGLINE}{C.RESET}"
        name_pad = max(1, (width - len(APP_NAME) - 2) // 2)
        tag_pad = max(1, (width - len(APP_TAGLINE) - 2) // 2)
        print(f"{C.BRIGHT_CYAN}╭{'─' * (width - 2)}╮{C.RESET}")
        print(f"{C.BRIGHT_CYAN}│{C.RESET}{' ' * name_pad}{name_line}{' ' * max(1, width - name_pad - len(APP_NAME) - 2)}{C.BRIGHT_CYAN}│{C.RESET}")
        print(f"{C.BRIGHT_CYAN}│{C.RESET}{' ' * tag_pad}{tag_line}{' ' * max(1, width - tag_pad - len(APP_TAGLINE) - 2)}{C.BRIGHT_CYAN}│{C.RESET}")
        print(f"{C.BRIGHT_CYAN}╰{'─' * (width - 2)}╯{C.RESET}")
        print()

    @staticmethod
    def section(title: str):
        width = min(get_terminal_width(), 80)
        title_len = min(len(title), width - 4)
        print(f"\n{C.BOLD}{C.BRIGHT_WHITE}{title[:title_len]}{C.RESET}")
        print(f"{C.DIM}{'─' * title_len}{C.RESET}")

    @staticmethod
    def success(msg: str):
        print(f"  {C.GREEN}✓{C.RESET} {msg}")

    @staticmethod
    def error(msg: str):
        print(f"  {C.RED}✗{C.RESET} {msg}")

    @staticmethod
    def warning(msg: str):
        print(f"  {C.YELLOW}⚠{C.RESET} {msg}")

    @staticmethod
    def info(msg: str):
        print(f"  {C.BLUE}ℹ{C.RESET} {msg}")

    @staticmethod
    def kv(label: str, value: str, indent: int = 2):
        print(f"{' ' * indent}{C.BRIGHT_CYAN}{label}:{C.RESET} {value}")

    @staticmethod
    def _raw_input() -> str:
        try:
            return input(f"{C.BRIGHT_CYAN}> {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raise VibeQuit()

    @staticmethod
    def prompt(text: str) -> str:
        """Text input. 'q' quits the tool, 'b' goes back one level."""
        print(f"\n{text}")
        val = UI._raw_input()
        if val.lower() == 'q':
            raise VibeQuit()
        if val.lower() == 'b':
            raise VibeBack()
        return val

    @staticmethod
    def confirm(text: str) -> bool:
        """Yes/No gate printed as '<text> (y/n)'. q is DISABLED here."""
        print(f"\n{text} (y/n)")
        while True:
            val = UI._raw_input_safe()
            if val is None:
                return False
            v = val.lower()
            if v in ('y', 'yes'):
                return True
            if v in ('n', 'no', 'b', 'back'):
                return False
            if v == 'q':
                UI.warning("Quit is disabled during critical operations. Answer y or n.")
                continue
            UI.warning("Please answer 'y' or 'n'.")

    @staticmethod
    def _raw_input_safe() -> Optional[str]:
        try:
            return input(f"{C.BRIGHT_CYAN}> {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None

    @staticmethod
    def menu(title: str, options: List[Tuple[str, str]], allow_back: bool = True) -> int:
        width = get_terminal_width()
        print(f"\n{C.BOLD}{title}{C.RESET}\n")
        for i, (key, desc) in enumerate(options, 1):
            print(f"  {C.BRIGHT_CYAN}[{i}]{C.RESET} {C.BOLD}{key}{C.RESET}")
            if desc:
                print(f"      {C.DIM}{truncate_to_width(desc, max(20, width - 8))}{C.RESET}")
        print()
        while True:
            choice = UI._raw_input()
            lc = choice.lower()
            if lc == 'q':
                raise VibeQuit()
            if lc == 'b':
                if allow_back:
                    raise VibeBack()
                UI.warning("Nothing to go back to here.")
                continue
            try:
                idx = int(choice)
                if 1 <= idx <= len(options):
                    return idx
                UI.warning(f"Please enter a number between 1 and {len(options)}.")
            except ValueError:
                UI.warning("Please enter a valid number (or q/b).")

    @staticmethod
    def progress(label: str, current: int, total: int):
        pct = 100 if total == 0 else int((current / total) * 100)
        width = get_terminal_width()
        bar_max = max(8, min(40, width - 2 - 20 - 1 - 1 - 4 - 2))
        filled = int(bar_max * (1 if total == 0 else current / total))
        bar = f"{C.BRIGHT_CYAN}{'█' * filled}{C.DIM}{'░' * (bar_max - filled)}{C.RESET}"
        sys.stdout.write(f"\r  {label:<20} {bar} {pct:>3}%  \033[K")
        sys.stdout.flush()
        if total == 0 or current >= total:
            print()

    @staticmethod
    def pause(msg: str = "Press Enter to continue..."):
        try:
            input(f"\n{C.DIM}{msg}{C.RESET}")
        except (EOFError, KeyboardInterrupt):
            print()

# =============================================================================
# ENVIRONMENT MANAGER
# =============================================================================

class EnvironmentManager:
    def __init__(self):
        self.platform = self._detect_platform()
        self.has_rg = self._check_rg()
        self.storage_root = None

    def _detect_platform(self) -> str:
        if 'TERMUX_VERSION' in os.environ or 'com.termux' in os.environ.get('PREFIX', ''):
            return 'termux'
        if os.path.exists('/etc/debian_version'):
            return 'debian'
        if os.path.exists('/etc/os-release'):
            try:
                content = open('/etc/os-release').read().lower()
                for name in ('ubuntu', 'debian', 'arch', 'fedora'):
                    if name in content:
                        return name
            except Exception:
                pass
        if os.name == 'nt': return 'windows'
        if sys.platform == 'darwin': return 'macos'
        return 'unknown'

    def _check_rg(self) -> bool:
        try:
            subprocess.run(['rg', '--version'], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            return False

    def _get_rg_version(self) -> Optional[str]:
        try:
            out = subprocess.run(['rg', '--version'], capture_output=True, text=True, check=True)
            return out.stdout.split('\n')[0].replace('ripgrep ', '')
        except Exception:
            return None

    def _check_storage(self) -> bool:
        for root in DEFAULT_STORAGE_ROOTS:
            try:
                os.makedirs(root, exist_ok=True)
                t = os.path.join(root, '.vibediff_test')
                open(t, 'w').write('x')
                os.remove(t)
                self.storage_root = root
                return True
            except Exception:
                continue
        return False

    def _check_permissions(self) -> bool:
        try:
            return os.access(os.path.expanduser('~'), os.W_OK)
        except Exception:
            return False

    def check(self) -> Dict[str, Any]:
        return {
            'python': True,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
            'ripgrep': self.has_rg,
            'rg_version': self._get_rg_version() if self.has_rg else None,
            'platform': self.platform,
            'storage': self._check_storage(),
            'permissions': self._check_permissions(),
        }

    def display_check(self, check: Dict[str, Any]):
        UI.section("Environment check")
        print()
        UI.success(f"Python      {check['python_version']}") if check['python'] else UI.error("Python      not found")
        UI.success(f"ripgrep     {check['rg_version']}") if check['ripgrep'] else UI.error("ripgrep     not found")
        UI.success(f"Platform    {check['platform'].title()}")
        UI.success(f"Storage     {self.storage_root}") if check['storage'] else UI.error("Storage     not accessible")
        UI.success("Permissions OK") if check['permissions'] else UI.error("Permissions insufficient")
        print()

    def bootstrap(self) -> bool:
        check = self.check()
        self.display_check(check)
        if check['ripgrep'] and check['storage']:
            UI.success("Environment ready.")
            return True
        print(f"  {C.BOLD}VibeDiff needs:{C.RESET}")
        print("    • Python")
        print("    • ripgrep")
        if not check['storage']:
            UI.error("No writable storage found.")
            return False
        if not check['ripgrep']:
            UI.gap()
            if UI.confirm("Install ripgrep now?"):
                if self._install_rg():
                    self.has_rg = True
                    if self.check()['ripgrep']:
                        UI.gap()
                        UI.success("ripgrep installed successfully.")
                        UI.success("Environment ready.")
                        return True
        if not self.has_rg:
            UI.warning("Continuing without ripgrep. Python fallback scanner will be used.")
            return True
        return True

    def _install_rg(self) -> bool:
        try:
            if self.platform == 'termux':
                print(f"\n  {C.BOLD}Termux environment detected.{C.RESET}")
                print(f"  {C.DIM}$ pkg install -y ripgrep{C.RESET}")
                subprocess.run(['pkg', 'install', '-y', 'ripgrep'], check=True)
                return True
            if self.platform in ('debian', 'ubuntu'):
                print(f"\n  {C.BOLD}{self.platform.title()} detected.{C.RESET}")
                print(f"  {C.DIM}$ sudo apt update && sudo apt install -y ripgrep{C.RESET}")
                subprocess.run(['sudo', 'apt', 'update'], check=True)
                subprocess.run(['sudo', 'apt', 'install', '-y', 'ripgrep'], check=True)
                return True
            if self.platform == 'arch':
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'ripgrep'], check=True)
                return True
            if self.platform == 'fedora':
                subprocess.run(['sudo', 'dnf', 'install', '-y', 'ripgrep'], check=True)
                return True
            UI.warning(f"Auto-install not supported for {self.platform}.")
            print("  Install manually: https://github.com/BurntSushi/ripgrep")
        except Exception:
            UI.error("Failed to install ripgrep.")
        return False

# =============================================================================
# STORAGE MANAGER  (disk = source of truth)
# =============================================================================

class StorageManager:
    def __init__(self, root: str):
        self.root = Path(root)
        self.projects_dir = self.root / "Projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def project_path(self, name): return self.projects_dir / name
    def snapshots_path(self, name): return self.project_path(name) / "snapshots"
    def diffs_path(self, name): return self.project_path(name) / "diffs"
    def project_json(self, name): return self.project_path(name) / "project.json"
    def snapshot_path(self, name, v): return self.snapshots_path(name) / v
    def diff_file(self, name, a, b): return self.diffs_path(name) / f"{a}_to_{b}.txt"

    def list_projects(self) -> List[str]:
        if not self.projects_dir.exists():
            return []
        return sorted(p.name for p in self.projects_dir.iterdir()
                      if p.is_dir() and (p / "project.json").exists())

    def load_project_meta(self, name) -> Optional[Dict]:
        pj = self.project_json(name)
        if pj.exists():
            try:
                return json.load(open(pj))
            except Exception:
                pass
        return None

    def save_project_meta(self, name, meta):
        pj = self.project_json(name)
        pj.parent.mkdir(parents=True, exist_ok=True)
        tmp = pj.with_suffix('.tmp')
        json.dump(meta, open(tmp, 'w'), indent=2)
        tmp.replace(pj)

    @staticmethod
    def _version_key(v: str):
        parts = []
        for p in v.lstrip('v').split('.'):
            try: parts.append(int(p))
            except Exception: parts.append(0)
        return parts

    def list_snapshots(self, name) -> List[str]:
        sp = self.snapshots_path(name)
        if not sp.exists():
            return []
        return sorted((p.name for p in sp.iterdir() if p.is_dir()),
                      key=self._version_key)

    def snapshot_exists(self, name, v) -> bool:
        return self.snapshot_path(name, v).is_dir()

    @staticmethod
    def _dir_stats(path: Path) -> Tuple[int, int]:
        count = size = 0
        for p in path.rglob('*'):
            if p.is_file():
                count += 1
                try: size += p.stat().st_size
                except Exception: pass
        return count, size

    def reconcile(self, name: str) -> Dict:
        meta = self.load_project_meta(name) or {
            'name': name, 'source_path': '', 'created': datetime.datetime.now().isoformat(),
            'snapshots': []
        }
        disk = self.list_snapshots(name)
        kept, seen = [], set()
        for entry in meta.get('snapshots', []):
            v = entry.get('version')
            if v in disk and v not in seen:
                kept.append(entry)
                seen.add(v)
        changed = len(kept) != len(meta.get('snapshots', []))
        for v in disk:
            if v not in seen:
                cnt, size = self._dir_stats(self.snapshot_path(name, v))
                kept.append({'version': v, 'timestamp': datetime.datetime.fromtimestamp(
                    self.snapshot_path(name, v).stat().st_mtime).isoformat(),
                    'files': cnt, 'size': size, 'recovered': True})
                seen.add(v)
                changed = True
        kept.sort(key=lambda e: self._version_key(e['version']))
        for entry in kept:
            cnt, size = self._dir_stats(self.snapshot_path(name, entry['version']))
            if entry.get('files') is not None and (cnt != entry.get('files') or size != entry.get('size')):
                if entry.get('integrity') != 'mismatch':
                    entry['integrity'] = 'mismatch'
                    changed = True
            elif entry.get('integrity'):
                entry.pop('integrity', None)
                changed = True
        meta['snapshots'] = kept
        if changed:
            meta['updated'] = datetime.datetime.now().isoformat()
            self.save_project_meta(name, meta)
        return meta

    def delete_snapshot(self, name: str, version: str) -> int:
        sp = self.snapshot_path(name, version)
        if sp.exists():
            shutil.rmtree(sp, ignore_errors=True)
        meta = self.load_project_meta(name) or {}
        meta['snapshots'] = [s for s in meta.get('snapshots', []) if s.get('version') != version]
        self.save_project_meta(name, meta)
        removed = 0
        dp = self.diffs_path(name)
        if dp.exists():
            for f in list(dp.glob('*.txt')):
                parts = f.stem.split('_to_')
                if len(parts) == 2 and version in parts:
                    try:
                        f.unlink()
                        removed += 1
                    except Exception:
                        pass
        return removed

    def delete_project(self, name: str):
        shutil.rmtree(self.project_path(name), ignore_errors=True)

    def get_disk_usage(self):
        u = shutil.disk_usage(self.root)
        return {'total': u.total, 'used': u.used, 'free': u.free}

# =============================================================================
# SCANNER / HASHER
# =============================================================================

BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico', '.svg', '.tiff',
    '.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a',
    '.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv',
    '.zip', '.tar', '.gz', '.bz2', '.rar', '.7z', '.xz',
    '.exe', '.dll', '.so', '.dylib', '.bin', '.o', '.a', '.lib',
    '.apk', '.app', '.dmg', '.deb', '.rpm',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.sqlite', '.db', '.class', '.pyc', '.pyo',
    '.ttf', '.otf', '.woff', '.woff2', '.iso', '.img', '.rom', '.sav',
}

SKIP_DIRS = {
    '.git', '.svn', '.hg', '.bzr', 'node_modules', 'bower_components', 'vendor',
    '__pycache__', '.mypy_cache', '.pytest_cache', 'build', 'dist', 'target',
    'out', 'bin', 'obj', '.idea', '.vscode', '.vs', '.gradle', '.mvn', '.tox',
    'venv', 'env', '.venv', '.env', '.cache', 'cache', '.tmp', 'tmp', 'temp',
    'coverage', '.nyc_output',
}
SKIP_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}

class Scanner:
    def __init__(self, use_rg: bool = True):
        self.use_rg = use_rg and self._rg_available()

    @staticmethod
    def _rg_available() -> bool:
        try:
            subprocess.run(['rg', '--version'], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            return False

    def scan(self, project_path: str, on_progress=None) -> List[Path]:
        project = Path(project_path)
        if not project.exists():
            return []
        return self._scan_with_rg(project) if self.use_rg else self._scan_python(project, on_progress)

    def _scan_with_rg(self, project: Path) -> List[Path]:
        cmd = ['rg', '--files', '--hidden', '--no-ignore', str(project)]
        for d in SKIP_DIRS:
            cmd += ['-g', f'!{d}', '-g', f'!**/{d}/**']
        for f in SKIP_FILES:
            cmd += ['-g', f'!{f}']
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return [Path(l.strip()) for l in res.stdout.splitlines()
                    if l.strip() and Path(l.strip()).is_file()]
        except Exception:
            return self._scan_python(project)

    def _scan_python(self, project: Path, on_progress=None) -> List[Path]:
        files = []
        for root, dirs, names in os.walk(project):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for n in names:
                if n in SKIP_FILES:
                    continue
                fp = Path(root) / n
                if fp.is_file():
                    files.append(fp)
        return files

    @staticmethod
    def is_binary(path: Path) -> bool:
        if path.suffix.lower() in BINARY_EXTENSIONS:
            return True
        try:
            chunk = open(path, 'rb').read(8192)
            if b'\x00' in chunk:
                return True
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
            nontext = sum(1 for b in chunk if b not in text_chars)
            return len(chunk) > 0 and nontext / len(chunk) > 0.3
        except Exception:
            return True

class Hasher:
    @staticmethod
    def file_hash(path: Path, algorithm='sha256') -> Optional[str]:
        try:
            h = hashlib.new(algorithm)
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    @staticmethod
    def quick_compare(a: Path, b: Path) -> str:
        if not a.exists() or not b.exists():
            return 'CHANGED'
        try:
            sa, sb = a.stat().st_size, b.stat().st_size
        except OSError:
            return 'CHANGED'
        if sa != sb:
            return 'BINARY_CHANGED' if (Scanner.is_binary(a) or Scanner.is_binary(b)) else 'CHANGED'
        if Hasher.file_hash(a) == Hasher.file_hash(b):
            return 'UNCHANGED'
        return 'BINARY_CHANGED' if Scanner.is_binary(a) else 'CHANGED'

# =============================================================================
# DIFF ENGINE
# =============================================================================

@dataclass
class FileDiff:
    state: str
    path: str
    old_size: int = 0
    new_size: int = 0
    old_hash: str = ""
    new_hash: str = ""
    lines_added: int = 0
    lines_removed: int = 0
    diff_lines: List[str] = field(default_factory=list)
    is_binary: bool = False
    intra_line_changes: List[Dict] = field(default_factory=list)

@dataclass
class DiffResult:
    old_version: str
    new_version: str
    timestamp: str
    files: List[FileDiff] = field(default_factory=list)
    total_added: int = 0
    total_modified: int = 0
    total_deleted: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0

class DiffEngine:
    def compare(self, old_dir: Path, new_dir: Path, old_ver: str, new_ver: str,
                on_progress=None) -> DiffResult:
        result = DiffResult(old_ver, new_ver, datetime.datetime.now().isoformat())
        old_files = self._file_map(old_dir) if old_dir and old_dir.exists() else {}
        new_files = self._file_map(new_dir) if new_dir and new_dir.exists() else {}
        all_paths = sorted(set(old_files) | set(new_files))
        total = len(all_paths)

        for i, rel in enumerate(all_paths):
            if on_progress and total:
                on_progress(i, total)
            in_o, in_n = rel in old_files, rel in new_files

            if in_o and not in_n:
                op = old_files[rel]
                fd = FileDiff('DELETED', rel,
                              old_size=op.stat().st_size if op.exists() else 0,
                              old_hash=Hasher.file_hash(op) or "")
                fd.lines_removed = self._count_lines(op)
                fd.diff_lines = self._full_side_diff(op, 'del')
                result.files.append(fd)
                result.total_deleted += 1
                result.total_lines_removed += fd.lines_removed

            elif in_n and not in_o:
                np = new_files[rel]
                fd = FileDiff('ADDED', rel, new_size=np.stat().st_size,
                              new_hash=Hasher.file_hash(np) or "")
                fd.is_binary = Scanner.is_binary(np)
                if not fd.is_binary:
                    fd.lines_added = self._count_lines(np)
                    fd.diff_lines = self._full_side_diff(np, 'add')
                    result.total_lines_added += fd.lines_added
                result.files.append(fd)
                result.total_added += 1

            else:
                op, np = old_files[rel], new_files[rel]
                cmp = Hasher.quick_compare(op, np)
                if cmp == 'UNCHANGED':
                    continue
                if cmp == 'BINARY_CHANGED' or Scanner.is_binary(np):
                    fd = FileDiff('BINARY_MODIFIED', rel,
                                  old_size=op.stat().st_size, new_size=np.stat().st_size,
                                  old_hash=Hasher.file_hash(op) or "",
                                  new_hash=Hasher.file_hash(np) or "", is_binary=True)
                else:
                    fd = self._line_diff(rel, op, np)
                result.files.append(fd)
                result.total_modified += 1
                result.total_lines_added += fd.lines_added
                result.total_lines_removed += fd.lines_removed

        if on_progress and total:
            on_progress(total, total)
        return result

    def _file_map(self, directory: Path) -> Dict[str, Path]:
        files = {}
        for root, dirs, names in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for n in names:
                if n.startswith('.'):
                    continue
                fp = Path(root) / n
                files[str(fp.relative_to(directory))] = fp
        return files

    def _count_lines(self, p: Path) -> int:
        try:
            return sum(1 for _ in open(p, 'r', encoding='utf-8', errors='ignore'))
        except Exception:
            return 0

    def _full_side_diff(self, p: Path, kind: str) -> List[str]:
        out = []
        try:
            for line in open(p, 'r', encoding='utf-8', errors='ignore'):
                out.append(('+' if kind == 'add' else '-') + line.rstrip('\n'))
        except Exception:
            pass
        return out

    def _line_diff(self, rel: str, op: Path, np: Path) -> FileDiff:
        fd = FileDiff('MODIFIED', rel, old_size=op.stat().st_size, new_size=np.stat().st_size,
                      old_hash=Hasher.file_hash(op) or "", new_hash=Hasher.file_hash(np) or "")
        try:
            old_lines = open(op, 'r', encoding='utf-8', errors='ignore').readlines()
            new_lines = open(np, 'r', encoding='utf-8', errors='ignore').readlines()
        except Exception as e:
            fd.diff_lines = [f"[Error reading files: {e}]"]
            return fd

        diff = difflib.unified_diff(old_lines, new_lines,
                                    fromfile=f'a/{rel}', tofile=f'b/{rel}', lineterm='')
        added = removed = 0
        for line in diff:
            clean = line.rstrip('\n')
            if line.startswith('+') and not line.startswith('+++'):
                added += 1
            elif line.startswith('-') and not line.startswith('---'):
                removed += 1
            fd.diff_lines.append(clean)
        fd.lines_added = added
        fd.lines_removed = removed
        fd.intra_line_changes = self._intra_line(old_lines, new_lines)
        return fd

    def _intra_line(self, old_lines, new_lines) -> List[Dict]:
        changes = []
        sm = difflib.SequenceMatcher(None, old_lines, new_lines)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'replace':
                continue
            for oi, ni in zip(range(i1, i2), range(j1, j2)):
                ol = old_lines[oi] if oi < len(old_lines) else ""
                nl = new_lines[ni] if ni < len(new_lines) else ""
                changes.append({
                    'old_line_num': oi + 1, 'new_line_num': ni + 1,
                    'old_line': ol, 'new_line': nl,
                    'changes': self._char_diff(ol, nl),
                })
        return changes

    def _char_diff(self, ol: str, nl: str) -> List[Dict]:
        out = []
        sm = difflib.SequenceMatcher(None, ol, nl)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'equal':
                out.append({'type': tag, 'old_start': i1, 'old_end': i2,
                            'new_start': j1, 'new_end': j2,
                            'old_text': ol[i1:i2], 'new_text': nl[j1:j2]})
        return out

# =============================================================================
# REPORT GENERATOR
# =============================================================================

class ReportGenerator:
    @staticmethod
    def generate(result: DiffResult, output_path: Path):
        L = []
        W = 60
        L += ["═" * W, f"  {APP_NAME}", f"  {result.old_version}  →  {result.new_version}",
              f"  {result.timestamp}", "═" * W, ""]
        L += ["SUMMARY", "─" * 40,
              f"  Files changed:  {len(result.files)}",
              f"  Added:          {result.total_added} files",
              f"  Modified:       {result.total_modified} files",
              f"  Deleted:        {result.total_deleted} files", "",
              f"  Lines added:    +{result.total_lines_added}",
              f"  Lines removed:  -{result.total_lines_removed}",
              "═" * W, "", "CHANGED FILES", "─" * 40, ""]
        for state, mark in (('ADDED', '+'), ('MODIFIED', '~'), ('BINARY_MODIFIED', 'B'), ('DELETED', '-')):
            group = [f for f in result.files if f.state == state]
            if not group:
                continue
            L.append(f"  [{state}]")
            for fd in group:
                if state == 'MODIFIED':
                    L.append(f"    {mark} {fd.path}  +{fd.lines_added} -{fd.lines_removed}")
                elif state == 'BINARY_MODIFIED':
                    L.append(f"    [BINARY] {fd.path}")
                else:
                    L.append(f"    {mark} {fd.path}")
            L.append("")
        L += ["═" * W, "DETAILED CHANGES", "═" * W]
        for fd in result.files:
            L += ["", "─" * 60, f"FILE: {fd.path}", f"STATE: {fd.state}", "─" * 60]
            if fd.is_binary:
                L += [f"  Previous size: {ReportGenerator._fmt(fd.old_size)}",
                      f"  New size:      {ReportGenerator._fmt(fd.new_size)}",
                      f"  Hash changed:  yes"]
            else:
                L += fd.diff_lines
            L.append("")
        L += ["═" * W, "FINAL STATISTICS",
              f"  Total files in diff: {len(result.files)}",
              f"  Timestamp: {result.timestamp}", "═" * W]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(L) + '\n')

    @staticmethod
    def display_summary(result: DiffResult):
        W = min(get_terminal_width(), 60)
        print()
        print(f"{C.BRIGHT_CYAN}{'═' * W}{C.RESET}")
        print(f"{C.BRIGHT_CYAN}{C.BOLD}  {APP_NAME}{C.RESET}")
        print(f"{C.BOLD}  {result.old_version}  →  {result.new_version}{C.RESET}")
        print(f"{C.DIM}  {result.timestamp}{C.RESET}")
        print(f"{C.BRIGHT_CYAN}{'═' * W}{C.RESET}")
        print()
        print(f"  {C.BOLD}SUMMARY{C.RESET}")
        print(f"  {C.DIM}{'─' * 38}{C.RESET}")
        print(f"  Files changed:  {len(result.files)}")
        print(f"  Added:          {C.BRIGHT_GREEN}{result.total_added} files{C.RESET}")
        print(f"  Modified:       {C.BRIGHT_YELLOW}{result.total_modified} files{C.RESET}")
        print(f"  Deleted:        {C.BRIGHT_RED}{result.total_deleted} files{C.RESET}")
        print()
        print(f"  Lines added:    {C.BRIGHT_GREEN}+{result.total_lines_added}{C.RESET}")
        print(f"  Lines removed:  {C.BRIGHT_RED}-{result.total_lines_removed}{C.RESET}")
        print(f"{C.BRIGHT_CYAN}{'═' * W}{C.RESET}")
        print()
        print(f"  {C.BOLD}CHANGED FILES{C.RESET}")
        print(f"  {C.DIM}{'─' * 38}{C.RESET}")
        for fd in result.files:
            if fd.state == 'ADDED':
                print(f"  {C.BRIGHT_GREEN}+ {fd.path}{C.RESET}")
            elif fd.state == 'MODIFIED':
                print(f"  {C.BRIGHT_YELLOW}~ {fd.path:<24} +{fd.lines_added} -{fd.lines_removed}{C.RESET}")
            elif fd.state == 'BINARY_MODIFIED':
                print(f"  {C.BRIGHT_MAGENTA}B {fd.path}  (binary){C.RESET}")
            elif fd.state == 'DELETED':
                print(f"  {C.BRIGHT_RED}- {fd.path}{C.RESET}")
        print()

    @staticmethod
    def _fmt(size: int) -> str:
        for u in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {u}"
            size /= 1024
        return f"{size:.1f} TB"

# =============================================================================
# VISUAL DIFF VIEWER
# =============================================================================

class VisualDiffViewer:
    STATE_META = {
        'ADDED':      (C.BRIGHT_GREEN,  "new file — every line below was added"),
        'DELETED':    (C.BRIGHT_RED,    "file removed — every line below was deleted"),
        'MODIFIED':   (C.BRIGHT_YELLOW, "modified — changed segments are strongly highlighted"),
        'BINARY_MODIFIED': (C.BRIGHT_MAGENTA, "binary file — content not shown as text"),
    }
    STATE_TAG = {'ADDED': 'ADD', 'DELETED': 'DEL', 'MODIFIED': 'MOD', 'BINARY_MODIFIED': 'BIN'}

    @staticmethod
    def show(result: DiffResult):
        files = result.files
        if not files:
            UI.info("No changes to display.")
            return
        idx = 0
        while True:
            UI.clear()
            fd = files[idx]
            VisualDiffViewer._header(fd, idx, len(files))
            VisualDiffViewer._body(fd)
            print()
            print(f"  {C.DIM}[n]ext  [p]rev  [l]ist  [s]earch  [b]ack  [q]uit{C.RESET}")
            try:
                key = input(f"  {C.BRIGHT_CYAN}> {C.RESET}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if key == 'q':
                raise VibeQuit()          # q = exit the whole tool
            elif key == 'b':
                return                     # b = back one level
            elif key == 'n':
                idx = (idx + 1) % len(files)
            elif key == 'p':
                idx = (idx - 1) % len(files)
            elif key == 'l':
                picked = VisualDiffViewer._list_pick(files)
                if picked is not None:
                    idx = picked
            elif key == 's':
                picked = VisualDiffViewer._search_pick(files)
                if picked is not None:
                    idx = picked

    # ---- pickers ---------------------------------------------------------
    @staticmethod
    def _list_pick(files):
        print()
        for i, f in enumerate(files, 1):
            color = VisualDiffViewer.STATE_META.get(f.state, (C.WHITE, ""))[0]
            print(f"  {C.BRIGHT_CYAN}[{i}]{C.RESET} {color}[{VisualDiffViewer.STATE_TAG.get(f.state, '?')}]{C.RESET} {f.path}")
        print()
        try:
            sel = input(f"  {C.BRIGHT_CYAN}open #> {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if sel.isdigit() and 1 <= int(sel) <= len(files):
            return int(sel) - 1
        return None

    @staticmethod
    def _search_pick(files):
        """Live search: list updates on every keystroke."""
        if _HAS_TTY:
            try:
                if sys.stdin.isatty():
                    return VisualDiffViewer._live_search(files)
            except Exception:
                pass
        return VisualDiffViewer._blind_search(files)

    @staticmethod
    def _read_key(fd):
        ch = os.read(fd, 1).decode('utf-8', 'replace')
        if ch == '\x1b':
            if select.select([fd], [], [], 0.05)[0]:
                c2 = os.read(fd, 1).decode('utf-8', 'replace')
                if c2 == '[':
                    c3 = os.read(fd, 1).decode('utf-8', 'replace')
                    return {'A': 'UP', 'B': 'DOWN'}.get(c3, 'ESC')
                return 'ESC'
            return 'ESC'
        return ch

    @staticmethod
    def _live_search(files):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        query = ""
        sel = 0
        printed = 0
        matches = []
        try:
            tty.setcbreak(fd)

            def draw():
                nonlocal printed, matches
                matches = [(i, f) for i, f in enumerate(files)
                           if query.lower() in f.path.lower()]
                if printed:
                    sys.stdout.write(f"\033[{printed}A")
                sys.stdout.write("\033[J")
                lines = [f"  {C.BRIGHT_CYAN}search> {C.RESET}{query}{C.DIM}█{C.RESET}"]
                if not matches:
                    lines.append(f"  {C.DIM}(no match){C.RESET}")
                else:
                    shown = matches[:8]
                    for n, (i, f) in enumerate(shown):
                        color = VisualDiffViewer.STATE_META.get(f.state, (C.WHITE, ""))[0]
                        mark = f"{C.BRIGHT_WHITE}>{C.RESET}" if n == sel else " "
                        lines.append(f"  {mark} {color}[{VisualDiffViewer.STATE_TAG.get(f.state, '?')}]{C.RESET} {f.path}")
                    if len(matches) > 8:
                        lines.append(f"  {C.DIM}  … +{len(matches) - 8} more{C.RESET}")
                lines.append(f"  {C.DIM}↑↓ select • enter open • esc cancel{C.RESET}")
                sys.stdout.write("\n".join(lines) + "\n")
                sys.stdout.flush()
                printed = len(lines)

            draw()
            while True:
                key = VisualDiffViewer._read_key(fd)
                if key in ('ESC', '\x03'):
                    return None
                if key in ('\n', '\r'):
                    if matches:
                        sel = min(sel, len(matches) - 1)
                        return matches[sel][0]
                    return None
                if key == 'UP':
                    sel = max(0, sel - 1)
                    draw()
                elif key == 'DOWN':
                    sel = min(len(matches) - 1, sel + 1)
                    draw()
                elif key in ('\x7f', '\x08'):
                    query = query[:-1]
                    sel = 0
                    draw()
                elif key.isprintable():
                    query += key
                    sel = 0
                    draw()
        except Exception:
            return VisualDiffViewer._blind_search(files)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            if printed:
                sys.stdout.write(f"\033[{printed}A\033[J")
                sys.stdout.flush()

    @staticmethod
    def _blind_search(files):
        try:
            q = input(f"  {C.BRIGHT_CYAN}search> {C.RESET}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if not q:
            return None
        matches = [(i, f) for i, f in enumerate(files) if q in f.path.lower()]
        if not matches:
            UI.warning("No matching file.")
            return None
        if len(matches) == 1:
            return matches[0][0]
        print()
        for i, f in matches:
            color = VisualDiffViewer.STATE_META.get(f.state, (C.WHITE, ""))[0]
            print(f"  {C.BRIGHT_CYAN}[{i + 1}]{C.RESET} {color}[{VisualDiffViewer.STATE_TAG.get(f.state, '?')}]{C.RESET} {f.path}")
        print()
        try:
            sel = input(f"  {C.BRIGHT_CYAN}open #> {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if sel.isdigit() and 1 <= int(sel) <= len(files):
            return int(sel) - 1
        return None

    # ---- rendering -------------------------------------------------------
    @staticmethod
    def _header(fd, idx, total):
        color, desc = VisualDiffViewer.STATE_META.get(fd.state, (C.WHITE, ""))
        w = get_terminal_width()
        print()
        print(f"  {C.DIM}File {idx + 1}/{total}{C.RESET}")
        print(f"  {color}{C.BOLD}[{fd.state}]{C.RESET} {C.BOLD}{fd.path}{C.RESET}")
        print(f"  {C.DIM}{desc}{C.RESET}")
        if fd.is_binary:
            print(f"  {C.DIM}Previous size: {ReportGenerator._fmt(fd.old_size)}   "
                  f"New size: {ReportGenerator._fmt(fd.new_size)}   hash: changed{C.RESET}")
        else:
            print(f"  {C.BRIGHT_GREEN}+{fd.lines_added}{C.RESET} {C.BRIGHT_RED}-{fd.lines_removed}{C.RESET}"
                  f"  {C.DIM}lines{C.RESET}")
        print(f"  {C.DIM}{'─' * max(10, w - 4)}{C.RESET}")

    @staticmethod
    def _parse_rows(fd):
        rows = []
        old_no = new_no = 0
        for line in fd.diff_lines:
            if line.startswith('@@'):
                m = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
                if m:
                    old_no, new_no = int(m.group(1)), int(m.group(2))
                rows.append(('hunk', line, None, None))
                continue
            if line.startswith('---') or line.startswith('+++'):
                continue
            if line.startswith('-'):
                rows.append(('del', line[1:], old_no, None)); old_no += 1
            elif line.startswith('+'):
                rows.append(('add', line[1:], None, new_no)); new_no += 1
            else:
                rows.append(('ctx', line[1:] if line[:1] == ' ' else line, old_no, new_no))
                old_no += 1; new_no += 1
        return rows

    @staticmethod
    def _seg_map(fd):
        om, nm = {}, {}
        for ch in fd.intra_line_changes:
            om.setdefault(ch['old_line_num'], []).extend(
                (c['old_start'], c['old_end']) for c in ch['changes'] if c['old_end'] > c['old_start'])
            nm.setdefault(ch['new_line_num'], []).extend(
                (c['new_start'], c['new_end']) for c in ch['changes'] if c['new_end'] > c['new_start'])
        return om, nm

    @staticmethod
    def _body(fd):
        if fd.is_binary:
            return
        rows = VisualDiffViewer._parse_rows(fd)
        if not rows:
            print(f"  {C.DIM}(empty file){C.RESET}")
            return
        om, nm = VisualDiffViewer._seg_map(fd)
        width = get_terminal_width()
        for kind, text, ono, nno in rows:
            if kind == 'hunk':
                print(f"  {C.CYAN}{truncate_to_width(text, width - 4)}{C.RESET}")
                continue
            if kind == 'ctx':
                VisualDiffViewer._print_wrapped(' ', text, [], None, width)
                continue
            if kind == 'del':
                VisualDiffViewer._print_wrapped('-', text, om.get(ono, []), 'del', width)
            else:
                VisualDiffViewer._print_wrapped('+', text, nm.get(nno, []), 'add', width)

    @staticmethod
    def _print_wrapped(marker, text, segs, kind, width):
        row_bg = C.ROW_DEL if kind == 'del' else (C.ROW_ADD if kind == 'add' else "")
        seg_bg = C.SEG_DEL if kind == 'del' else (C.SEG_ADD if kind == 'add' else "")
        mark_fg = C.BRIGHT_RED if kind == 'del' else (C.BRIGHT_GREEN if kind == 'add' else C.DIM)

        pieces = []
        pos = 0
        for s, e in sorted(segs):
            s, e = max(s, pos), max(e, pos)
            if s > pos:
                pieces.append((text[pos:s], False))
            if e > s:
                pieces.append((text[s:e], True))
            pos = e
        if pos < len(text):
            pieces.append((text[pos:], False))
        if not pieces:
            pieces = [("", False)]

        gutter_w = 3
        content_w = max(8, width - gutter_w - 2)

        phys = []
        cur, cur_len = [], 0
        for ptext, changed in pieces:
            while True:
                space = content_w - cur_len
                if space <= 0:
                    phys.append(cur); cur, cur_len = [], 0
                    space = content_w
                if len(ptext) <= space:
                    cur.append((ptext, changed)); cur_len += len(ptext)
                    break
                chunk = ptext[:space]
                sp = chunk.rfind(' ')
                if sp > content_w // 3:
                    chunk = chunk[:sp + 1]
                cur.append((chunk, changed)); cur_len += len(chunk)
                ptext = ptext[len(chunk):]
        if cur or not phys:
            phys.append(cur)

        for ri, row in enumerate(phys):
            gut_mark = mark_fg + marker if ri == 0 else ' '
            buf = f"  {row_bg}{gut_mark} {C.RESET}"
            vis_len = gutter_w
            for chunk, changed in row:
                style = (row_bg + seg_bg + C.BOLD) if changed else row_bg
                buf += f"{style}{chunk}{C.RESET}"
                vis_len += len(chunk)
            pad = max(0, width - vis_len - 2)
            if row_bg:
                buf += f"{row_bg}{' ' * pad}{C.RESET}"
            print(buf)

# =============================================================================
# SNAPSHOT MANAGER
# =============================================================================

class SnapshotManager:
    def __init__(self, storage: StorageManager, scanner: Scanner, engine: DiffEngine):
        self.storage = storage
        self.scanner = scanner
        self.engine = engine

    def save_snapshot(self, name, source_path, version, on_progress=None) -> bool:
        source = Path(source_path)
        if not source.exists():
            UI.error(f"Source path does not exist: {source_path}")
            return False
        if self.storage.snapshot_exists(name, version):
            UI.error(f"Snapshot already exists on disk: {version}")
            return False

        src_size = self._dir_size(source)
        free = self.storage.get_disk_usage()['free']
        UI.info(f"Source size: {ReportGenerator._fmt(src_size)}")
        UI.info(f"Available:   {ReportGenerator._fmt(free)}")
        if src_size > free:
            UI.error("Insufficient disk space.")
            return False
        UI.gap()

        snap = self.storage.snapshot_path(name, version)
        tmp = snap.with_name(snap.name + '.tmp')
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        try:
            files = self.scanner.scan(str(source))
            if not files:
                UI.warning("No files found to snapshot.")
                return False
            base = source.resolve()
            total = len(files)
            for i, fp in enumerate(files):
                try:
                    rel = fp.resolve().relative_to(base)
                    dest = tmp / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(fp, dest)
                except Exception as e:
                    UI.warning(f"Failed to copy {fp}: {e}")
                if on_progress:
                    on_progress('Saving snapshot', i + 1, total)
            tmp.rename(snap)

            meta = self.storage.load_project_meta(name) or {
                'name': name, 'source_path': str(base),
                'created': datetime.datetime.now().isoformat(), 'snapshots': []}
            meta['source_path'] = str(base)
            meta['snapshots'] = [s for s in meta.get('snapshots', []) if s.get('version') != version]
            meta['snapshots'].append({'version': version,
                                      'timestamp': datetime.datetime.now().isoformat(),
                                      'files': total, 'size': src_size})
            meta['snapshots'].sort(key=lambda e: StorageManager._version_key(e['version']))
            meta['updated'] = datetime.datetime.now().isoformat()
            self.storage.save_project_meta(name, meta)
            UI.gap()
            UI.success(f"Snapshot saved: {version}")
            UI.success(f"{total} files archived")
            return True
        except Exception as e:
            UI.error(f"Failed to create snapshot: {e}")
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            return False

    def update_snapshot(self, name, source_path, new_version, on_progress=None):
        disk = self.storage.list_snapshots(name)
        if not disk:
            UI.warning("No previous snapshot on disk — performing a plain SAVE instead.")
            if not self.save_snapshot(name, source_path, new_version, on_progress):
                return None
            return 'saved-only'
        latest = disk[-1]
        if not self.save_snapshot(name, source_path, new_version, on_progress):
            return None
        UI.gap()
        old_dir = self.storage.snapshot_path(name, latest)
        new_dir = self.storage.snapshot_path(name, new_version)
        result = self.engine.compare(old_dir, new_dir, latest, new_version,
                                     on_progress=lambda c, t: on_progress and on_progress('Comparing files', c, t))
        report = self.storage.diff_file(name, latest, new_version)
        ReportGenerator.generate(result, report)
        UI.gap()
        UI.success("Full diff saved:")
        print(f"    {report}")
        return result

    def compare_versions(self, name, old_v, new_v, on_progress=None):
        od, nd = self.storage.snapshot_path(name, old_v), self.storage.snapshot_path(name, new_v)
        if not od.is_dir():
            UI.error(f"Snapshot not found on disk: {old_v}")
            return None
        if not nd.is_dir():
            UI.error(f"Snapshot not found on disk: {new_v}")
            return None
        result = self.engine.compare(od, nd, old_v, new_v,
                                     on_progress=lambda c, t: on_progress and on_progress('Comparing files', c, t))
        report = self.storage.diff_file(name, old_v, new_v)
        ReportGenerator.generate(result, report)
        UI.gap()
        UI.success("Full diff saved:")
        print(f"    {report}")
        return result

    def restore_snapshot(self, name, version, target_path, on_progress=None) -> bool:
        snap = self.storage.snapshot_path(name, version)
        target = Path(target_path)
        if not snap.is_dir():
            UI.error(f"Snapshot not found on disk: {version}")
            return False
        files = [f for f in snap.rglob('*') if f.is_file()]
        if not files:
            UI.error("Snapshot is empty or corrupted.")
            return False

        UI.section(f"RESTORE {version}")
        UI.kv("Target", str(target))
        UI.gap()
        UI.warning("This will COMPLETELY replace the current project directory.")
        UI.warning("Files present now but absent from the snapshot WILL be removed.")
        UI.gap()
        if not UI.confirm("Continue?"):
            UI.info("Restore cancelled.")
            return False
        UI.gap()

        tmp = target.parent / f"{target.name}.restore.tmp"
        backup = target.parent / f"{target.name}.backup"
        try:
            if tmp.exists():
                shutil.rmtree(tmp)
            total = len(files)
            for i, fp in enumerate(files):
                dest = tmp / fp.relative_to(snap)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fp, dest)
                if on_progress:
                    on_progress('Copying snapshot', i + 1, total)
            if target.exists():
                if backup.exists():
                    shutil.rmtree(backup, ignore_errors=True)
                target.rename(backup)
            tmp.rename(target)
            if backup.exists():
                shutil.rmtree(backup, ignore_errors=True)
            UI.gap()
            UI.success(f"Snapshot {version} restored")
            UI.success(f"{total} files restored — directory fully replaced")
            return True
        except Exception as e:
            UI.error(f"Restore failed: {e}")
            if not target.exists() and backup.exists():
                try:
                    backup.rename(target)
                    UI.info("Original directory recovered from backup.")
                except Exception:
                    UI.error("CRITICAL: backup exists but could not be restored.")
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            return False

    @staticmethod
    def _dir_size(p: Path) -> int:
        return sum(f.stat().st_size for f in p.rglob('*') if f.is_file())

# =============================================================================
# PROJECT MANAGER
# =============================================================================

class ProjectManager:
    def __init__(self, storage: StorageManager, snaps: SnapshotManager):
        self.storage = storage
        self.snaps = snaps

    def run(self):
        UI.clear()
        UI.banner()
        if self.storage.list_projects():
            choice = UI.menu("What would you like to do?", [
                ("OPEN SAVED PROJECT", "Continue working with an existing tracked project"),
                ("NEW PROJECT", "Add a new project path"),
                ("QUIT", "Exit VibeDiff"),
            ], allow_back=False)
            if choice == 1:
                self._select_saved()
            elif choice == 2:
                self._new_project()
        else:
            choice = UI.menu("No saved projects yet.", [
                ("NEW PROJECT", "Add a new project path"),
                ("QUIT", "Exit VibeDiff"),
            ], allow_back=False)
            if choice == 1:
                self._new_project()

    def _select_saved(self):
        names = self.storage.list_projects()
        if not names:
            UI.warning("No saved projects found.")
            return
        UI.section("Saved projects")
        for i, n in enumerate(names, 1):
            meta = self.storage.reconcile(n)
            snaps = meta.get('snapshots', [])
            latest = snaps[-1]['version'] if snaps else 'None'
            bad = any(s.get('integrity') == 'mismatch' for s in snaps)
            print(f"\n  {C.BRIGHT_CYAN}[{i}]{C.RESET} {C.BOLD}{n}{C.RESET}"
                  + (f"  {C.YELLOW}⚠ integrity warning{C.RESET}" if bad else ""))
            UI.kv("Path", meta.get('source_path', 'Unknown'), indent=6)
            UI.kv("Latest", latest, indent=6)
            UI.kv("Snapshots", str(len(snaps)), indent=6)
        print()
        sel = UI.prompt("Select project number")
        try:
            self._open(names[int(sel) - 1])
        except (ValueError, IndexError):
            UI.error("Invalid selection.")

    def _new_project(self):
        p = UI.prompt("Project path")
        p = os.path.expanduser(p)
        if not os.path.exists(p):
            UI.error(f"Path does not exist: {p}")
            return
        name = Path(p).name
        name = "".join(c if c.isalnum() or c in '_-' else '_' for c in name)
        if self.storage.load_project_meta(name):
            UI.warning(f"Project '{name}' is already tracked.")
            if UI.confirm("Open the existing project?"):
                self._open(name)
            return
        self.storage.save_project_meta(name, {
            'name': name, 'source_path': str(Path(p).resolve()),
            'created': datetime.datetime.now().isoformat(), 'snapshots': []})
        UI.success(f"Project '{name}' added.")
        self._open(name)

    def _open(self, name):
        meta = self.storage.reconcile(name)
        source = meta.get('source_path', '')
        if source and not Path(source).exists():
            UI.gap()
            UI.warning("Original path is unavailable")
            UI.kv("Stored path", source)
            UI.gap()
            ch = UI.menu("What would you like to do?", [
                ("Reconnect", "Point this project to a new location"),
                ("Snapshots only", "Work with saved versions only"),
                ("Back", "Return to project selection"),
            ])
            if ch == 1:
                np = UI.prompt("New project path")
                np = os.path.expanduser(np)
                if Path(np).exists():
                    meta['source_path'] = str(Path(np).resolve())
                    self.storage.save_project_meta(name, meta)
                    source = meta['source_path']
                    UI.success("Project reconnected.")
                else:
                    UI.error("Invalid path.")
                    return
            elif ch == 2:
                source = ''
            else:
                return

        while True:
            UI.clear()
            UI.banner()
            meta = self.storage.reconcile(name)
            snaps = self.storage.list_snapshots(name)
            UI.section(f"Project: {name}")
            if source:
                UI.kv("Path", source)
            UI.kv("Snapshots", str(len(snaps)))
            if snaps:
                UI.kv("Latest", snaps[-1])
            if meta.get('updated'):
                UI.kv("Last update", meta['updated'])
            for s in meta.get('snapshots', []):
                if s.get('integrity') == 'mismatch':
                    UI.warning(f"Snapshot {s['version']} content differs from its record.")

            if snaps:
                ch = UI.menu("What would you like to do?", [
                    ("UPDATE", "Save current state as a new version + generate Diff"),
                    ("COMPARE", "Compare any two saved versions"),
                    ("RESTORE", "Restore a saved snapshot to the project path"),
                    ("SAVE", "Save as a new version (without diff)"),
                    ("HISTORY", "View, compare, restore or delete snapshots"),
                    ("DELETE PROJECT", "Remove this project from VibeDiff (source untouched)"),
                    ("BACK", "Return to project selection"),
                ])
                if ch == 1: self._update(name, source)
                elif ch == 2: self._compare(name)
                elif ch == 3: self._restore(name, source)
                elif ch == 4: self._save(name, source)
                elif ch == 5: self._history(name)
                elif ch == 6: self._delete_project(name); return
                elif ch == 7: return
            else:
                ch = UI.menu("What would you like to do?", [
                    ("SAVE", "Save current project as a new version"),
                    ("DELETE PROJECT", "Remove this project from VibeDiff"),
                    ("BACK", "Return to project selection"),
                ])
                if ch == 1: self._save(name, source)
                elif ch == 2: self._delete_project(name); return
                elif ch == 3: return

    def _save(self, name, source):
        if not source:
            UI.error("No source path connected.")
            return
        v = UI.prompt("New version (e.g., v1.0.0)")
        if self.storage.snapshot_exists(name, v):
            UI.error(f"Version already exists: {v}")
            return
        UI.gap()
        if self.snaps.save_snapshot(name, source, v, on_progress=self._prog):
            UI.gap()
            UI.success("Operation completed.")
        UI.pause()

    def _update(self, name, source):
        if not source:
            UI.error("No source path connected.")
            return
        v = UI.prompt("New version (e.g., v1.0.1)")
        if self.storage.snapshot_exists(name, v):
            UI.error(f"Version already exists: {v}")
            return
        UI.gap()
        result = self.snaps.update_snapshot(name, source, v, on_progress=self._prog)
        if result == 'saved-only':
            UI.pause()
            return
        if result:
            ReportGenerator.display_summary(result)
            ch = UI.menu("What would you like to do?", [
                ("VISUAL DIFF", "Inspect changes interactively in Terminal"),
                ("CONTINUE", "Return to project menu"),
            ])
            if ch == 1:
                VisualDiffViewer.show(result)
        UI.pause()

    def _compare(self, name):
        snaps = self.storage.list_snapshots(name)
        if len(snaps) < 2:
            UI.warning("Need at least 2 snapshots on disk to compare.")
            UI.pause()
            return
        self._list_versions(snaps)
        a = UI.prompt("Select OLD version number")
        b = UI.prompt("Select NEW version number")
        try:
            ov, nv = snaps[int(a) - 1], snaps[int(b) - 1]
        except (ValueError, IndexError):
            UI.error("Invalid selection.")
            UI.pause()
            return
        UI.gap()
        result = self.snaps.compare_versions(name, ov, nv, on_progress=self._prog)
        if result:
            ReportGenerator.display_summary(result)
            ch = UI.menu("What would you like to do?", [
                ("VISUAL DIFF", "Inspect changes interactively in Terminal"),
                ("CONTINUE", "Return to project menu"),
            ])
            if ch == 1:
                VisualDiffViewer.show(result)
        UI.pause()

    def _restore(self, name, source):
        if not source:
            UI.error("Cannot restore without a connected project path.")
            UI.pause()
            return
        snaps = self.storage.list_snapshots(name)
        if not snaps:
            UI.warning("No snapshots on disk.")
            UI.pause()
            return
        self._list_versions(snaps)
        sel = UI.prompt("Select snapshot to restore")
        try:
            v = snaps[int(sel) - 1]
        except (ValueError, IndexError):
            UI.error("Invalid selection.")
            UI.pause()
            return
        UI.gap()
        if self.snaps.restore_snapshot(name, v, source, on_progress=self._prog):
            UI.gap()
            UI.success("Restore completed.")
        UI.pause()

    def _history(self, name):
        meta = self.storage.reconcile(name)
        snaps = meta.get('snapshots', [])
        if not snaps:
            UI.info("No snapshots yet.")
            UI.pause()
            return
        while True:
            UI.clear()
            UI.section("Snapshot History")
            for i, s in enumerate(snaps, 1):
                flag = f"  {C.YELLOW}⚠ {s['integrity']}{C.RESET}" if s.get('integrity') else ""
                rec = f"  {C.DIM}(recovered from disk){C.RESET}" if s.get('recovered') else ""
                print(f"\n  {C.BRIGHT_CYAN}[{i}]{C.RESET} {C.BOLD}{s['version']}{C.RESET}{flag}{rec}")
                UI.kv("Date", s.get('timestamp', '?'), indent=6)
                UI.kv("Files", str(s.get('files', '?')), indent=6)
                UI.kv("Size", ReportGenerator._fmt(s.get('size', 0)), indent=6)
            ch = UI.menu("Select action", [
                ("RESTORE", "Restore a snapshot to the project path"),
                ("COMPARE", "Compare two snapshots"),
                ("DELETE SNAPSHOT", "Permanently delete a snapshot + its diffs"),
                ("BACK", "Return to project menu"),
            ])
            if ch == 1:
                sel = UI.prompt("Select snapshot number to restore")
                try:
                    v = snaps[int(sel) - 1]['version']
                except (ValueError, IndexError):
                    UI.error("Invalid selection."); UI.pause(); continue
                source = meta.get('source_path', '')
                if not source:
                    UI.error("No connected path to restore into."); UI.pause(); continue
                UI.gap()
                self.snaps.restore_snapshot(name, v, source, on_progress=self._prog)
                UI.pause()
                return
            if ch == 2:
                if len(snaps) < 2:
                    UI.warning("Need at least 2 snapshots."); UI.pause(); continue
                self._list_versions([s['version'] for s in snaps])
                a = UI.prompt("Select OLD snapshot number")
                b = UI.prompt("Select NEW snapshot number")
                try:
                    ov = snaps[int(a) - 1]['version']; nv = snaps[int(b) - 1]['version']
                except (ValueError, IndexError):
                    UI.error("Invalid selection."); UI.pause(); continue
                UI.gap()
                result = self.snaps.compare_versions(name, ov, nv, on_progress=self._prog)
                if result:
                    ReportGenerator.display_summary(result)
                    c2 = UI.menu("What would you like to do?", [
                        ("VISUAL DIFF", "Inspect changes"),
                        ("CONTINUE", "Return to history"),
                    ])
                    if c2 == 1:
                        VisualDiffViewer.show(result)
                UI.pause()
            elif ch == 3:
                sel = UI.prompt("Select snapshot number to DELETE")
                try:
                    v = snaps[int(sel) - 1]['version']
                except (ValueError, IndexError):
                    UI.error("Invalid selection."); UI.pause(); continue
                UI.gap()
                UI.warning(f"This permanently deletes snapshot {v} and every diff referencing it.")
                if UI.confirm(f"Delete snapshot {v}?"):
                    n = self.storage.delete_snapshot(name, v)
                    UI.success(f"Snapshot {v} deleted ({n} diff file(s) removed).")
                else:
                    UI.info("Cancelled.")
                UI.pause()
                snaps = self.storage.reconcile(name).get('snapshots', [])
            else:
                return

    def _delete_project(self, name):
        UI.gap()
        UI.warning(f"This removes ALL VibeDiff data for '{name}':")
        print(f"    {self.storage.project_path(name)}")
        UI.warning("Snapshots, diffs and metadata will be destroyed.")
        UI.warning("The ORIGINAL project folder is NOT touched.")
        UI.gap()
        answer = UI.prompt(f"Type the project name to confirm ({name})")
        if answer == name:
            self.storage.delete_project(name)
            UI.success(f"Project '{name}' removed from VibeDiff.")
        else:
            UI.info("Cancelled — name did not match.")
        UI.pause()

    @staticmethod
    def _list_versions(snaps):
        UI.section("Available versions")
        for i, v in enumerate(snaps, 1):
            print(f"  {C.BRIGHT_CYAN}[{i}]{C.RESET} {v}")
        print()

    def _prog(self, label, cur, total):
        UI.progress(label, cur, total)

# =============================================================================
# MAIN
# =============================================================================

def main():
    try:
        env = EnvironmentManager()
        UI.clear()
        UI.banner()
        if not env.bootstrap():
            UI.error("Environment not ready. Exiting.")
            sys.exit(1)
        storage = StorageManager(env.storage_root)
        snaps = SnapshotManager(storage, Scanner(use_rg=env.has_rg), DiffEngine())
        pm = ProjectManager(storage, snaps)
        while True:
            try:
                pm.run()
            except VibeBack:
                continue
            if not UI.confirm("Process another project?"):
                break
    except VibeQuit:
        print(f"\n  {C.BRIGHT_CYAN}Goodbye.{C.RESET}")
        sys.exit(0)
    except VibeBack:
        sys.exit(0)
    except KeyboardInterrupt:
        print(f"\n\n  {C.YELLOW}Interrupted. Goodbye.{C.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n  {C.RED}Fatal error: {e}{C.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
