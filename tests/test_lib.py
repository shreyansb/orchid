"""Tests for the task reader, config reader and the install scripts. Standard library only.

Every script test runs with HOME and the skills folder pointed at a temporary directory, so
nothing outside it is touched.
"""
import atexit
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "lib"))
import orchid_config  # noqa: E402
import orchid_tasks  # noqa: E402


# A fake `herdr` first on PATH for every script a test runs, so no test can reach the real
# herdr server (HOME does not isolate its socket). Calls are logged to HERDR_STUB_LOG.
STUB_DIR = tempfile.mkdtemp(prefix="orchid-stub-")
STUB_LOG = os.path.join(STUB_DIR, "calls.log")
STUB = """import json, os, sys
args = sys.argv[1:]
with open(os.environ["HERDR_STUB_LOG"], "a") as f:
    f.write(" ".join(args) + "\\n")
named = {"result": {"agents": [
    {"pane_id": "w1:p1", "workspace_id": "w1", "name": "orchid", "agent": "claude",
     "agent_status": "idle", "cwd": "/tmp", "terminal_title_stripped": "", "completion_seq": 0},
    {"pane_id": "w1:p2", "workspace_id": "w1", "agent": "claude",
     "agent_status": "idle", "cwd": "/tmp", "terminal_title_stripped": "", "completion_seq": 0}]}}
if args[:1] == ["--version"]:
    print("herdr 0.9.5")
elif args[:2] == ["agent", "list"]:
    print(json.dumps(named))
elif args[:2] == ["workspace", "list"]:
    print(json.dumps({"result": {"workspaces": [{"workspace_id": "w1", "label": "home"}]}}))
elif args[:2] in (["machine", "list"], ["machine", "status"]):
    print("[]")
elif args[:2] == ["agent", "rename"]:
    print("{}")
else:
    sys.stderr.write("stub herdr: unsupported: " + " ".join(args) + "\\n")
    sys.exit(1)
"""
# The launcher is a /bin/sh script, because the path of sys.executable may contain a space,
# which a shebang line cannot hold.
with open(os.path.join(STUB_DIR, "herdr_stub.py"), "w") as _f:
    _f.write(STUB)
