---
name: herdr-sidebar
description: Add orchid's compact agent sidebar rows ([ui.sidebar.agents]) to the herdr config safely, with a diff and a backup. Use when the user wants a one-line-per-agent sidebar.
---

# herdr-sidebar

## What it does
Shows one line per agent in herdr's sidebar: a state icon and the agent name. Because orchid names agents `<space>-<purpose>`, the line already shows where the agent runs. It adds a small `[ui.sidebar.agents]` block to `~/.config/herdr/config.toml`.

## Questions
1. Does the person want this layout? It is cosmetic. Skip if they say no.
2. Is the herdr config in the default place (`~/.config/herdr/config.toml`)? If not, ask for the path.

## Steps
1. Dry run: `python3 <repo>/skills/herdr-sidebar/merge_sidebar.py` (add `--config <path>` if needed). It prints a diff and changes nothing.
2. If it reports that the config already sets `sidebar.agents`, stop. It prints both versions. Merging is the person's decision; offer to explain the difference. Do not edit the file.
3. If the diff looks right and the person says yes, run it again with `--apply`. It backs up the config first (`config.toml.orchid-bak-<time>`) and appends the block.
4. Reload: herdr's global menu, or `herdr server reload-config`.

## Verify
`grep -n "sidebar.agents" ~/.config/herdr/config.toml` shows the block. The sidebar shows one line per agent after reload. If herdr reports a config error, restore the backup immediately.

## Undo
Copy the `.orchid-bak-*` file back over `config.toml`, or delete the three lines of the block. Reload the config.
