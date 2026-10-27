# Machines

Orchid uses herdr's saved SSH machines. Orchid does not run its own connection layer.

## What herdr provides (verified against herdr 0.9.5 help text and its bundled agent guide)

- `herdr machine add <ssh-target> --label <label>` prepares the remote herdr server and saves a profile. `--remote-session <name>` picks a named remote session; without it, non-interactive setup uses the remote default session.
- `herdr machine list [--json]`, `status [--json]`, `rename`, `remove`, `enable`, `disable`, `reconnect`.
- `herdr --machine <label> <command>` runs a command against a saved machine, with no open client needed. Example: `herdr --machine <label> agent list`.
- Both installs must support machine forwarding. The remote server must already be running. Forwarding never installs, starts or restarts a remote server.
- `machine add` asks before it stops an incompatible remote server. The default answer is No. Do not approve this for the person; it ends the agents running in that session.
- `machine reconnect` needs the person to finish SSH authentication in their own terminal.

Not verified here: behavior on Windows (herdr's docs say multi-machine is not supported there at the time of writing; check before relying on it).

## What you need

1. **SSH access** from the orchestrator machine to each other machine, with key login so nothing prompts. Test with `ssh <host> true`.
2. **herdr** installed on every machine, on versions that support `herdr machine` (0.9 or later; older versions did not have it).
3. A **label** for each machine. Use the same label everywhere. Do not put "/" in it; task files use `label/agent`.
4. **Reachability.** The machines must reach each other. On one network, plain hostnames work. Across networks, a mesh VPN such as Tailscale gives each machine a stable name. Orchid does not need Tailscale, and it does not configure it.

On macOS, turn on SSH under System Settings > General > Sharing > Remote Login. This needs the person's click or an admin password; orchid does not do it.

## Steps

1. On the orchestrator machine, the config (with this machine's label) comes from the `orchid-tasks` skill. Worker machines need no config.
2. On the orchestrator machine: `herdr machine add <ssh-target> --label <label>` for each other machine.
3. Check: `herdr machine status`, then the `herdr-agents` skill, which lists agents on all machines.

## Keeping a machine reachable

An always-on machine must not sleep, and must come back after a power cut. On macOS, `sudo pmset -a sleep 0` stops system sleep and `sudo pmset -a autorestart 1` restarts after power loss (both checked with `pmset -g` on a real machine). If FileVault is on, a restart waits at the disk password screen, and nothing starts until someone types it. That is a trade-off between disk encryption and unattended recovery; it is the person's decision. The orchestrator's own computer must be awake for the watcher to wake it.

## When a machine cannot be reached

Set up the machines you can reach and skip the others. `herdr machine add` does not save a profile when setup fails or is cancelled (seen with a version-upgrade prompt that was declined: "machine was not saved"), so there is nothing to undo. Add the machine later when SSH works. Tasks that name an unreachable machine go to `unreachable`; nothing is lost. A guessed or fake host name fails the SSH check in step 1 of the `herdr-machines` skill and goes no further.

## herdr must exist on the remote first

`machine add` prepares the remote herdr server, so herdr has to be installed there. herdr's docs say a missing or incompatible install needs your approval, and the default answer is No (not run here). A too-old running server was observed: the command refused and said it needed an interactive terminal to approve stopping the server, which ends the agents in it. Orchid never answers that question for you. Install or update herdr on the remote yourself, or approve it in your own terminal.

## Worker machines need no orchid scripts

A worker machine needs herdr and its own agent logins. It does not need the watcher, the orchid repo, a config file or any skill: the label other machines use for it is the one saved with `--label`. This holds for Linux workers too. One watcher, next to the orchestrator, polls every saved machine.

## Linux

Everything here works on Linux except the watcher, which uses launchd. A systemd unit is future work. Not tested on Linux.
