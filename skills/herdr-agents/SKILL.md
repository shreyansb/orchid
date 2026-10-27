---
name: herdr-agents
description: Print one table of all herdr agents (this machine and saved remote machines) with machine, space, pane, name, kind, status, directory and task. Use when the user asks to list, show or orchestrate herdr agents.
---

# herdr-agents

## What it does
Lists every agent in herdr on this machine and on every enabled saved machine, in one table. It also gives each unnamed agent a name (`<space>-p<N>`) and remembers names, so an agent keeps its name after a restart in the same pane.

## Questions
None. It is read-mostly. Naming changes only agent names in herdr, which the person should know about: the first run renames unnamed agents. Say so before the first run.

## Steps
1. Run `python3 -I <repo>/skills/herdr-agents/herdr_agents.py` and show the table as is. `<repo>` is the folder this repo was cloned to.
2. Add `--json` for machine-readable output, `--local` for this machine only, `--quiet` to rename without printing the table.
3. To act on a remote agent: `herdr --machine "<machine-label>" agent prompt <name-or-pane> "<text>" --wait`. Local agents need no `--machine`.
4. Do not rename, prompt or stop an agent unless the user asks.

## Config
Reads `~/.config/orchid/config` (or `ORCHID_CONFIG`) for `machine_label`, the label of this machine. Without a config the label is `local`. Saved names are in `names.json` next to the config.

## Verify
The table shows at least this machine's agents. Remote machines appear if `herdr machine list` shows them enabled and reachable. Unreachable machines print a WARNING line.

## Undo
Nothing to remove except `names.json` (saved names). Agent names set in herdr can be cleared with `herdr agent rename <target> --clear`. To unlink the skill: `<repo>/scripts/link-skill.sh herdr-agents --to claude --uninstall --apply` (or `--to codex`).

## Install this skill
`<repo>/scripts/link-skill.sh herdr-agents --to claude` (dry run), then add `--apply` after the person agrees.
