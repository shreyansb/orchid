---
name: orchid-tasks
description: Create the orchid home folder, the config file, generic orchestrator rules, and the task, board and journal files. Use when the user wants an orchestrator that tracks work across agents.
---

# orchid-tasks

## What it does
Creates the person's state: a home folder with the orchestrator's rules (`AGENTS.md`), `board.md`, `journal.md`, `spaces.md`, `tasks/` and `done/`, plus the config file that tells orchid where it is. The orchestrator agent runs from this folder. Task format: `docs/tasks.md`.

## Questions
1. Where should the home folder be? Default `~/orchid-home`. It must not be inside the repo clone.
2. Name of the orchestrator agent? Default `orchid`.
3. Label for this machine? (See `herdr-machines`.) No "/" in it.
4. Which agent kind will run the orchestrator: Claude Code or Codex? Claude reads `CLAUDE.md`, which imports `AGENTS.md`. Codex reads `AGENTS.md`.
5. Do they already keep global rules (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`)? Those are left alone. The agent loads them itself where its tool does.

## Steps
For every file below use `<repo>/scripts/safe-write.sh <source> <destination>` as a dry run, show the result, and add `--apply` only after a yes. It never overwrites without a diff and a backup.
1. Config: `<repo>/templates/config` -> `~/.config/orchid/config`. Then set `home=`, `orchestrator=` and `machine_label=` to the answers.
2. Make the folders: `<home>/tasks` and `<home>/done`.
3. Copy `<repo>/templates/{AGENTS.md,CLAUDE.md,board.md,journal.md,spaces.md}` to `<home>/`. The home `CLAUDE.md` must contain `@AGENTS.md`. Copy `templates/profiles.md` too if profiles are wanted (see `herdr-profiles`).
4. Copy `<repo>/templates/task.md` to `<home>/task-template.md`. Fill `spaces.md` with the spaces the person has, as a guess they can correct.
5. Start the orchestrator: in a herdr pane, `cd <home>` then start the agent (`claude` or `codex`). Name it: `herdr agent rename <pane> <orchestrator-name>`. The watcher wakes only an agent with that exact name.
6. Add the person's own rules to `<home>/AGENTS.md` if they want (it is their copy).

## Verify
`python3 <repo>/skills/orchid-watcher/orchid_watcher.py --check` prints the config and finds the orchestrator agent. `python3 <repo>/skills/orchid-doctor/doctor.py` shows OK for config, home folder and files.

## Undo
Delete `<home>` only if the person says so; it holds their records. Delete `~/.config/orchid/config` to unset the location. Both can be restored from the `.orchid-bak-*` backups if they were overwritten.
