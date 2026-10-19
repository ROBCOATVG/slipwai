"""A slice's berth has what its session needs, and git does not carry.

hr-test-2's first slices run abreast each exited 1 three times in six seconds: the session was started in
the slice's worktree with `--mcp-config .mcp.json`, and the branch had been cut before the file was
committed. The same worktree had no projected `.claude/commands/`, so `/drive` would not have been a
command, and a `.slipwai/logs` directory a session had already written into, which the captain left —
so every line after it would have missed the gate.
"""
from __future__ import annotations

import importlib.util
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
from test_harness import loaded

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "assets/toolkit/scripts/agents"


def moorings() -> Any:
    spec = importlib.util.spec_from_file_location("moorings_under_test", AGENTS / "moorings.py")
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(where: Path, *argv: str) -> None:
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv], cwd=where, check=True,
                   capture_output=True)


class BerthTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        self.root = self.home / "project with space"
        (self.root / "scripts/agents").mkdir(parents=True)
        # A projection that leaves the mark a real one leaves: the slash commands under `.claude/`.
        (self.root / "scripts/agents/project.py").write_text(
            "from pathlib import Path\n"
            "Path('.claude/commands').mkdir(parents=True, exist_ok=True)\n"
            "Path('.claude/commands/drive.md').write_text('# drive\\n')\n", encoding="utf-8")
        (self.root / ".gitignore").write_text(".env\n.claude/commands/\n.slipwai/logs/\n", encoding="utf-8")
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "scaffold")
        (self.root / ".env").write_text("SECRET=1\n", encoding="utf-8")
        self.module = moorings()

    def test_a_berth_gets_the_projected_commands_and_the_project_s_env(self) -> None:
        berth, said = self.module.berth(self.root, "L01", "slice/L01", "main")
        self.assertIsNotNone(berth)
        self.assertEqual(said, "")
        self.assertTrue((berth / ".claude/commands/drive.md").is_file(), "/drive is a command in the berth")
        self.assertEqual((berth / ".env").read_text(encoding="utf-8"), "SECRET=1\n")
        status = subprocess.run(["git", "status", "--porcelain"], cwd=berth, capture_output=True, text=True)
        self.assertEqual(status.stdout.strip(), "", "nothing the berth was given shows up as a change")

    def test_lines_a_session_wrote_before_the_link_are_kept_aside_and_the_log_is_linked(self) -> None:
        berth = self.root.parent / f"{self.root.name}-L02"
        git(self.root, "worktree", "add", "-q", "-b", "slice/L02", str(berth), "main")
        (berth / ".slipwai/logs/feature").mkdir(parents=True)
        (berth / ".slipwai/logs/feature/fairway.jsonl").write_text('{"kind": "demo"}\n', encoding="utf-8")
        found, said = self.module.berth(self.root, "L02", "slice/L02", "main")
        self.assertEqual(found.resolve(), berth.resolve())
        self.assertTrue((berth / ".slipwai/logs").is_symlink(), "every later line lands in the shared log")
        aside = [path for path in (berth / ".slipwai").iterdir() if path.name.startswith("logs.unread-")]
        self.assertEqual(len(aside), 1)
        self.assertEqual((aside[0] / "feature/fairway.jsonl").read_text(encoding="utf-8"), '{"kind": "demo"}\n')
        self.assertIn("kept at", said)

    def test_the_project_s_own_checkout_is_never_furnished(self) -> None:
        self.assertEqual(self.module.furnished(self.root, self.root), "")
        self.assertFalse((self.root / ".claude").exists())


class McpFlagTest(unittest.TestCase):
    def test_the_mcp_file_is_named_by_the_project_s_absolute_path_quoted(self) -> None:
        home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home, True)
        root = home / "hr-test 11.25.24"
        root.mkdir()
        (root / ".mcp.json").write_text("{}", encoding="utf-8")
        harness = loaded(root)
        line, _why = harness.template(harness.registry()["claude"])
        argv = shlex.split(line.replace("{prompt}", "p"))
        self.assertIn("--mcp-config", argv)
        self.assertEqual(argv[argv.index("--mcp-config") + 1], str(root / ".mcp.json"))

    def test_no_flag_where_the_project_has_no_mcp_file(self) -> None:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        harness = loaded(root)
        line, _why = harness.template(harness.registry()["claude"])
        self.assertNotIn("--mcp-config", line)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
