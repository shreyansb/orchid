#!/usr/bin/env python3
"""Background helper for orchid. Run it under launchd (see SKILL.md).

1. Naming: subscribes to herdr's event stream and runs herdr_agents.py --local --quiet --apply
   after each agent detection, so every new agent on this machine gets a name.
2. Wake-up: every POLL_SECONDS it lists agents on this machine and on every enabled saved
   machine. When an agent that owns an open task (<home>/tasks) stops working (idle, done, or
   blocked), sits in `unknown` for 30 s, or works with an unchanged screen for 10 min, it
   prompts the orchestrator agent, once the user has been idle for 20 s. The prompt names the
   agent, its state, and the task only. It never includes agent output.

The home folder, orchestrator name and machine label come from the orchid config
(~/.config/orchid/config). Nothing is hard-coded.

    orchid_watcher.py            run the daemon
    orchid_watcher.py --check    print the config and the open tasks, check each owner, exit
"""
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "lib"))
import orchid_config  # noqa: E402
import orchid_tasks  # noqa: E402

SOCK = os.environ.get("HERDR_SOCKET_PATH") or str(Path.home() / ".config/herdr/herdr.sock")
AGENTS_SCRIPT = str(HERE.parent / "herdr-agents" / "herdr_agents.py")
SUBS = [{"type": "pane.agent_detected"}]

