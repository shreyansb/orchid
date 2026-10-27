#!/usr/bin/env python3
"""Static checks on the repo. Standard library only. Changes nothing.

1. Every skills/*/SKILL.md has valid front matter: name equals the folder, description set.
2. Every relative Markdown link points at a file that exists.
3. Every Python file compiles.
4. The launchd template renders and has no placeholder left over.
5. Task examples and templates parse with the task reader.
Prints one line per check and exits 1 on any failure.
"""
import py_compile
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "lib"))
import orchid_tasks  # noqa: E402

failures = []


def fail(msg):
    failures.append(msg)
    print("FAIL  " + msg)


def ok(msg):
    print("ok    " + msg)


def skill_front_matter():
    for skill in sorted((REPO / "skills").iterdir()):
        md = skill / "SKILL.md"
        if not md.exists():
            fail("%s has no SKILL.md" % skill.name)
            continue
        text = md.read_text()
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        if not m:
            fail("%s: front matter missing or not closed" % skill.name)
            continue
        fields = dict(re.findall(r"^(\w+):[ \t]*(.*)$", m.group(1), re.M))
        if fields.get("name") != skill.name:
            fail("%s: name %r does not match the folder" % (skill.name, fields.get("name")))
        elif not fields.get("description") or len(fields["description"]) > 1024:
            fail("%s: description missing or over 1024 characters" % skill.name)
        else:
            for heading in ("## What it does", "## Verify", "## Undo"):
                if heading not in text:
                    fail("%s: missing section %r" % (skill.name, heading))
                    break
            else:
                ok("skill %s: front matter and sections" % skill.name)


def links():
    link = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
    checked = 0
    for md in sorted(REPO.rglob("*.md")):
        if ".git" in md.parts:
            continue
        for target in link.findall(md.read_text()):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            path = (md.parent / target.split("#")[0]).resolve()
            checked += 1
            if not path.exists():
                fail("%s: broken link %s" % (md.relative_to(REPO), target))
    ok("%d relative markdown links checked" % checked)


def compile_python():
    for py in sorted(REPO.rglob("*.py")):
        if ".git" in py.parts:
            continue
        try:
            with tempfile.TemporaryDirectory() as d:
                py_compile.compile(str(py), cfile=str(Path(d) / "x.pyc"), doraise=True)
        except py_compile.PyCompileError as e:
            fail("compile %s: %s" % (py.relative_to(REPO), e))
    ok("python files compile")


def plist_placeholders():
    text = (REPO / "launchd/dev.orchid.watcher.plist.template").read_text()
    found = set(re.findall(r"__[A-Z]+__", text))
    expected = {"__PYTHON__", "__SCRIPT__", "__PATH__", "__CONFIG__", "__LOG__"}
    if found != expected:
        fail("plist placeholders %s != %s" % (sorted(found), sorted(expected)))
    else:
        ok("plist template placeholders")


def task_files():
    for path in [REPO / "templates/task.md", REPO / "examples/two-machines-two-profiles/tasks/T001.md"]:
        meta = orchid_tasks.parse_front_matter(path.read_text())
        if "id" not in meta or "status" not in meta:
            fail("%s: front matter not readable" % path.relative_to(REPO))
    example = orchid_tasks.open_tasks(REPO / "examples/two-machines-two-profiles/tasks")
    if set(example) != {("workstation", "workstation-api-review"), ("laptop", "notes-research")}:
        fail("example task owners parsed wrong: %s" % example)
    else:
        ok("task template and example parse")


if __name__ == "__main__":
    skill_front_matter()
    links()
    compile_python()
    plist_placeholders()
    task_files()
    print("%d failure(s)" % len(failures))
    sys.exit(1 if failures else 0)