_stub_path = os.path.join(STUB_DIR, "herdr")
with open(_stub_path, "w") as _f:
    _f.write('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, os.path.join(STUB_DIR, "herdr_stub.py")))
os.chmod(_stub_path, 0o755)
atexit.register(shutil.rmtree, STUB_DIR, True)


def stub_calls():
    try:
        with open(STUB_LOG) as f:
            return f.read().splitlines()
    except OSError:
        return []


def reset_stub_log():
    try:
        os.remove(STUB_LOG)
    except OSError:
        pass


def sh(args, env=None, cwd=None):
    e = dict(os.environ)
    e["PATH"] = STUB_DIR + os.pathsep + "/usr/bin:/bin:/usr/sbin:/sbin"
    e["HERDR_STUB_LOG"] = STUB_LOG
    e["HERDR_SOCKET_PATH"] = "/nonexistent/herdr.sock"
    e.update(env or {})
    return subprocess.run(args, capture_output=True, text=True, env=e, cwd=cwd)


class ConfigTests(unittest.TestCase):
    def test_parse_skips_comments_and_blanks(self):
        got = orchid_config.parse("# c\n\nhome = ~/x\norchestrator=boss\n")
        self.assertEqual(got, {"home": "~/x", "orchestrator": "boss"})

    def test_load_defaults_when_missing(self):
        cfg = orchid_config.load("/nonexistent/orchid-config")
        self.assertEqual(cfg["orchestrator"], "orchid")
        self.assertEqual(cfg["machine_label"], "local")
        self.assertTrue(str(cfg["home"]).endswith("orchid-home"))

    def test_load_reads_values(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config"
            p.write_text("home=%s/h\norchestrator=boss\nmachine_label=box\n" % d)
            cfg = orchid_config.load(p)
        self.assertEqual(cfg["orchestrator"], "boss")
        self.assertEqual(cfg["machine_label"], "box")
        self.assertEqual(cfg["home"], Path(d) / "h")


class ConfigValidationTests(unittest.TestCase):
    def cfg(self, **kw):
        base = {"home": Path("/x"), "home_text": "/x", "orchestrator": "orchid", "machine_label": "laptop"}
        base.update(kw)
        return base

    def test_good_labels(self):
        for label in ("laptop", "my box", "Box-2", "local"):
            self.assertEqual(orchid_config.problems(self.cfg(machine_label=label)), [], label)

    def test_bad_labels(self):
        for label in ("", "   ", "<machine-label>", "a/b", "a>b", "<x"):
            self.assertTrue(orchid_config.problems(self.cfg(machine_label=label)), repr(label))

    def test_orchestrator_name_must_be_a_herdr_name(self):
        self.assertTrue(orchid_config.problems(self.cfg(orchestrator="Orchid")))
        self.assertTrue(orchid_config.problems(self.cfg(orchestrator="a b")))
        self.assertEqual(orchid_config.problems(self.cfg(orchestrator="boss_2")), [])

    def test_status_states(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(orchid_config.status(Path(d) / "none")[0], "missing")
            self.assertTrue(orchid_config.status(Path(d) / "none")[1].startswith("config not found"))
            p = Path(d) / "c"
            p.write_text("machine_label=<machine-label>\n")
            self.assertEqual(orchid_config.status(p)[0], "invalid")
            p.write_text("machine_label=\n")
            self.assertEqual(orchid_config.status(p)[0], "invalid")
            p.write_text("machine_label=laptop\n")
            self.assertEqual(orchid_config.status(p)[0], "ok")


class TaskParserTests(unittest.TestCase):
    def test_front_matter_and_inline_comments(self):
        text = "---\nid: T1\nagent:   # hint text\nstatus: running # note\n---\nbody"
        meta = orchid_tasks.parse_front_matter(text)
        self.assertEqual(meta["id"], "T1")
        self.assertEqual(meta["agent"], "")
        self.assertEqual(meta["status"], "running")

    def test_no_front_matter(self):
        self.assertEqual(orchid_tasks.parse_front_matter("just text"), {})
        self.assertEqual(orchid_tasks.parse_front_matter("---\nid: T1\n"), {})

    def test_owners_many_and_pair(self):
        meta = {"agents": "a/one, b/two ,bad,/x,c/", "machine": "m", "agent": "z"}
        self.assertEqual(orchid_tasks.owners(meta), [("a", "one"), ("b", "two"), ("m", "z")])

    def test_label_with_space_and_agent_with_slash(self):
        self.assertEqual(orchid_tasks.owners({"agents": "my box/a/b"}), [("my box", "a/b")])

    def test_open_tasks_filters_by_status(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "T001.md").write_text("---\nid: T001\ntitle: One\nstatus: running\nagents: m/a\n---\n")
            (d / "T002.md").write_text("---\nid: T002\ntitle: Two\nstatus: done\nagents: m/b\n---\n")
            (d / "T003.md").write_text("---\nid: T003\ntitle: Three\nstatus: new\nmachine: m\nagent: c\n---\n")
            (d / "notes.md").write_text("---\nid: X\nstatus: running\nagents: m/z\n---\n")
            got = orchid_tasks.open_tasks(d)
        self.assertEqual(got, {("m", "a"): ("T001", "One"), ("m", "c"): ("T003", "Three")})

    def test_unfilled_template_owns_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "T000.md").write_text((REPO / "templates/task.md").read_text())
            self.assertEqual(orchid_tasks.open_tasks(d), {})

    def test_missing_folder(self):
        self.assertEqual(orchid_tasks.open_tasks("/nonexistent/tasks"), {})


class MergeSidebarTests(unittest.TestCase):
    script = str(REPO / "skills/herdr-sidebar/merge_sidebar.py")
    snippet = str(REPO / "templates/herdr-sidebar.toml")

    def run_merge(self, d, *extra):
        return sh([sys.executable, self.script, "--config", str(Path(d) / "config.toml"),
                   "--snippet", self.snippet] + list(extra))

    def test_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config.toml"
            cfg.write_text("[ui]\n# sidebar_width = 26\n")
            r = self.run_merge(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Dry run", r.stdout)
            self.assertEqual(cfg.read_text(), "[ui]\n# sidebar_width = 26\n")

    def test_apply_appends_and_backs_up(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config.toml"
            cfg.write_text("[ui]\n# sidebar.agents is only mentioned in a comment\n")
            r = self.run_merge(d, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("[ui.sidebar.agents]", cfg.read_text())
            self.assertTrue(list(Path(d).glob("config.toml.orchid-bak-*")))

    def test_existing_setting_is_left_alone(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config.toml"
            original = '[ui.sidebar.agents]\nrows = [["agent"]]\n'
            cfg.write_text(original)
            r = self.run_merge(d, "--apply")
            self.assertEqual(r.returncode, 3)
            self.assertEqual(cfg.read_text(), original)
            self.assertFalse(list(Path(d).glob("*.orchid-bak-*")))

    def test_missing_config_is_created_only_on_apply(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_merge(d)
            self.assertEqual(r.returncode, 0)
            self.assertFalse((Path(d) / "config.toml").exists())
            self.run_merge(d, "--apply")
            self.assertTrue((Path(d) / "config.toml").exists())


class LinkSkillTests(unittest.TestCase):
    script = str(REPO / "scripts/link-skill.sh")

    def run_link(self, d, *args):
        return sh(["sh", self.script, "herdr-agents", "--to", "claude"] + list(args),
                  env={"SKILLS_DIR": str(Path(d) / "skills")})

    def test_dry_run_apply_refuse_uninstall(self):
        with tempfile.TemporaryDirectory() as d:
            link = Path(d) / "skills/herdr-agents"
            self.assertEqual(self.run_link(d).returncode, 0)
            self.assertFalse(link.exists())
            self.assertEqual(self.run_link(d, "--apply").returncode, 0)
            self.assertTrue(link.is_symlink())
            self.assertIn("already linked", self.run_link(d, "--apply").stdout)
            link.unlink()
            link.mkdir()
            r = self.run_link(d, "--apply")
            self.assertEqual(r.returncode, 1)
            self.assertIn("refusing", r.stderr)
            link.rmdir()
            self.run_link(d, "--apply")
            self.assertEqual(self.run_link(d, "--uninstall", "--apply").returncode, 0)
            self.assertFalse(link.exists())

    def test_unknown_skill(self):
        with tempfile.TemporaryDirectory() as d:
            r = sh(["sh", self.script, "no-such-skill", "--to", "claude"],
                   env={"SKILLS_DIR": str(Path(d) / "skills")})
            self.assertEqual(r.returncode, 1)


class SafeWriteTests(unittest.TestCase):
    script = str(REPO / "scripts/safe-write.sh")

    def test_new_changed_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            src, dest = Path(d) / "src", Path(d) / "sub/dest"
            src.write_text("one\n")
            self.assertEqual(sh(["sh", self.script, str(src), str(dest)]).returncode, 0)
            self.assertFalse(dest.exists())
            sh(["sh", self.script, str(src), str(dest), "--apply"])
            self.assertEqual(dest.read_text(), "one\n")
            self.assertIn("unchanged", sh(["sh", self.script, str(src), str(dest)]).stdout)
            src.write_text("two\n")
            sh(["sh", self.script, str(src), str(dest)])
            self.assertEqual(dest.read_text(), "one\n")  # dry run keeps it
            sh(["sh", self.script, str(src), str(dest), "--apply"])
            self.assertEqual(dest.read_text(), "two\n")
            baks = list(dest.parent.glob("dest.orchid-bak-*"))
            self.assertEqual(len(baks), 1)
            self.assertEqual(baks[0].read_text(), "one\n")


class LauncherTests(unittest.TestCase):
    script = str(REPO / "skills/herdr-profiles/make-launcher.sh")

    def test_dry_run_apply_and_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            env = {"HOME": d}
            target = Path(d) / ".local/bin/orchid-test-launcher"
            args = ["sh", self.script, "orchid-test-launcher", "claude", str(Path(d) / "cfg")]
            self.assertEqual(sh(args, env).returncode, 0)
            self.assertFalse(target.exists())
            self.assertEqual(sh(args + ["--apply"], env).returncode, 0)
            body = target.read_text()
            self.assertIn("CLAUDE_CONFIG_DIR=", body)
            self.assertIn('exec claude "$@"', body)
            self.assertTrue(os.access(str(target), os.X_OK))
            self.assertEqual(sh(args + ["--apply"], env).returncode, 1)

    def test_tilde_and_home_are_expanded_not_written_literally(self):
        with tempfile.TemporaryDirectory() as d:
            for given in ("~/.claude-work", "$HOME/.claude-work"):
                name = "t" + str(abs(hash(given)) % 100000)
                r = sh(["sh", self.script, name, "claude", given, "--apply"], {"HOME": d}, cwd=d)
                self.assertEqual(r.returncode, 0, r.stderr)
                body = (Path(d) / ".local/bin" / name).read_text()
                self.assertIn('CLAUDE_CONFIG_DIR="%s/.claude-work"' % d, body)
                self.assertNotIn("~", body)
            self.assertFalse((Path(d) / "~").exists(), "must not create a folder named ~")
            self.assertTrue((Path(d) / ".claude-work").is_dir())

    def test_relative_and_unsafe_dirs_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("relative/dir", "/tmp/a$b", '/tmp/a"b'):
                r = sh(["sh", self.script, "t-bad", "claude", bad], {"HOME": d})
                self.assertEqual(r.returncode, 2, bad)

    def test_codex_uses_codex_home_and_bad_name(self):
        with tempfile.TemporaryDirectory() as d:
            r = sh(["sh", self.script, "t-codex", "codex", str(Path(d) / "x")], {"HOME": d})
            self.assertIn("CODEX_HOME=", r.stdout)
            r = sh(["sh", self.script, "bad name", "claude", d], {"HOME": d})
            self.assertEqual(r.returncode, 2)


class WriteConfigTests(unittest.TestCase):
    script = str(REPO / "scripts/write-config.sh")

    def run_wc(self, d, label, *extra, orch="orchid"):
        dest = str(Path(d) / "cfg/config")
        return sh(["sh", self.script, "--home", "~/orchid-home", "--orchestrator", orch,
                   "--label", label, "--config", dest] + list(extra), {"HOME": d}), Path(dest)

    def test_rejects_placeholder_empty_slash_and_bad_orchestrator(self):
        with tempfile.TemporaryDirectory() as d:
            for label in ("<machine-label>", "a/b", "x>"):
                r, dest = self.run_wc(d, label, "--apply")
                self.assertEqual(r.returncode, 2, label)
                self.assertFalse(dest.exists())
            r, dest = self.run_wc(d, "", "--apply")
            self.assertEqual(r.returncode, 2)
            r, dest = self.run_wc(d, "laptop", "--apply", orch="Bad Name")
            self.assertEqual(r.returncode, 2)
            self.assertFalse(dest.exists())

    def test_dry_run_then_apply_then_backup_on_change(self):
        with tempfile.TemporaryDirectory() as d:
            r, dest = self.run_wc(d, "laptop")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(dest.exists())
            self.assertIn("Dry run", r.stdout)
            self.run_wc(d, "laptop", "--apply")
            self.assertIn("machine_label=laptop", dest.read_text())
            self.assertEqual(orchid_config.status(dest)[0], "ok")
            self.run_wc(d, "desktop", "--apply")
            self.assertIn("machine_label=desktop", dest.read_text())
            self.assertEqual(len(list(dest.parent.glob("config.orchid-bak-*"))), 1)


class InitHomeTests(unittest.TestCase):
    script = str(REPO / "scripts/init-home.sh")

    def test_dry_run_creates_nothing_apply_creates_all_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "h"
            r = sh(["sh", self.script, str(home)], {"HOME": d})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(home.exists(), "dry run must not create the folder")
            self.assertIn("would: mkdir -p %s/tasks" % home, r.stdout)
            self.assertIn("Dry run", r.stdout)
            r = sh(["sh", self.script, str(home), "--apply"], {"HOME": d})
            self.assertEqual(r.returncode, 0, r.stderr)
            for name in ("AGENTS.md", "CLAUDE.md", "board.md", "journal.md", "spaces.md", "task-template.md"):
                self.assertTrue((home / name).is_file(), name)
            self.assertTrue((home / "tasks").is_dir() and (home / "done").is_dir())
            self.assertIn("@AGENTS.md", (home / "CLAUDE.md").read_text())
            again = sh(["sh", self.script, str(home), "--apply"], {"HOME": d})
            self.assertIn("unchanged", again.stdout)
            self.assertFalse(list(home.glob("*.orchid-bak-*")))

    def test_existing_file_is_backed_up_not_lost(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "h"
            home.mkdir()
            (home / "AGENTS.md").write_text("my own rules\n")
            sh(["sh", self.script, str(home), "--apply"], {"HOME": d})
            baks = list(home.glob("AGENTS.md.orchid-bak-*"))
            self.assertEqual(len(baks), 1)
            self.assertEqual(baks[0].read_text(), "my own rules\n")

    def test_refuses_a_home_inside_the_repo_and_relative_paths(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(sh(["sh", self.script, str(REPO / "mine")], {"HOME": d}).returncode, 1)
            self.assertEqual(sh(["sh", self.script, "relative/h"], {"HOME": d}).returncode, 2)

    def test_tilde_home_expands(self):
        with tempfile.TemporaryDirectory() as d:
            sh(["sh", self.script, "~/orchid-home", "--apply"], {"HOME": d}, cwd=d)
            self.assertTrue((Path(d) / "orchid-home/AGENTS.md").is_file())
            self.assertFalse((Path(d) / "~").exists())


@unittest.skipUnless(platform.system() == "Darwin", "watcher installer is macOS only")
class WatcherInstallDryRun(unittest.TestCase):
    script = str(REPO / "skills/orchid-watcher/install.sh")

    def test_dry_run_renders_lints_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "cfg/config"
            cfg.parent.mkdir()
            cfg.write_text("home=%s/h\n" % d)
            r = sh(["sh", self.script], {"HOME": d, "ORCHID_CONFIG": str(cfg)})
            if "herdr is not on PATH" in r.stderr:
                self.skipTest("herdr not installed")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("passes plutil -lint", r.stdout)
            self.assertIn("/opt/homebrew/bin", r.stdout)
            self.assertIn("Dry run", r.stdout)
            self.assertFalse((Path(d) / "Library/LaunchAgents/dev.orchid.watcher.plist").exists())

    def test_uninstall_dry_run_without_plist(self):
        with tempfile.TemporaryDirectory() as d:
            r = sh(["sh", self.script, "--uninstall"], {"HOME": d})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Nothing to remove", r.stdout)


def write_config(d, label="testbox", orchestrator="orchid"):
    cfg = Path(d) / "cfg" / "config"
    cfg.parent.mkdir(exist_ok=True)
    cfg.write_text("home=%s/home\norchestrator=%s\nmachine_label=%s\n" % (d, orchestrator, label))
    return cfg


class HerdrAgentsReadOnlyTests(unittest.TestCase):
    script = str(REPO / "skills/herdr-agents/herdr_agents.py")

    def run_agents(self, d, *args):
        cfg = write_config(d)
        reset_stub_log()
        r = sh([sys.executable, "-I", self.script, "--local"] + list(args),
               {"ORCHID_CONFIG": str(cfg), "HOME": d})
        return r, cfg

    def test_default_run_renames_nothing_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            r, cfg = self.run_agents(d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse([c for c in stub_calls() if "rename" in c], stub_calls())
            self.assertFalse((cfg.parent / "names.json").exists())
            self.assertIn("home-p2*", r.stdout)
            self.assertIn("Nothing was renamed", r.stdout)

    def test_apply_renames_and_saves(self):
        with tempfile.TemporaryDirectory() as d:
            r, cfg = self.run_agents(d, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual([c for c in stub_calls() if "rename" in c], ["agent rename w1:p2 home-p2"])
            self.assertIn("home-p2", (cfg.parent / "names.json").read_text())

    def test_json_says_whether_applied(self):
        with tempfile.TemporaryDirectory() as d:
            r, _ = self.run_agents(d, "--json")
            self.assertIn('"applied": false', r.stdout)

    def test_invalid_config_stops_before_touching_herdr(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = write_config(d, label="<machine-label>")
            reset_stub_log()
            r = sh([sys.executable, "-I", self.script, "--local", "--apply"], {"ORCHID_CONFIG": str(cfg), "HOME": d})
            self.assertEqual(r.returncode, 2)
            self.assertIn("config invalid", r.stderr)
            self.assertEqual(stub_calls(), [])

    def test_watcher_names_with_apply(self):
        src = (REPO / "skills/orchid-watcher/orchid_watcher.py").read_text()
        self.assertIn('"--quiet", "--apply"', src)

    def test_watcher_never_prompts_or_reads_the_keyboard(self):
        src = (REPO / "skills/orchid-watcher/orchid_watcher.py").read_text()
        for banned in ('"prompt"', "ioreg", "HIDIdleTime", "IDLE_SECONDS", "osascript", "PushNotification"):
            self.assertNotIn(banned, src)

    def test_tests_use_the_stub_not_the_real_herdr(self):
        env_path = STUB_DIR + os.pathsep + "/usr/bin:/bin"
        self.assertEqual(shutil.which("herdr", path=env_path), os.path.join(STUB_DIR, "herdr"))


class ConfigMissingAgreementTests(unittest.TestCase):
    """The watcher check and the doctor must describe a missing or broken config alike."""
    watcher = str(REPO / "skills/orchid-watcher/orchid_watcher.py")
    doctor = str(REPO / "skills/orchid-doctor/doctor.py")

    def run_both(self, cfg_path, d):
        env = {"ORCHID_CONFIG": str(cfg_path), "HOME": d}
        w = sh([sys.executable, "-I", self.watcher, "--check"], env)
        k = sh([sys.executable, "-I", self.doctor], env)
        return w, k

    def test_missing_config(self):
        with tempfile.TemporaryDirectory() as d:
            w, k = self.run_both(Path(d) / "nope", d)
            self.assertEqual(w.returncode, 1)
            self.assertIn("config not found", w.stdout)
            self.assertIn("config not found", k.stdout)
            self.assertEqual(k.returncode, 0)  # a missing config is a WARN for the doctor
            self.assertNotIn("machine_label: local", w.stdout)

    def test_invalid_label_fails_both(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = write_config(d, label="<machine-label>")
            w, k = self.run_both(cfg, d)
            self.assertEqual(w.returncode, 1)
            self.assertIn("config invalid", w.stdout)
            self.assertEqual(k.returncode, 1)
            self.assertIn("FAIL", k.stdout)
            self.assertIn("config invalid", k.stdout)

    def test_good_config_passes_the_check(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = write_config(d)
            (Path(d) / "home").mkdir()
            w, k = self.run_both(cfg, d)
            self.assertEqual(w.returncode, 0, w.stdout + w.stderr)
            self.assertIn("machine_label: testbox", w.stdout)
            self.assertNotIn("FAIL", k.stdout)



class WatcherWakeTests(unittest.TestCase):
    """A wake writes one line to wakes.log and never calls `herdr agent prompt`."""

    def load_watcher(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("orchid_watcher_under_test",
                                                      REPO / "skills/orchid-watcher/orchid_watcher.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def poll(self, d, statuses):
        """Run poll_once once per status in `statuses` with a fake herdr. Returns (calls, wakes)."""
        home = Path(d) / "home"
        (home / "tasks").mkdir(parents=True)
        (home / "tasks" / "T001.md").write_text(
            "---\nid: T001\ntitle: Test task\nstatus: running\nagents: laptop/worker\n---\n")
        cfg_file = write_config(d, label="laptop")
        old = os.environ.get("ORCHID_CONFIG")
        os.environ["ORCHID_CONFIG"] = str(cfg_file)
        try:
            w = self.load_watcher()
            calls = []
            current = {}

            def fake_json(*args, machine=None):
                calls.append(" ".join(args))
                return {"result": {"agents": [{"name": "worker", "agent_status": current["s"], "completion_seq": 0}]}}

            w.herdr_json = fake_json
            w.targets = lambda label: [(label, None)]
            cfg = orchid_config.load(cfg_file)
            seen, pending, down = {}, {}, set()
            extra = {"unknown": {}, "screen": {}, "flagged": set()}
            for s in statuses:
                current["s"] = s
                w.poll_once(cfg, seen, pending, down, extra)
            wakes = orchid_config.wakes_path()
            return calls, (wakes.read_text().splitlines() if wakes.exists() else []), wakes
        finally:
            if old is None:
                os.environ.pop("ORCHID_CONFIG", None)
            else:
                os.environ["ORCHID_CONFIG"] = old

    def test_wake_writes_one_line_and_does_not_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            calls, lines, wakes = self.poll(d, ["working", "idle", "idle"])
            self.assertEqual(wakes.parent, Path(d) / "cfg")  # next to the config
            self.assertEqual(len(lines), 1, lines)
            self.assertIn("agent worker on laptop is now idle (task T001: Test task)", lines[0])
            self.assertEqual([c for c in calls if "prompt" in c], [])
            self.assertEqual(set(c.split()[0] for c in calls), {"agent"})

    def test_no_wake_line_for_an_agent_that_never_worked(self):
        with tempfile.TemporaryDirectory() as d:
            _, lines, _ = self.poll(d, ["idle", "idle"])
            self.assertEqual(lines, [])

    def test_wakes_path_is_next_to_the_config(self):
        old = os.environ.get("ORCHID_CONFIG")
        os.environ["ORCHID_CONFIG"] = "/x/y/config"
        try:
            self.assertEqual(orchid_config.wakes_path(), Path("/x/y/wakes.log"))
        finally:
            if old is None:
                os.environ.pop("ORCHID_CONFIG", None)
            else:
                os.environ["ORCHID_CONFIG"] = old

if __name__ == "__main__":
    unittest.main()
