# Profiles

A profile is one login: an agent kind plus the environment that selects its credentials. People keep several: a work subscription and a personal one, two Claude accounts, Claude and Codex side by side. Orchid's job is to start each piece of work under the right one, and to check.

## What is verified

Checked on a real machine with Claude Code and Codex CLI installed:

| Fact | How it was checked |
|---|---|
| `CLAUDE_CONFIG_DIR=<dir>` selects a separate Claude Code login | With a new empty directory, `claude auth status` reports `"loggedIn": false`, while the default login reports true |
| `claude auth status` prints JSON with `loggedIn` | Run it |
| `CODEX_HOME=<dir>` selects a separate Codex home, and the folder must already exist | Pointing it at a missing folder gives an error that says the path does not exist |
| `codex login status` prints the login state | Run it |
| `herdr agent start` can start many agent kinds, including `claude` and `codex` (24 on herdr 0.9.5) | `herdr agent start --help` lists them |
| `herdr pane split`, `herdr tab create` and `herdr workspace create` accept `--env KEY=VALUE` | `--help` on herdr 0.9.5 |

## What is not verified

- Profile environments for any kind other than Claude Code and Codex. The kinds list in `herdr agent start --help` is what herdr can start; whether each one has a per-login environment variable is not checked. Add a row to `profiles.md` only after you confirm it.
- Where credentials are stored for a given config folder (file or system keychain), and whether copying a folder to another machine would work. Do not copy credentials between machines; sign in on each one.
- Codex skill folder location (`~/.codex/skills`) is the documented convention but was not tested with orchid's skills.

## How orchid uses profiles

1. `profiles.md` in your home folder lists each profile: kind, environment, launcher command, contexts, machines, verify command.
2. When the orchestrator starts an agent for a context, it creates the pane with the profile's environment:
   `herdr pane split --current --env CLAUDE_CONFIG_DIR=<dir> --no-focus`, then
   `herdr agent start <name> --kind claude --pane <pane-id>`.
   `agent start` needs a pane at a plain shell prompt, so the environment must be set when the pane is created, not typed later.
3. It runs the verify command with the same environment variable (`claude auth status` or `codex login status`) on the machine where the agent runs, and checks the result before sending work. On a remote machine that means over SSH, or by asking the new agent to run it. The command shows the login the profile selects; it does not read the agent's own screen.
4. For a remote machine, the pane and agent steps run with `herdr --machine <label> ...`. The profile's directory is on that machine.

## Paths: use `$HOME` or a full path

A `~` only expands when it is unquoted and at the start of a word. Inside quotes it stays a literal `~`, and the tool then looks for (or creates) a folder named `~`. So `profiles.md` and every command use `$HOME/.claude-<name>` or a full path. `make-launcher.sh` expands a leading `~` itself and writes the full path into the launcher. For `herdr ... --env KEY=VALUE`, give the full path: herdr is assumed to pass the value as given (not tested).

## Launchers

A launcher is a two-line script so you can type one command: `CLAUDE_CONFIG_DIR=<full-path> exec claude "$@"`. `skills/herdr-profiles/make-launcher.sh` writes it to `~/.local/bin/<name>`. It never edits shell startup files. If `~/.local/bin` is not on your PATH, add it yourself or use the full path.

## First sign-in

Each profile needs one interactive sign-in per machine, done by the person in a browser: run the launcher, then log in. Orchid cannot and should not do this for you.

## Subscriptions and terms

Each tool's terms decide what a subscription login may be used for, including use by scripts or other agents. Read them. Orchid starts the vendor's own CLI under its own login; it does not read, copy or relay credentials.
