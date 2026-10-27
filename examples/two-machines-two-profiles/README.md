# Example: two machines, two profiles

A laptop runs the orchestrator. A workstation runs worker agents. There are two contexts, each with its own login.

All names are placeholders. Replace them with yours.

| Piece | Value |
|---|---|
| Machines | `laptop` (orchestrator, local), `workstation` (saved over SSH) |
| Profiles | `work` (Claude Code, `~/.claude-work`), `personal` (Codex, `~/.codex-personal`) |
| Contexts | `work` -> profile `work`; `personal` -> profile `personal` |

## Files

- `config`: the orchid config for the laptop. Install as `~/.config/orchid/config`. On the workstation, the same file with `machine_label=workstation` is only needed if you run `herdr-agents` there.
- `profiles.md`, `spaces.md`: copy to the home folder and adapt.
- `tasks/T001.md`: an open task with two agents on two machines. The watcher reads the `agents:` line.

## Setup order

1. `herdr-machines`: save `workstation` with `herdr machine add <ssh-target> --label workstation`.
2. `herdr-profiles`: make the `work` and `personal` launchers; sign in to each once on each machine that uses it.
3. `orchid-tasks`: create the home folder and start the orchestrator in it.
4. `orchid-watcher`, then `orchid-doctor`.
