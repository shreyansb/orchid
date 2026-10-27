#!/usr/bin/env python3
"""Add the orchid [ui.sidebar.agents] rows to the herdr config without breaking it.

    merge_sidebar.py                        dry run: show the diff, change nothing
    merge_sidebar.py --apply                back up the config, then write
    merge_sidebar.py --config PATH          use another config file (default ~/.config/herdr/config.toml)
    merge_sidebar.py --snippet PATH         use another snippet (default templates/herdr-sidebar.toml)

The script only appends when the config has no active `sidebar.agents` setting at all. If it
finds one, it prints both versions and stops: merging two settings is the person's decision.
Standard library only; works on Python 3.8 and later.
"""
import argparse
import difflib
import re
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ACTIVE = re.compile(r"^\s*(\[\s*ui\.sidebar\.agents[\].]|.*sidebar\.agents)", re.M)


def active_lines(text):
    return [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def has_setting(text):
    return any(ACTIVE.match(l) for l in active_lines(text))


def merged(config_text, snippet_text):
    sep = "" if config_text.endswith("\n") or not config_text else "\n"
    return config_text + sep + ("\n" if config_text else "") + snippet_text.rstrip("\n") + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(Path.home() / ".config/herdr/config.toml"))
    ap.add_argument("--snippet", default=str(REPO / "templates/herdr-sidebar.toml"))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    config, snippet = Path(args.config).expanduser(), Path(args.snippet)
    old = config.read_text() if config.exists() else ""
    new_part = snippet.read_text()

    if has_setting(old):
        print("The config already sets sidebar.agents. Not touching it.")
        print("Current lines:")
        print("\n".join("  " + l for l in active_lines(old) if "sidebar" in l or l.lstrip().startswith("rows")))
        print("Orchid suggests:")
        print("\n".join("  " + l for l in active_lines(new_part)))
        print("Merge by hand if you want the orchid layout.")
        return 3

    new = merged(old, new_part)
    sys.stdout.writelines(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), str(config), str(config) + " (new)"))

    if not args.apply:
        print("\nDry run. Add --apply to write.")
        return 0
    config.parent.mkdir(parents=True, exist_ok=True)
    if config.exists():
        backup = config.with_name(config.name + ".orchid-bak-" + time.strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(config, backup)
        print("backup: %s" % backup)
    config.write_text(new)
    print("written: %s. Reload the config from herdr's global menu or run: herdr server reload-config" % config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
