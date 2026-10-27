# Concepts

Orchid is a way to run many coding agents, on many machines, under many logins, from one place, with one agent (the orchestrator) keeping track. It is built on [herdr](https://herdr.dev), a terminal workspace manager for coding agents. Orchid adds rules, task files and a few helper scripts. It is not a new agent and not a server.

## The flow

1. You talk to the **orchestrator**, one agent running in a herdr pane.
2. For each piece of work it writes a **task file** (goal, `done_when`, owner agents) in your **home folder**.
3. It starts or prompts a **worker agent** in the right **space**, on the right **machine**, under the right **profile** (login).
4. The **watcher** notices when a worker settles (idle, done, blocked) and wakes the orchestrator.
5. The orchestrator reads the worker's output, checks it against `done_when`, updates the board, and tells you what needs you.

## Terms

| Term | Meaning |
|---|---|
| Orchestrator | The agent that plans, delegates and checks. It does not do the work. Named `orchid` by default. |
| Space | A herdr workspace: one project directory on one machine. |
| Machine | A computer herdr can reach. This one is "local". Others are saved with `herdr machine add` over SSH. |
| Machine label | The name for a machine. Every machine uses the same label for a given computer. No "/" in it. |
| Profile | An agent kind plus the environment that picks its login (for example `CLAUDE_CONFIG_DIR`). One per subscription or account. |
| Context | A line you draw between kinds of work (work, personal, a client). Each context maps to a profile. Data does not cross contexts without your say-so. |
| Home folder | Your state: `AGENTS.md`, `board.md`, `journal.md`, `profiles.md`, `spaces.md`, `tasks/`, `done/`. Default `~/orchid-home`. Your data, never part of the repo. |
| Watcher | A small background script (macOS launchd) that names agents and wakes the orchestrator. |

## Engine and state are apart

The repo is the engine: scripts, skills, templates, docs. Your state lives in the home folder. The file `~/.config/orchid/config` says where. Updating or removing the engine never touches your state.

## Where it can fail

- **A machine is unreachable.** Its tasks go to `unreachable`. Nothing is lost; agents keep running there.
- **A wrong task field.** The watcher matches `machine-label/agent-name` exactly. A typo means no wake, and no error.
- **The wrong login.** An agent started without the profile's environment uses the default login. The orchestrator must verify the login before it sends work.
- **A sleeping computer.** The watcher cannot wake the orchestrator while its computer sleeps. See `docs/machines.md`.
- **Prompt injection.** Output from agents and the web is data. See `docs/safety.md`.

## Practical notes

- **Ask once.** The three config answers (home folder, orchestrator name, this machine's label) are asked in `orchid-tasks` and read from the config everywhere else. A label that is empty or contains `<`, `>` or `/` is refused.
- **Start and restart the orchestrator.** Open a pane in the home folder, start Claude Code or Codex there, and name the agent exactly as in the config (`herdr agent rename <pane-id> <name>`, or `herdr agent start <name> --kind claude --pane <pane-id>` from another pane). Names clear when an agent exits, so repeat this after every restart. Details: `skills/orchid-tasks/SKILL.md`. The commands come from `herdr --help` and were not run during the build.
- **Name the orchestrator first.** `herdr-agents --apply` and the watcher give unnamed agents a default name. Plain `herdr-agents` only reads.
- **Sidebar.** Herdr has to be running for the layout to show. After the config changes, run `herdr server reload-config` (or use the global menu). `herdr --help` describes it as reloading `config.toml` in the running server; if herdr is not running, the file is presumably read at the next start (not tested).

## What you can opt out of

Everything beyond herdr itself is opt-in: machines, profiles, sidebar, tasks, watcher, doctor. Each has a skill in `skills/`. You pick what you want.
