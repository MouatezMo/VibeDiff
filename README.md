# VibeDiff

**Precision Version Tracker for Termux & Linux**

VibeDiff is a lightweight, GitHub-inspired version tracker for local project folders. Save numbered snapshots of any project, compare any two versions, inspect precise file and line changes, restore an older version, and keep the whole history organized — without turning the project itself into a Git repository.

It is built for the moments when a project is changing fast and you want a simple answer to:

> **“What exactly changed between the version I had before and the version I have now?”**

---

## Why VibeDiff?

Not every folder needs a Git workflow.

Sometimes you are working on a Godot project, an Android app, a Python tool, a SaaS project, a Termux utility, or a one-off experiment. You just want checkpoints you can trust and a clean way to see what changed.

VibeDiff gives you that workflow:

```text
Current project
      │
      ├── SAVE   → v0.2.9
      │
      ├── work on the project
      │
      ├── UPDATE → v0.3.0
      │              │
      │              └── automatic Diff
      │
      └── later → COMPARE v0.2.9 ↔ v0.3.0
```

The result is intentionally split into three experiences:

```text
Terminal summary
    ↓
quick understanding

TXT report
    ↓
complete, searchable record

Visual Diff
    ↓
human-friendly inspection
```

---

## Features

### 📦 Versioned snapshots

Save the complete state of a project as a named version:

```text
v0.2.9
v0.3.0
v0.4.0
v1.0.0
```

Each project gets its own organized archive.

### 🔍 GitHub-inspired Diff

Compare the contents of any two snapshots and detect:

- added files
- modified files
- deleted files
- binary changes
- added/removed lines
- precise intra-line changes for visual inspection

The important distinction is that file-level, line-level, and character-level changes are treated separately.

### 🎨 Visual Diff

The Terminal viewer is designed for actual inspection rather than dumping hundreds of lines onto the screen.

Modified lines receive a subtle background tint, while the changed portion inside the line receives stronger highlighting so the eye can immediately see **where the change happened**.

Long lines are wrapped safely instead of being cut off.

### 🧾 One canonical report

Every comparison produces one complete `.txt` report.

No duplicate ANSI/plain report pair.

Example:

```text
VibeDiff/
└── Projects/
    └── my_project/
        └── diffs/
            └── v0.2.9_to_v0.3.0.txt
```

The saved report is plain text, complete, searchable, and suitable for both humans and AI tools.

### 🔄 Compare any two versions

You are not limited to:

```text
previous → latest
```

You can compare:

```text
v0.2.9 → v0.8.0
```

or any other two snapshots available for the project.

### ♻️ Full restore

Restore any saved snapshot back into the project's original path.

Restore is a **real replacement**, not a simple overlay copy. Files that exist in the current project but do not exist in the selected snapshot are removed as part of the replacement.

The operation uses a temporary restore directory and safety checks to reduce the chance of leaving a partially restored project.

### 🧭 Project memory

Once a project is registered, VibeDiff remembers its original path.

You do not have to type the path again every time:

```text
OPEN SAVED PROJECT
```

You can also add a completely new project whenever needed.

### 🩺 Environment awareness

At startup, VibeDiff checks its runtime environment and looks for:

- Python
- ripgrep
- writable storage
- usable permissions

`ripgrep` is used as the fast discovery path, while Python handles the exact snapshot, filesystem, metadata, and diff logic.

If `ripgrep` is missing, VibeDiff can offer to install it on supported environments or continue with the Python fallback scanner.

### 📱 Termux-first UX

The UI is designed with phone terminals in mind:

- responsive terminal width
- wrap-safe banners
- single-line progress bars
- live search
- keyboard navigation
- `q` for full exit
- `b` for back

The interface avoids assuming a desktop-sized terminal.

---

## Storage layout

VibeDiff keeps its data outside the project itself.

By default:

```text
/sdcard/VibeDiff/
└── Projects/
    ├── project_a/
    │   ├── snapshots/
    │   │   ├── v0.1.0/
    │   │   ├── v0.2.0/
    │   │   └── v0.3.0/
    │   │
    │   ├── diffs/
    │   │   ├── v0.1.0_to_v0.2.0.txt
    │   │   └── v0.2.0_to_v0.3.0.txt
    │   │
    │   └── project.json
    │
    └── project_b/
        └── ...
```

Your original project folder remains where it is unless you explicitly use **RESTORE**.

---

## Typical workflow

### 1. First checkpoint

Open VibeDiff and choose:

```text
NEW PROJECT
```

Enter your project path, for example:

