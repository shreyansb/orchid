# Profiles

| Profile | Kind | Environment | Start command | Contexts | Machines | Verify |
|---|---|---|---|---|---|---|
| `work` | claude | `CLAUDE_CONFIG_DIR=~/.claude-work` | `claude-work` | work | `laptop`, `workstation` | `CLAUDE_CONFIG_DIR=~/.claude-work claude auth status` |
| `personal` | codex | `CODEX_HOME=~/.codex-personal` | `codex-personal` | personal | `laptop` | `CODEX_HOME=~/.codex-personal codex login status` |

Logins are per machine. `work` needs one sign-in on the laptop and one on the workstation.
