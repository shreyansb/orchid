---
name: herdr-agents
description: Print one table of all herdr agents (this machine and saved remote machines) with machine, space, pane, name, kind, status, directory and task. Use when the user asks to list, show or orchestrate herdr agents.
---

# herdr-agents

## What it does
Lists every agent in herdr on this machine and on every enabled saved machine, in one table. By default it is read-only: unnamed agents are shown with the name they would get (`<space>-p<N>`, marked `*`), and nothing is renamed or saved. With `--apply` it renames them and remembers the names, so an agent keeps its name after a restart in the same pane.

## Questions
Only for `--apply`: does the person want unnamed agents renamed? Name the orchestrator first (see `orchid-tasks`), or `--apply` gives it a default name too. Without `--apply` there is nothing to ask.

## Steps
1. Run `python3 -I <repo>/skills/herdr-agents/herdr_agents.py` and show the table as is. `<repo>` is the folder this repo was cloned to. This changes nothing.
2. To set the proposed names, ask first, then add `--apply`. Other flags: `--json` (machine-readable; each agent has the name it has or would get, and `"applied"` says which), `--local` for this machine only, `--quiet` to print warnings only.
3. To act on a remote agent: `herdr --machine "<machine-label>" agent prompt <name-or-pane> "<text>" --wait`. Local agents need no `--machine`.
4. Do not rename, prompt or stop an agent unless the user asks.

## Config
Reads `~/.config/orchid/config` (or `ORCHID_CONFIG`) for `machine_label`, the label of this machine. Without a config the label is `local`. A config with an invalid label (empty, or with `<`, `>`, `/`) stops the script with exit code 2. Saved names are in `names.json` next to the config, written only with `--apply`. The watcher runs this script with `--apply` to name new agents.

## Verify
The table shows at least this machine's agents. Remote machines appear if `herdr machine list` shows them enabled and reachable. Unreachable machines print a WARNING line. A plain run changes nothing in herdr.

## Undo
Nothing to remove except `names.json` (saved names, only present after `--apply`). Names set with `--apply` can be cleared with `herdr agent rename <target> --clear`. To unlink the skill: `<repo>/scripts/link-skill.sh herdr-agents --to claude --uninstall --apply` (or `--to codex`).

## Install this skill
`<repo>/scripts/link-skill.sh herdr-agents --to claude` (dry run), then add `--apply` after the person agrees.
