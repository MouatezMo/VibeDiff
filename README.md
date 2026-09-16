# VibeDiff

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Termux](https://img.shields.io/badge/made%20for-Termux%20%7C%20Linux-green.svg)
![Dependencies](https://img.shields.io/badge/deps-stdlib%20%2B%20ripgrep-lightgrey.svg)

**Local checkpoints, snapshots and GitHub inspired precision Diff for any project.**

You have a project folder. You make changes. Before the next big change, you want a reliable **checkpoint**. Later you want to know exactly what changed, compare versions, or return to an earlier state.

**VibeDiff gives you checkpoints, versioned snapshots, Diff, restore and a clean Terminal workflow in one Python file.**

## Features

📍 **CHECKPOINTS**  Save a known good state before making risky or experimental changes.

📦 **SNAPSHOTS**  Keep complete project states under version names such as `v0.2.9` and `v0.3.0`.

🔄 **UPDATE**  Save the next version and automatically compare it with the previous snapshot.

🔍 **COMPARE**  Compare any two saved versions, even when many versions are between them.

♻️ **RESTORE**  Completely replace the project with any saved snapshot.

🎨 **VISUAL DIFF**  Inspect changed files with line and intra line highlighting, including precise changed segments.

🔎 **LIVE SEARCH**  Filter changed files as you type.

🧾 **ONE TXT REPORT**  Every comparison produces one complete plain text report.

⚡ **FAST SCANNING**  Uses ripgrep when available, with a Python fallback.

📱 **TERMUX FRIENDLY**  Responsive output and wrap safe progress bars for phone terminals.

## Quick Start

### Termux

```bash
pkg install python ripgrep
python ~/vibediff.py
```

Register it as a global command:

```bash
chmod +x ~/vibediff.py
ln -sf ~/vibediff.py "$PREFIX/bin/vibediff"
```

Then simply run:

```bash
vibediff
```

from any directory.

Verify:

```bash
which vibediff
```

### Linux

```bash
sudo apt install python3 ripgrep
python3 ~/vibediff.py
```

## Workflow

Use a checkpoint whenever you reach a state you may want to return to:

```text
CHECKPOINT
    ↓
SAVE v0.1.0
    ↓
make changes
    ↓
UPDATE v0.2.0
    ↓
automatic Diff
```

Later:

```text
COMPARE
v0.1.0 → v1.0.0
```

Or:

```text
RESTORE
v0.1.0
```

Projects and snapshots are stored separately under:

```text
/sdcard/VibeDiff/Projects/
```

## What it is

VibeDiff is not trying to replace Git.

It is a lightweight answer to one practical question:

> **What changed in my project, and can I get back to the exact version I saved?**

## License

Released under the MIT License. Free to use, modify, and distribute.
