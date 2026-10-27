# Profiles

One row per login. A profile is an agent kind plus the environment that selects its login.
Work for a context runs only under the profile listed for it. See `docs/profiles.md`.

| Profile | Kind | Environment | Start command | Contexts | Machines | Verify |
|---|---|---|---|---|---|---|
| `<profile-name>` | claude | `CLAUDE_CONFIG_DIR=$HOME/.claude-<profile-name>` | `<launcher-command>` | `<context>` | `<machine-label>` | `CLAUDE_CONFIG_DIR=$HOME/.claude-<profile-name> claude auth status` |
| `<profile-name>` | codex | `CODEX_HOME=$HOME/.codex-<profile-name>` | `<launcher-command>` | `<context>` | `<machine-label>` | `CODEX_HOME=$HOME/.codex-<profile-name> codex login status` |

Notes
- Write folders as `$HOME/...` or a full path, never `~` inside quotes: a quoted `~` is not expanded and the shell then looks for a folder literally named `~`. In `herdr ... --env` use the full path (herdr passes the value as given; assumed, not tested).
- Logins are per machine. A profile that exists on two machines needs a sign-in on each.
- Remove the rows you do not use. Add one per login.
- A default login (plain `claude` or `codex`) is also a profile. List it if you use it.
