"""Read the orchid config file. Standard library only; works on Python 3.8 and later.

The config is a plain `key=value` file (no TOML, because the system Python on macOS
predates `tomllib`). Default path: ~/.config/orchid/config. Override with ORCHID_CONFIG.

Keys:
  home           folder that holds state: tasks, board, journal, profiles, spaces
  orchestrator   herdr agent name of the orchestrator (the watcher wakes this agent)
  machine_label  label of THIS machine, the same label other machines use for it
"""
import os
from pathlib import Path

DEFAULTS = {"home": "~/orchid-home", "orchestrator": "orchid", "machine_label": "local"}


def config_path():
    env = os.environ.get("ORCHID_CONFIG")
    return Path(env).expanduser() if env else Path.home() / ".config" / "orchid" / "config"


def parse(text):
    """Turn config text into a dict. Blank lines and lines starting with # are skipped."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load(path=None):
    """Return the config with defaults filled in. `home` is a Path."""
    path = Path(path) if path else config_path()
    cfg = dict(DEFAULTS)
    try:
        cfg.update({k: v for k, v in parse(path.read_text()).items() if v})
    except OSError:
        pass
    cfg["home"] = Path(cfg["home"]).expanduser()
    return cfg


def state_dir():
    """Machine-local state (saved agent names, watcher log). Next to the config file."""
    return config_path().parent
