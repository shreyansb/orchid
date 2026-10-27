---
name: orchid-watcher
description: Install the background watcher that names new agents and writes a wake line to wakes.log when a worker settles (macOS launchd). Use when the user wants the orchestrator to react without being asked.
---

# orchid-watcher

## What it does
A small Python script run by launchd. It (1) names new agents on this machine, and (2) polls this machine and every saved machine, and appends one line to `wakes.log` when an agent that owns an open task settles, sits in `unknown`, or freezes. The watcher never types into an agent and sends no notification. The orchestrator reads the file with a Monitor. Rules and timings: `docs/tasks.md`. It needs a valid config and a home folder (`orchid-tasks`); with no config, or an invalid one, it refuses to start. It runs `herdr_agents.py --apply` to name new agents.

The installer is macOS only. The script and the log path (`~/.config/orchid/wakes.log`, next to the config) are the same on Linux, but a systemd unit is future work and Linux is not tested.

## Before you start
The orchestrator agent must already be running and named exactly as in the config (see `orchid-tasks`, "Start and restart"). The watcher names unnamed agents, and it would also name an unnamed orchestrator pane `<space>-p<N>`. Without the right name the watcher cannot skip the orchestrator, and it may write wakes about the orchestrator itself.

## Questions
1. Is the orchestrator on this machine? One watcher is enough for all machines; install it on the orchestrator's machine only.
2. Is this computer one that sleeps? The watcher writes no wakes while it sleeps. Tell them.
3. OK to keep a background job running? It starts at login and restarts if it stops.

## Steps
1. Check the config exists and names the right home, orchestrator and label: `python3 <repo>/skills/orchid-watcher/orchid_watcher.py --check`. It prints the open tasks and whether each owner agent is found. It changes nothing.
2. Dry run the install: `sh <repo>/skills/orchid-watcher/install.sh`. It renders the launchd plist, runs `plutil -lint`, and prints what it would do. The job's PATH includes the folder of the `herdr` it found, `/opt/homebrew/bin`, `/usr/local/bin` and `~/.local/bin`.
3. If a plist already exists and differs, the script prints a diff and backs it up before changing it.
4. After a yes: `sh <repo>/skills/orchid-watcher/install.sh --apply`.
5. The repo must stay where it is. The job runs the script from this folder. If the repo moves, run the install again.

## Verify
`launchctl list | grep dev.orchid.watcher` shows the job. The log is `~/.config/orchid/watcher.log` (next to the config). Check it for lines starting `wake:` and for errors. Then run the end-to-end test: with the person's yes, create a throwaway task in `<home>/tasks/` with `status: running` and `agents: <label>/<test-agent>`, start a small test agent, let it finish a short prompt, and watch for a `wake: written` log line and a new line at the end of `~/.config/orchid/wakes.log`. Delete the test task and close the test agent afterward.

## Orchestrator side
The orchestrator must read the file, or nothing reacts to a wake. Its `AGENTS.md` (from `templates/AGENTS.md`) holds the rules: at session start arm a Monitor on `tail -n 0 -F <config folder>/wakes.log` (30 minutes at most, arm again on expiry) and read the file for missed lines. It sends a `PushNotification` only when it has a message for the user.

## Undo
`sh <repo>/skills/orchid-watcher/install.sh --uninstall` (dry run), then add `--apply`. It stops the job and moves the plist aside (`.orchid-removed-<time>`) instead of deleting it.
