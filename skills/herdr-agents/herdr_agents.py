#!/usr/bin/env python3
"""Print one table of every herdr agent on this machine and all enabled saved machines.

Each agent gets one name. Herdr clears a name when its agent exits, so names are saved in
names.json (next to the orchid config), keyed by machine label and pane, and put back on the
next run. Unnamed agents get "<space>-p<N>" as a default.

Flags: --local (this machine only), --json, --quiet (rename only, print warnings).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
import orchid_config  # noqa: E402

NAME_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")


def herdr(*args, machine=None, raw=False):
    cmd = ["herdr"] + (["--machine", machine] if machine else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout if raw else json.loads(r.stdout)


def default_name(space, pane):
    slug = re.sub(r"[^a-z0-9_-]+", "-", space.lower()).strip("-") or "agent"
    return "%s-p%s" % (slug[:28], pane.split(":p")[-1])


def collect(label, machine, registry, errors):
    spaces = {w["workspace_id"]: w["label"]
              for w in herdr("workspace", "list", machine=machine)["result"]["workspaces"]}
    agents = herdr("agent", "list", machine=machine)["result"]["agents"]
    used = {a["name"] for a in agents if a.get("name")}
    rows = []
    for a in agents:
        pane, space = a["pane_id"], spaces.get(a["workspace_id"], a["workspace_id"])
        key, name = "%s|%s" % (label, pane), a.get("name")
        if name:
            registry[key] = name
        else:
            want = registry.get(key)
            if not want or want in used or not NAME_RE.fullmatch(want):
                want = default_name(space, pane)
            if want in used:
                errors.append("%s %s: name %s is in use" % (label, pane, want))
                name = "-"
            else:
                try:
                    herdr("agent", "rename", pane, want, machine=machine, raw=True)
                    name = registry[key] = want
                    used.add(want)
                except Exception as e:
                    errors.append("%s %s: rename failed: %s" % (label, pane, e))
                    name = "-"
        mine = machine is None and pane == os.environ.get("HERDR_PANE_ID")
        rows.append({
            "name": name + (" (me)" if mine else ""), "machine": label, "space": space,
            "pane": pane, "kind": a.get("agent") or "?",
            "status": a.get("agent_status") or "unknown",
            "cwd": (a.get("cwd") or "").replace(str(Path.home()), "~"),
            "task": a.get("terminal_title_stripped", ""),
        })
    return rows


def saved_machines():
    r = subprocess.run(["herdr", "machine", "list", "--json"], capture_output=True, text=True)
    try:
        return [m for m in json.loads(r.stdout or "[]") if m.get("enabled")]
    except ValueError:
        return []


def main(argv):
    cfg = orchid_config.load()
    registry_path = orchid_config.state_dir() / "names.json"
    try:
        registry = json.loads(registry_path.read_text())
    except (OSError, ValueError):
        registry = {}

    targets = [(cfg["machine_label"], None)]
    if "--local" not in argv:
        targets += [(m["label"], m["label"]) for m in saved_machines()]

    rows, errors = [], []
    for label, machine in targets:
        try:
            rows += collect(label, machine, registry, errors)
        except Exception as e:
            errors.append("%s: %s" % (label, e))

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True))

    if "--quiet" in argv:
        for e in errors:
            print("WARNING  %s" % e, file=sys.stderr)
        return
    if "--json" in argv:
        print(json.dumps({"agents": rows, "errors": errors}, indent=2))
        return

    cols = ["name", "machine", "space", "pane", "kind", "status", "cwd", "task"]
    w = {c: max([len(c)] + [len(r[c]) for r in rows]) for c in cols}

    def line(r):
        return " | ".join(r[c].ljust(w[c]) for c in cols)

    print(line({c: c.upper() for c in cols}))
    print("-+-".join("-" * w[c] for c in cols))
    for r in rows:
        print(line(r))
    for e in errors:
        print("WARNING  %s" % e, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
