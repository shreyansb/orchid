#!/usr/bin/env python3
"""Read-only health check for an orchid setup. It changes nothing.

    doctor.py            human-readable report
    doctor.py --json     same, as JSON

Each check prints OK, WARN or FAIL, or SKIP when the feature is not installed. WARN and SKIP
do not fail the run; the exit code is 1 only when a FAIL is found.
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "lib"))
import orchid_config  # noqa: E402
import orchid_tasks  # noqa: E402

RESULTS = []


def add(level, name, detail=""):
    RESULTS.append({"level": level, "check": name, "detail": detail})


def run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", str(e)


def check_tools():
    v = sys.version_info
    add("OK" if v >= (3, 8) else "FAIL", "python3", platform.python_version())
    code, out, _ = run(["herdr", "--version"])
    if code:
        add("FAIL", "herdr", "not found on PATH")
        return False
    m = re.search(r"(\d+)\.(\d+)", out)
    old = m and (int(m.group(1)), int(m.group(2))) < (0, 9)
    add("WARN" if old else "OK", "herdr", out + ("  (herdr machine needs 0.9 or later; not verified for older)" if old else ""))
    for tool in ("claude", "codex", "gh", "git"):
        path = shutil.which(tool)
        add("OK" if path else "SKIP", tool, path or "not installed (only needed if you use it)")
    return True


def check_config():
    state, message, cfg = orchid_config.status()
    if state == "missing":
        add("WARN", "config", message + " (tasks and watcher need it)")
        return None
    if state == "invalid":
        add("FAIL", "config", message)
        return None
    add("OK", "config", str(orchid_config.config_path()))
    home = cfg["home"]
    if not home.is_dir():
        add("FAIL", "home folder", "%s does not exist" % home)
        return cfg
    add("OK", "home folder", str(home))
    for f in ("AGENTS.md", "board.md", "journal.md"):
        add("OK" if (home / f).exists() else "WARN", "home/" + f, "" if (home / f).exists() else "missing")
    add("OK" if (home / "tasks").is_dir() else "WARN", "home/tasks", "")
    claude_md = home / "CLAUDE.md"
    if claude_md.exists():
        ok = "@AGENTS.md" in claude_md.read_text()
        add("OK" if ok else "WARN", "home/CLAUDE.md imports AGENTS.md", "")
    return cfg


def check_machines(cfg):
    code, out, err = run(["herdr", "machine", "list", "--json"])
    if code:
        add("WARN", "herdr machines", err or "could not list")
        return
    try:
        machines = json.loads(out or "[]")
    except ValueError:
        add("WARN", "herdr machines", "unreadable output")
        return
    if not machines:
        add("SKIP", "saved machines", "none saved (single-machine setup)")
        return
    labels = [m["label"] for m in machines]
    bad = [l for l in labels if "/" in l]
    add("FAIL" if bad else "OK", "machine labels", ", ".join(labels) + ("  (a label must not contain '/')" if bad else ""))
    code, out, _ = run(["herdr", "machine", "status", "--json"], timeout=60)
    try:
        for s in json.loads(out or "[]"):
            name = s.get("label") or s.get("id")
            state = str(s.get("status") or s.get("state") or s)
            add("OK" if "reach" in state.lower() or state.lower() in ("ok", "ready") else "WARN",
                "machine " + str(name), state)
    except (ValueError, AttributeError):
        add("WARN", "machine status", "could not read `herdr machine status --json`")


def check_watcher(cfg):
    if platform.system() != "Darwin":
        add("SKIP", "watcher", "macOS only; a systemd unit is future work")
        return
    label = "dev.orchid.watcher"
    code, out, _ = run(["launchctl", "print", "gui/%d/%s" % (os.getuid(), label)])
    if code:
        add("SKIP", "watcher", "not installed")
        return
    running = "state = running" in out
    add("OK" if running else "WARN", "watcher job", "running" if running else "loaded but not running")
    log = orchid_config.state_dir() / "watcher.log"
    add("OK" if log.exists() else "WARN", "watcher log", str(log))
    wakes = orchid_config.wakes_path()
    add("OK" if wakes.exists() else "SKIP", "wakes.log", str(wakes) if wakes.exists() else "not written yet (no wake so far)")


def check_skills():
    for base in (Path.home() / ".claude/skills", Path.home() / ".codex/skills"):
        if not base.is_dir():
            continue
        for skill in sorted((REPO / "skills").iterdir()):
            link = base / skill.name
            if link.is_symlink() and Path(os.readlink(str(link))) == skill:
                add("OK", "skill " + skill.name, "linked in %s" % base)


def check_profiles(cfg):
    if not cfg:
        return
    p = cfg["home"] / "profiles.md"
    if not p.exists():
        add("SKIP", "profiles.md", "not set up")
        return
    add("OK", "profiles.md", str(p))
    text = p.read_text()
    for var, kind in (("CLAUDE_CONFIG_DIR", "claude"), ("CODEX_HOME", "codex")):
        for d in sorted(set(re.findall(var + r"=(\S+)", text))):
            path = Path(os.path.expandvars(os.path.expanduser(d.strip('"\''))))
            if path.is_dir():
                add("OK", "profile dir " + d, "exists (login not checked here; run the verify command in profiles.md)")
            else:
                add("WARN", "profile dir " + d, "does not exist on this machine")


def check_test_task():
    """Simulate a task in a temporary folder and make sure the parser finds its owner.
    Nothing is written to the home folder."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "T000.md").write_text(
            "---\nid: T000\ntitle: doctor test\nstatus: running\nagents: <label>/test-agent\n---\n")
        found = orchid_tasks.open_tasks(d)
    ok = found == {("<label>", "test-agent"): ("T000", "doctor test")}
    add("OK" if ok else "FAIL", "task parser (simulated task)", "" if ok else str(found))


def main():
    have_herdr = check_tools()
    cfg = check_config()
    if have_herdr:
        check_machines(cfg)
    check_watcher(cfg)
    check_skills()
    check_profiles(cfg)
    check_test_task()
    if "--json" in sys.argv:
        print(json.dumps(RESULTS, indent=2))
    else:
        for r in RESULTS:
            print("%-5s %-34s %s" % (r["level"], r["check"], r["detail"]))
    return 1 if any(r["level"] == "FAIL" for r in RESULTS) else 0


if __name__ == "__main__":
    sys.exit(main())
