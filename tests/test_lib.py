"""Tests for the task reader, config reader and the install scripts. Standard library only.

Every script test runs with HOME and the skills folder pointed at a temporary directory, so
nothing outside it is touched.
"""
import os
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "lib"))
import orchid_config  # noqa: E402
import orchid_tasks  # noqa: E402


def sh(args, env=None, cwd=None):
    e = dict(os.environ)
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

    def test_codex_uses_codex_home_and_bad_name(self):
        with tempfile.TemporaryDirectory() as d:
            r = sh(["sh", self.script, "t-codex", "codex", str(Path(d) / "x")], {"HOME": d})
            self.assertIn("CODEX_HOME=", r.stdout)
            r = sh(["sh", self.script, "bad name", "claude", d], {"HOME": d})
            self.assertEqual(r.returncode, 2)


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


if __name__ == "__main__":
    unittest.main()
