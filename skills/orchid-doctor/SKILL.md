---
name: orchid-doctor
description: Read-only check of an orchid setup: versions, config, home folder, machines, linked skills, profiles, watcher, and a simulated test task. Use after setup, or when something stopped working.
---

# orchid-doctor

## What it does
Runs checks and prints OK, WARN, FAIL or SKIP for each. It never changes anything. SKIP means a feature is not installed, which is fine.

## Questions
None.

## Steps
1. Run `python3 <repo>/skills/orchid-doctor/doctor.py` (add `--json` for scripts).
2. Explain each WARN and FAIL in plain words. Offer the skill that fixes it; do not fix it without a yes:
   - missing or wrong config, home files -> `orchid-tasks`
   - machine unreachable, label with "/" -> `herdr-machines`
   - profile folder missing -> `herdr-profiles`
   - watcher not running -> `orchid-watcher`
3. For the live end-to-end test of the watcher, follow the Verify section of `orchid-watcher`. The doctor itself only simulates a task in a temporary folder and checks the parser finds its owner.

## What it checks
Python (3.8 or later), herdr version, `claude`, `codex`, `gh`, `git` on PATH, the config and home folder, home files, machine labels and reachability, the launchd job and log, linked skills, profile folders, and the task parser.

## Verify
Exit code 0 means no FAIL. A WARN is a hint, not an error.

## Undo
Nothing to undo; it makes no changes.
