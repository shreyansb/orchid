"""Find the agents that own open tasks. Standard library only.

A task file starts with front matter between two `---` lines:

    ---
    id: T001
    title: Short title
    status: running
    agents: <machine-label>/<agent-name>, <machine-label>/<other-agent>
    ---

The watcher writes a wake line for the orchestrator when one of these agents settles.
"""
import re
from pathlib import Path

OPEN_STATUSES = {"new", "running"}
_FIELD = re.compile(r"^(\w+):[ \t]*(.*?)[ \t]*$", re.M)


def parse_front_matter(text):
    """Return the front matter fields as a dict. Empty dict if there is none.

    A trailing ` # comment` on a field line is dropped, so a copied template does not
    turn its hint text into a value.
    """
    parts = text.split("---", 2)
    if not text.lstrip().startswith("---") or len(parts) < 3:
        return {}
    meta = {}
    for key, value in _FIELD.findall(parts[1]):
        meta[key] = re.sub(r"(^|\s+)#.*$", "", value).strip()
    return meta


def owners(meta):
    """List of (machine label, agent name) pairs a task names.

    `agents: label/name, label/name` lists many agents. A `machine:` plus `agent:` pair
    names one. Machine labels must not contain "/".
    """
    pairs = []
    for item in meta.get("agents", "").split(","):
        item = item.strip()
        if "/" in item:
            machine, agent = item.split("/", 1)
            if machine.strip() and agent.strip():
                pairs.append((machine.strip(), agent.strip()))
    if meta.get("machine") and meta.get("agent"):
        pairs.append((meta["machine"], meta["agent"]))
    return pairs


def open_tasks(tasks_dir):
    """{(machine, agent): (task id, title)} for tasks whose status is new or running."""
    found = {}
    for f in sorted(Path(tasks_dir).glob("T*.md")):
        try:
            meta = parse_front_matter(f.read_text())
        except OSError:
            continue
        if meta.get("status") not in OPEN_STATUSES:
            continue
        for pair in owners(meta):
            found[pair] = (meta.get("id", f.stem), meta.get("title", ""))
    return found
