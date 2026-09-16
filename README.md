# VibeDiff

**Numbered snapshots + GitHub-style diffs for any folder. One Python file. Zero drama.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Termux](https://img.shields.io/badge/made%20for-Termux%20%7C%20Linux-green.svg)
![Dependencies](https://img.shields.io/badge/deps-stdlib%20only%20(ripgrep%20optional)-lightgrey.svg)

---

It's 1 AM. You're fixing "just one thing" in a project on your phone.
You save, you run, everything breaks.

And you remember clearly: *it worked yesterday.*

Git? Never initialized here. Cloud? No. Backup? That folder you copied
last week… maybe? Somewhere?

**VibeDiff exists for exactly this moment.**

Point it at any folder. It keeps numbered snapshots of it, and between any
two snapshots it shows you *exactly* what changed file by file, line by
line, character by character, with the calm, colored clarity of a GitHub
diff, right in your terminal. No git required. No internet. No accounts.
Nothing leaves your device.

---

## The whole deal, in six bullets

- 📄 **One file.** `vibediff.py`, ~1700 lines, Python standard library only.
  Copy it to any machine and it works.
- 🗂 **Snapshots as versions.** `SAVE v0.1.0`, then `UPDATE v0.2.0`…
  a real, browsable history for folders that were never git repos.
- 🔬 **Precision diff.** Added / modified / deleted files, line diffs, and
  intra-line highlighting: when `8` becomes `7`, you *see* the `8` and the `7`.
- 📑 **One clean report per comparison.** A complete, plain-text,
  human- and AI-readable `.txt`. Never truncated. Never two files.
- ⏪ **True restore.** Restoring a snapshot fully replaces the directory,
  files that shouldn't exist disappear. With confirmation and rollback safety.
- 🤖 **Self-aware.** Checks its own environment on start, offers to install
  what's missing (Termux / Debian / Ubuntu / Arch / Fedora), and if you
  delete a snapshot folder by hand behind its back, it notices and reconciles.
  **The disk is the source of truth.**

---

## Install (30 seconds, Termux)

```bash
pkg install python ripgrep
curl -fL -o ~/vibediff.py https://raw.githubusercontent.com/MouatezMo/VibeDiff/main/vibediff.py
python ~/vibediff.py
```

> `ripgrep` is optional but recommended: VibeDiff uses it for fast discovery
> on big trees. Missing it? VibeDiff offers to install it, or quietly falls
> back to its built-in Python scanner. You're never blocked.

On desktop Linux, the same file works as-is, it detects Debian/Ubuntu/Arch/Fedora
and adapts its installer and storage location automatically.

### Make it a real command (run it from anywhere)

You don't want to type `python ~/vibediff.py` forever. One-time setup:

```bash
chmod +x ~/vibediff.py
ln -sf ~/vibediff.py "$PREFIX/bin/vibediff"
```

Now, from any folder:

```bash
vibediff
```

Sanity check:

```bash
which vibediff
# /data/data/com.termux/files/usr/bin/vibediff
```

Prefer something faster to type? Name it whatever your thumbs like:

```bash
ln -sf ~/vibediff.py "$PREFIX/bin/vd"     # now: vd
```

On desktop Linux, same idea:

```bash
ln -sf ~/vibediff.py ~/.local/bin/vibediff   # ensure ~/.local/bin is in $PATH
```

The nice part: `ln -sf` points at the script itself, not a copy.
Update `vibediff.py` tomorrow and your `vibediff` / `vd` command is already
up to date. Nothing to redo.

---

## How it feels

**First run**: it checks itself before it wrecks itself:

```
╭──────────────────────────────────────────────╮
│                   VibeDiff                   │
│           Precision Version Tracker          │
╰──────────────────────────────────────────────╯

Environment check
  ✓ Python      3.12
  ✓ ripgrep     14.1
  ✓ Platform    Termux
  ✓ Storage     /sdcard/VibeDiff
  ✓ Permissions OK

  ✓ Environment ready.
```

**After an UPDATE**: you get the summary, not a wall of text:

```
  SUMMARY
  ──────────────────────────────────────
  Files changed:  3
  Added:          0 files
  Modified:       3 files
  Deleted:        0 files

  Lines added:    +7
  Lines removed:  -1051

  CHANGED FILES
  ~ msg.txt              +1 -1046
  ~ vmaw/__init__.py     +1 -0
  ~ vmaw/cli.py          +5 -5

  ✓ Full diff saved:
    /sdcard/VibeDiff/Projects/vmaw/diffs/v0.2.9_to_v0.3.0.txt
```

**When you want to look closer** `VISUAL DIFF`: GitHub-inspired inspection
with a soft tint on changed lines, a stronger highlight on the exact changed
characters, soft-wrapped long lines (nothing hides off-screen on a phone),
and live search as you type:

```
  [MODIFIED] vmaw/cli.py
  modified, changed segments are strongly highlighted

  -         if argv[i] in ("-C", "--dir") and i + 1 < len(argv):
  +         if argv[i] in ("-C", "--dir") and i - 2< len(argv):
```

*(In a real terminal those two lines carry color: subtle whole-line tint,
bold tint on `+ 1` → `- 2`. Navigate with `n`/`p`, list with `l`,
live-search with `s`, back with `b`, quit with `q` from anywhere.)*

### Three layers, on purpose

| Layer | Where | What it gives you |
|---|---|---|
| **Summary** | terminal, by default | the answer in 5 seconds |
| **Canonical TXT** | `diffs/vA_to_vB.txt` | the complete truth: full, plain, searchable, archivable |
| **Visual diff** | terminal, on demand | the pleasure: color, highlighting, navigation |

They are not three copies of the same dump. Each exists for a different kind of reading.

---

## What you can do with a project

| Operation | Meaning |
|---|---|
| `SAVE` | freeze the current state as a new version |
| `UPDATE` | freeze + auto-diff against the latest snapshot |
| `COMPARE` | diff **any** two versions, not just neighbors |
| `RESTORE` | fully replace the project dir with a snapshot (confirmed, rollback-safe) |
| `HISTORY` | browse, compare, restore, or delete snapshots |
| `DELETE` | remove a snapshot (and its diffs), or untrack a project entirely, your source folder is never touched |

Safety is not an afterthought: snapshots are written to a temp dir, verified,
then atomically renamed. Restores keep a backup until the swap succeeds and
roll back if anything fails. Disk space is checked before copying.
Duplicate versions are refused.

---

## Where your data lives

```
/sdcard/VibeDiff/                 (~/VibeDiff on desktop Linux)
└── Projects/
    └── my_project/
        ├── project.json          # identity + snapshot registry (self-healing)
        ├── snapshots/
        │   ├── v0.1.0/           # a full copy of your project at that version
        │   └── v0.2.0/
        └── diffs/
            └── v0.1.0_to_v0.2.0.txt   # the one canonical report
```

Plain folders. Plain files. You can inspect, copy, or move them with any
tool you already trust. No database, no lock-in.

---

## Under the hood (briefly)

- **Hybrid engine:** ripgrep for fast file discovery when available,
  Python for exact reasoning always. Speed where it's safe, precision where it matters.
- **Layered comparison:** metadata → size → hash → content → intra-line.
  Unchanged files cost almost nothing, even in huge projects.
- **Binary-aware:** images, audio, archives are reported as binary changes
  (sizes + hashes), never dumped as garbage text.
- **Honest statistics:** file-level, line-level and character-level changes
  are kept separate. Deleting a `"` inside a line is a *modification*,
  and the visual diff shows you the `"` it is never miscounted as a deleted file.
- **Phone-first terminal UX:** responsive banner, wrap-safe single-line
  progress bars, width-aware everything. No corrupted `\r`, no wrapped boxes.

---

## Requirements

- Python 3.8+
- ripgrep: optional (auto-install offered; graceful Python fallback otherwise)

That's it. No pip, no virtualenv, no package.json, no node_modules crying in the corner.

---

## This repository

```
VibeDiff/
├── README.md
└── vibediff.py      # the entire product
```

That's the whole repo. One file. That's the point.

---

## Questions you might have

**Is this a git replacement?**
No, and it doesn't want to be. Git tracks content with branches and remotes;
VibeDiff tracks *folders* with versions and readable diffs. For projects where
git is overkill, impossible, or simply not yours, VibeDiff is the right weight.

**Will it touch my original project?**
Only `RESTORE` writes to your project path, and only after an explicit
confirmation showing exactly what will happen. Everything else is read-only.

**Does anything leave my device?**
No. No network calls, no telemetry, no accounts. The only optional network
action is you approving a package-manager install of ripgrep.

**I deleted a snapshot folder manually. Is my history corrupted?**
No. VibeDiff reconciles its metadata with the disk on every open: ghosts are
dropped, orphan folders are recovered, tampered snapshots are flagged.

---

## License

MIT © VibeDiff contributors.
Use it, fork it, ship it, rename it to `vd` and never think about me again.

---

*Your folder changed again last night.*
*This time, you'll know exactly what changed, and you can go back.*
```
