"""Read the orchid config file. Standard library only; works on Python 3.8 and later.

The config is a plain `key=value` file (no TOML, because the system Python on macOS
predates `tomllib`). Default path: ~/.config/orchid/config. Override with ORCHID_CONFIG.

Keys:
  home           folder that holds state: tasks, board, journal, profiles, spaces
  orchestrator   herdr agent name of the orchestrator (the watcher wakes this agent)
  machine_label  label of THIS machine, the same label other machines use for it
"""
import os
import re
from pathlib import Path

DEFAULTS = {"home": "~/orchid-home", "orchestrator": "orchid", "machine_label": "local"}
AGENT_NAME = re.compile(r"[a-z][a-z0-9_-]{0,31}")  # herdr's rule for agent names
LABEL_FORBIDDEN = "<>/"


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
        cfg.update(parse(path.read_text()))  # an empty value stays empty, so problems() can flag it
    except OSError:
        pass
    cfg["home_text"] = cfg["home"]
    cfg["home"] = Path(cfg["home"]).expanduser()
    return cfg


def state_dir():
    """Machine-local state (saved agent names, watcher log). Next to the config file."""
    return config_path().parent


def problems(cfg):
    """List what is wrong with a loaded config. Empty list means it is usable.

    A label left as the template placeholder (`<machine-label>`), an empty label, or one with
    "/" breaks task matching without any error, so it is rejected here.
    """
    out = []
    if not cfg.get("home_text", str(cfg.get("home", ""))).strip():
        out.append("home is empty")
    label = cfg.get("machine_label", "")
    if not label.strip():
        out.append("machine_label is empty")
    elif any(c in label for c in LABEL_FORBIDDEN):
        out.append("machine_label %r must not contain any of: %s" % (label, " ".join(LABEL_FORBIDDEN)))
    if not AGENT_NAME.fullmatch(cfg.get("orchestrator", "")):
        out.append("orchestrator %r is not a valid herdr agent name (lowercase letters, digits, - and _; "
                   "start with a letter; 32 characters at most)" % cfg.get("orchestrator", ""))
    return out


def status(path=None):
    """(state, message, cfg). State is "ok", "missing" or "invalid".

    The one place that decides what a missing or broken config means, so every tool says the
    same thing. The message for "missing" always starts with "config not found".
    """
    path = Path(path) if path else config_path()
    cfg = load(path)
    if not path.exists():
        return "missing", "config not found: %s" % path, cfg
    bad = problems(cfg)
    if bad:
        return "invalid", "config invalid: %s (%s)" % ("; ".join(bad), path), cfg
    return "ok", "config: %s" % path, cfg