POLL_SECONDS = 10
SETTLED = {"idle", "done", "blocked"}
UNKNOWN_SECONDS = 30      # an agent in an unrecognized state this long may sit at a dialog
WAKE_GRACE_SECONDS = 60   # pause after the computer wakes, so links to other machines return
IDLE_SECONDS = 20         # hold a wake until keyboard and mouse have been idle this long
STALL_SECONDS = 600       # working, but the screen has not changed this long


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def herdr_json(*args, machine=None):
    cmd = ["herdr"] + (["--machine", machine] if machine else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return json.loads(r.stdout)


def herdr_text(*args, machine=None):
    cmd = ["herdr"] + (["--machine", machine] if machine else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout


# --- naming ---------------------------------------------------------------

def reconcile():
    r = subprocess.run([sys.executable, "-I", AGENTS_SCRIPT, "--local", "--quiet", "--apply"],
                       capture_output=True, text=True, timeout=60)
    if r.stderr.strip():
        log(r.stderr.strip())


def watch():
    s = socket.socket(socket.AF_UNIX)
    s.connect(SOCK)
    s.sendall((json.dumps({"id": "namer", "method": "events.subscribe",
                           "params": {"subscriptions": SUBS}}) + "\n").encode())
    reconcile()  # catch agents that started while the watcher was down
    for line in s.makefile("r"):
        if '"subscription_started"' in line:
            continue
        reconcile()
    raise ConnectionError("herdr closed the event stream")


# --- wake-up --------------------------------------------------------------

def targets(local_label):
    out = [(local_label, None)]
    try:
        r = subprocess.run(["herdr", "machine", "list", "--json"],
                           capture_output=True, text=True, timeout=30)
        out += [(m["label"], m["label"]) for m in json.loads(r.stdout or "[]") if m.get("enabled")]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return out


def note_activity(key, machine, status, extra, pending):
    """Flag an open-task agent that sits in `unknown`, or works with a frozen screen.
    The screen text is hashed here and never stored or sent."""
    now = time.time()
    if status == "unknown":
        since = extra["unknown"].setdefault(key, now)
        if now - since >= UNKNOWN_SECONDS and key not in extra["flagged"]:
            extra["flagged"].add(key)
            pending[key] = "unknown"
        return
    extra["unknown"].pop(key, None)
    if status != "working":
        extra["screen"].pop(key, None)
        extra["flagged"].discard(key)
        return
    try:
        out = herdr_text("agent", "read", key[1], "--source", "visible", machine=machine)
    except Exception:
        return
    h = hash(out)
    prev = extra["screen"].get(key)
    if not prev or prev[0] != h:
        extra["screen"][key] = (h, now)
        extra["flagged"].discard(key)
    elif now - prev[1] >= STALL_SECONDS and key not in extra["flagged"]:
        extra["flagged"].add(key)
        pending[key] = "stalled"


def user_idle_seconds():
    """Seconds since the last key or mouse input. macOS only (ioreg). Returns a large number
    where it cannot be read, so on other systems no wake is held back."""
    try:
        out = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True, text=True,
                             timeout=10).stdout
        m = re.search(r'"HIDIdleTime" = (\d+)', out)
        return int(m.group(1)) / 1e9 if m else 1e9
    except (OSError, subprocess.TimeoutExpired):
        return 1e9


def poll_once(cfg, seen, pending, down, extra):
    orchestrator = cfg["orchestrator"]
    tasks = orchid_tasks.open_tasks(cfg["home"] / "tasks")
    for label, machine in targets(cfg["machine_label"]):
        try:
            agents = herdr_json("agent", "list", machine=machine)["result"]["agents"]
            down.discard(label)
        except Exception as e:
            if label not in down:
                log("wake: %s unreachable: %s" % (label, e))
            down.add(label)
            continue
        for a in agents:
            name = a.get("name")
            if not name or (name == orchestrator and machine is None):
                continue
            key, status, seq = (label, name), a["agent_status"], a.get("completion_seq", 0)
            prev = seen.get(key)
            seen[key] = (status, seq)
            # Wake only after seeing the agent work, or after its completion counter moves.
            if prev and status in SETTLED and (prev[0] == "working" or seq > prev[1]):
                pending[key] = status
            elif status == "working":
                pending.pop(key, None)
            if key in tasks:
                note_activity(key, machine, status, extra, pending)
    if pending and user_idle_seconds() < IDLE_SECONDS:
        return  # the user may be typing; a wake now would land in their half-typed message
    for key, status in list(pending.items()):
        if key not in tasks:
            del pending[key]
            continue
        tid, title = tasks[key]
        what = {"stalled": "is working, but its screen has not changed for %d min" % (STALL_SECONDS // 60),
                "unknown": "is in an unrecognized state (unknown) and may be showing a dialog"
                }.get(status, "is now %s" % status)
        msg = ("Wake from watcher: agent %s on %s %s (task %s: %s). Read its terminal, check the "
               "result against the task's done_when, update the task file and board, then tell "
               "the user what matters." % (key[1], key[0], what, tid, title))
        try:
            herdr_json("agent", "prompt", orchestrator, msg)
            log("wake: sent for %s (%s, %s)" % (key[1], status, tid))
            del pending[key]
        except Exception as e:
            log("wake: could not prompt %s, will retry: %s" % (orchestrator, e))


def poll_loop(cfg):
    seen, pending, down = {}, {}, set()
    extra = {"unknown": {}, "screen": {}, "flagged": set()}
    last = time.time()
    while True:
        now = time.time()
        if now - last > POLL_SECONDS + 15:
            # The computer slept. Network links need time to come back, and sleep must not
            # count as a stall. Wait, drop the timers, and poll again.
            log("wake: computer slept %d s; waiting %d s before poll" % (now - last, WAKE_GRACE_SECONDS))
            extra["unknown"].clear()
            extra["screen"].clear()
            time.sleep(WAKE_GRACE_SECONDS)
        last = time.time()
        try:
            poll_once(cfg, seen, pending, down, extra)
        except Exception as e:
            log("wake: poll failed: %s" % e)
        time.sleep(POLL_SECONDS)


def check(cfg):
    """Print what the daemon would watch. Changes nothing. Returns the exit code."""
    state, message, _ = orchid_config.status()
    print(message)
    if state != "ok":
        print("The watcher needs a valid config. See skills/orchid-tasks.")
        return 1
    print("config:        %s" % orchid_config.config_path())
    print("home:          %s" % cfg["home"])
    print("orchestrator:  %s" % cfg["orchestrator"])
    print("machine_label: %s" % cfg["machine_label"])
    tasks = orchid_tasks.open_tasks(cfg["home"] / "tasks")
    print("open tasks with owners: %d" % len(tasks))
    live = {}
    for label, machine in targets(cfg["machine_label"]):
        try:
            live[label] = {a.get("name") for a in
                           herdr_json("agent", "list", machine=machine)["result"]["agents"]}
        except Exception as e:
            live[label] = None
            print("  machine %s: unreachable (%s)" % (label, e))
    for (label, agent), (tid, title) in sorted(tasks.items()):
        if label not in live:
            state = "machine label not known"
        elif live[label] is None:
            state = "machine unreachable"
        else:
            state = "agent found" if agent in live[label] else "agent NOT found"
        print("  %s %s/%s: %s" % (tid, label, agent, state))
    orch = live.get(cfg["machine_label"])
    print("orchestrator agent running here: %s" % ("yes" if orch and cfg["orchestrator"] in orch else "no"))
    return 0


def main():
    state, message, cfg = orchid_config.status()
    if "--check" in sys.argv:
        sys.exit(check(cfg))
    if state != "ok":
        log("%s; not starting" % message)
        sys.exit(2)
    threading.Thread(target=poll_loop, args=(cfg,), daemon=True).start()
    while True:
        try:
            watch()
        except Exception as e:
            log("namer: %s; retrying in 5s" % e)
            time.sleep(5)


if __name__ == "__main__":
    main()
