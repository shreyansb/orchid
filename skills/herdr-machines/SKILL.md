---
name: herdr-machines
description: Check SSH and Tailscale, save another computer in herdr with `herdr machine add`, and set this machine's label. Use when the user wants agents on more than one computer.
---

# herdr-machines

## What it does
Connects this herdr to other computers over SSH so their spaces and agents show up here and can be driven with `herdr --machine <label>`. Sets the label this machine uses in the orchid config. Background: `docs/machines.md`.

## Questions
1. Which other computers? For each: the SSH target (a host name from `~/.ssh/config`, or `user@host`) and a short label. Labels must not contain "/".
2. Is each one reachable now? If they are on different networks, does the person already use a mesh VPN such as Tailscale? Do not install one for them; offer the link and let them choose.
3. A label for this machine (written to the config).

## Steps
1. Check herdr: `herdr --version`. `herdr machine` needs 0.9 or later. If older, tell the person to update herdr; do not update it yourself unless they ask.
2. For each target, check SSH without prompts: `ssh -o BatchMode=yes -o ConnectTimeout=8 <target> true`. If it fails, stop and explain: keys, Remote Login on macOS (System Settings > General > Sharing), or network. The person does these by hand.
3. Check herdr on the remote: `ssh <target> 'command -v herdr && herdr --version'`. If missing, tell the person; do not install it.
4. Save it: `herdr machine add <ssh-target> --label <label>`. If it asks to stop or replace a remote server, stop and ask the person. That ends running agents there. The answer defaults to No; never answer Yes for them.
5. Write this machine's label into the config: copy `<repo>/templates/config` with `<repo>/scripts/safe-write.sh` (dry run first), then set `machine_label=`. If the config already exists, show the diff and ask.
6. Repeat on each remote machine for its own label (a remote machine needs herdr and the config only if it will run the orchestrator or the herdr-agents skill).

## Verify
`herdr machine list` shows each label enabled. `herdr machine status` shows reachable. `herdr --machine <label> agent list` returns JSON. The `herdr-agents` skill lists agents from every machine.

## Undo
`herdr machine remove <label>` removes the saved profile. It does not stop anything on the remote machine. The config label can be restored from the `.orchid-bak-*` backup next to it.
