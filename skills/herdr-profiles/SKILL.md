---
name: herdr-profiles
description: Set up one login per context (CLAUDE_CONFIG_DIR for Claude Code, CODEX_HOME for Codex), write profiles.md, make launcher commands, and verify the login. Use when the user has more than one account or subscription.
---

# herdr-profiles

## What it does
Lets the person keep several logins side by side, and start work under the right one. A profile is an agent kind plus the environment variable that selects its login. Background and what was verified: `docs/profiles.md`.

## Questions
1. Which logins do they have? For each: a name, the kind (`claude` or `codex`), and which context it is for (for example work, personal).
2. Which machines does each profile live on? Logins are per machine.
3. Config folder per profile. Suggest `~/.claude-<name>` or `~/.codex-<name>`. Does an existing one already exist? If so, use it; do not move it.
4. Do they want a launcher command per profile (a tiny script in `~/.local/bin`)?
5. Other agent kinds (herdr can start many)? Only Claude Code and Codex have a verified per-login environment. For others, say it is unverified and ask whether to add a row anyway.

## Steps
1. Make sure the home folder exists (see `orchid-tasks`). Copy `<repo>/templates/profiles.md` to `<home>/profiles.md` with `<repo>/scripts/safe-write.sh` (dry run, show, then `--apply` after a yes). Fill in the rows the person gave. Remove rows they do not use.
2. For each launcher the person wants, dry run first:
   `<repo>/skills/herdr-profiles/make-launcher.sh <command-name> claude <config-dir>`
   Show the output. After a yes, add `--apply`. The script refuses if the command or file exists. It does not edit shell startup files. If `~/.local/bin` is not on PATH, say so; the person adds it or uses the full path.
3. First sign-in is the person's: they run the launcher and log in through the browser. Do not try to do this for them. For Codex the folder must exist before first use; the launcher script creates it.
4. Verify each profile (below).
5. Tell the person the rule the orchestrator will follow: work for a context starts only under its profile, with the profile's environment set when the pane is created.

## Verify
- Claude: `CLAUDE_CONFIG_DIR=<dir> claude auth status`. Check `"loggedIn": true` and that it is the account the person expects.
- Codex: `CODEX_HOME=<dir> codex login status`.
- A new empty folder reports not logged in. That means the selection works and the person still has to sign in.

## Undo
Delete the launcher (`rm ~/.local/bin/<command-name>`), restore `profiles.md` from its `.orchid-bak-*` backup or delete it. Config folders hold logins; do not delete them unless the person says so. Signing out: `claude auth logout` with the same environment variable.
