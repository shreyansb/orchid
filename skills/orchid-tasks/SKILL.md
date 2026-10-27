---
name: orchid-tasks
description: Create the orchid home folder, the config file, generic orchestrator rules, and the task, board and journal files; start and name the orchestrator. Use when the user wants an orchestrator that tracks work across agents.
---

# orchid-tasks

## What it does
Creates the person's state: a home folder with the orchestrator's rules (`AGENTS.md`), `board.md`, `journal.md`, `spaces.md`, `tasks/` and `done/`, plus the config file that tells orchid where it is. The orchestrator agent runs from this folder. Task format: `docs/tasks.md`.

This skill owns the three config answers (home folder, orchestrator name, this machine's label). Ask them here, once. Every other skill reuses them from the config; none asks again. If a config already exists, read it, show it, and ask only whether to keep it.

## Questions
1. Where should the home folder be? Default `~/orchid-home`. It must not be inside the repo clone.
2. Name of the orchestrator agent? Default `orchid`. Lowercase letters, digits, `-` and `_`.
3. A label for this machine, for example `laptop`. It must not be empty and must not contain `<`, `>` or `/`. Other machines will use the same label for this computer.
4. Which agent kind will run the orchestrator: Claude Code or Codex? Claude reads `CLAUDE.md`, which imports `AGENTS.md`. Codex reads `AGENTS.md`.
5. Do they already keep global rules (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`)? Those are left alone. The agent loads them itself where its tool does.

## Steps
Every script below is a dry run until you add `--apply`. Run it without `--apply`, show the output, and add `--apply` only after a yes.
1. Config: `<repo>/scripts/write-config.sh --home <home> --orchestrator <name> --label <label>`. It checks the three values (a placeholder such as `<machine-label>` is refused), shows a diff, and backs up an old config.
2. Home folder: `<repo>/scripts/init-home.sh <home>`. The dry run lists every folder and file it would create. It makes `tasks/` and `done/` and copies `AGENTS.md`, `CLAUDE.md` (which contains `@AGENTS.md`), `board.md`, `journal.md`, `spaces.md` and `task-template.md`. An existing file is diffed and backed up first. Copy `templates/profiles.md` later if profiles are wanted (see `herdr-profiles`).
3. Fill `<home>/spaces.md` with the spaces the person has, as a guess they can correct. Add the person's own rules to `<home>/AGENTS.md` if they want; it is their copy.
4. **Start and name the orchestrator before anything else runs against herdr.** See "Start and restart" below. The watcher skips only an agent with the exact configured name, and `herdr-agents --apply` (and the watcher) give unnamed agents a default name, which would also rename an unnamed orchestrator pane.

## Start and restart
The orchestrator is an ordinary agent in a herdr pane, started in the home folder.
1. Open a pane in the home folder: `herdr pane split --cwd <home>` (or `cd <home>` in a pane).
2. Start the agent and give it the name from the config. Either start it by hand (`claude` or `codex`) and, from another pane, `herdr agent rename <pane-id> <name>`; or from another pane run `herdr agent start <name> --kind claude --pane <pane-id>` (use `--kind codex` for Codex). The target pane must be at a shell prompt.
3. First message: "Read AGENTS.md, board.md, spaces.md and profiles.md, then follow the After a restart section."
4. Restart: close the agent, start it again the same way in the same folder. It rebuilds its picture from the files; nothing else is needed. Agent names are cleared when an agent exits, so rename it every time.

(Pane and agent commands above come from `herdr --help` output and were not run during this build.)

## Verify
`python3 <repo>/skills/orchid-watcher/orchid_watcher.py --check` prints the config and says whether the orchestrator agent is running. `python3 <repo>/skills/orchid-doctor/doctor.py` shows OK for config, home folder and files. With no config both say `config not found`.

## Undo
Delete `<home>` only if the person says so; it holds their records. Delete `~/.config/orchid/config` to unset the location. Overwritten files can be restored from their `.orchid-bak-*` backups.