```text
/storage/emulated/0/vmaw_v0_1
```

Then:

```text
SAVE
```

and give it a version:

```text
v0.2.9
```

### 2. Keep working normally

Change files, add files, remove files, experiment, refactor — VibeDiff does not require you to change how you work.

### 3. Create the next version

Run VibeDiff again:

```text
OPEN SAVED PROJECT
    ↓
UPDATE
    ↓
v0.3.0
```

VibeDiff saves the new snapshot and automatically compares it with the previous saved version.

### 4. Inspect the result

The default screen stays compact:

```text
SUMMARY
────────────────────────────────────────
Files changed:  3
Added:          0 files
Modified:       3 files
Deleted:        0 files

Lines added:    +7
Lines removed:  -1051

CHANGED FILES
────────────────────────────────────────
~ msg.txt              +1 -1046
~ vmaw/__init__.py     +1 -0
~ vmaw/cli.py          +5 -5
```

Then choose **VISUAL DIFF** when you actually want to inspect the changes on-screen.

The complete report is also saved to disk.

---

## Live search

Inside Visual Diff, press:

```text
s
```

Search is live.

As you type:

```text
search> m
```

the matching changed-file list updates immediately.

Use:

```text
↑ / ↓    move
Enter    open
Esc      cancel search
```

This is especially useful in large projects where you already know part of the filename or path.

---

## Controls

### Global

```text
q   Exit VibeDiff completely
b   Go back one level
```

### Visual Diff

```text
n   Next changed file
p   Previous changed file
l   File list
s   Live search
b   Back
q   Quit
```

Critical confirmations intentionally require explicit `y/n` input.

---

## Installation

VibeDiff is intentionally kept as a **single Python file**.

### Requirements

The core runtime is:

```text
Python 3
ripgrep
```

The project aims to keep the core lightweight and avoid unnecessary Python package dependencies.

### Termux

Install the basic requirements:

```bash
pkg update
pkg install python ripgrep
```

Then download `vibediff.py` into your home directory:

```text
~/vibediff.py
```

and run:

```bash
python ~/vibediff.py
```

VibeDiff also checks for `ripgrep` at startup and can offer installation when it is missing.

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install python3 ripgrep
```

Then:

```bash
python3 ~/vibediff.py
```

---

## Make `vibediff` work from anywhere

For a Termux setup where the script lives at:

```text
~/vibediff.py
```

make it executable:

```bash
chmod +x ~/vibediff.py
```

Then create a launcher in Termux's executable path:

```bash
ln -sf ~/vibediff.py "$PREFIX/bin/vibediff"
```

Now you can simply type:

```bash
vibediff
```

from **any directory**.

That means:

```text
~/project-a
```

```bash
vibediff
```

or:

```text
/storage/emulated/0/MyGame
```

```bash
vibediff
```

or anywhere else.

To verify:

```bash
which vibediff
```

You should get something similar to:

```text
/data/data/com.termux/files/usr/bin/vibediff
```

### Optional: make the command survive replacing the script

The symbolic link points to:

```text
~/vibediff.py
```

so updating the file does not require recreating the command.

---

## Design philosophy

VibeDiff deliberately sits between two worlds.

It is not trying to replace Git.

It is for the much simpler workflow:

```text
I have a folder.
I want checkpoints.
I want exact differences.
I want easy restore.
I do not want a complicated setup.
```

The architecture follows the same idea:

```text
ripgrep
   ↓
fast file discovery

Python
   ↓
exact filesystem + snapshot logic

hashing
   ↓
skip unnecessary content comparisons

line diff
   ↓
structural changes

intra-line diff
   ↓
precise visual targets

Terminal UI
   ↓
human inspection
```

Speed matters, but correctness matters more.

---

## Compatibility

Designed primarily for:

- Termux
- Android development workflows
- Linux
- Debian / Ubuntu

It can also operate in other Python-capable environments when the required filesystem and terminal behavior are available.

---

## Current version

```text
VibeDiff 0.3.1
```

The current release focuses on:

- saved-project workflow
- responsive Terminal UI
- live Visual Diff search
- complete canonical reports
- character/intra-line highlighting
- safe full restore
- snapshot reconciliation
- project and snapshot deletion
- Termux/Linux environment checks

---

## License

Choose a license for your repository before publishing.

A common lightweight option for a single-file utility is **MIT**, but the repository should use whichever license matches your intentions.

---

## The idea in one sentence

> **VibeDiff turns an ordinary project folder into a lightweight local version history with a GitHub-style precision Diff experience.**
