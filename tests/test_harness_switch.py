"""A project set up under one coding agent and opened in another sets itself up there.

A team that moves from one harness to another found the project followed none of its rules: the commands,
skills and delegate types are generated per harness and git ignores them, and the harness the project was
moved to read no file it recognised. So the context file is committed for every harness that reads one by
include, `make agents` adds the harness the session runs in, removes projections whose source has gone, and
says when the slipwai installed here is newer than the one that wrote the project.

Each case is a project of a few files and the real projector run against it, with `specify` and `slipwai`
stood in by scripts on PATH that record what they were asked.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project.agent_settings import IMPORT_REGION, context_imports
from slipwai.project.gitignore import projection_artifacts

AGENTS = TOOLKIT_ROOT / "scripts/agents"
SESSION_VARIABLES = ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")
COMMAND = "---\ndescription: Drive one slice\n---\n\n# Drive\n"
AGENT_TYPE = ("---\nname: sail-review-mate\ndescription: Review one slice\nstage: none\nwrites: none\n"
              "commands: read-only\n---\n\nRead the diff.\n")
# Records the call, then does what Spec Kit's `integration install` does to the record: adds the key beside the
# others and keeps the default. `REFUSE` set makes it refuse the way Spec Kit refuses an unsafe second install.
SPECIFY = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ["CALLS"]).open("a", encoding="utf-8").write(" ".join(sys.argv[1:]) + "\\n")
if os.environ.get("REFUSE"):
    print("Installing multiple integrations is only automatic when all involved integrations are "
          "declared multi-install safe.")
    sys.exit(1)
record = Path(".specify/integration.json")
state = json.loads(record.read_text(encoding="utf-8"))
state["installed_integrations"] = [*state["installed_integrations"], sys.argv[3]]
record.write_text(json.dumps(state), encoding="utf-8")
"""
SLIPWAI = "#!/bin/sh\necho \"slipwai $INSTALLED\"\n"


def projector() -> Any:
    """The projector's module, for its constants and pure helpers; loaded from its path like every toolkit script."""
    spec = importlib.util.spec_from_file_location("projector_under_test", AGENTS / "project.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


class Switch(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(AGENTS, self.root / "scripts/agents", ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "project.json").write_text(json.dumps({"generator": {"updatedWith": "2.0.0.dev2"}}),
                                                encoding="utf-8")
        (self.root / "AGENTS.md").write_text("# Repository guidance\n", encoding="utf-8")
        for path, text in {"commands/sail.md": COMMAND, "agents/sail-review-mate.md": AGENT_TYPE,
                           "skills/testing/SKILL.md": "---\nname: testing\n---\n\nTest it.\n"}.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(text, encoding="utf-8")
        (self.root / ".specify").mkdir()
        (self.root / ".specify/integration.json").write_text(json.dumps(
            {"installed_integrations": ["cursor-agent"], "default_integration": "cursor-agent"}), encoding="utf-8")
        self.bin = self.root / ".bin"
        self.bin.mkdir()
        for name, text in {"specify": SPECIFY, "slipwai": SLIPWAI}.items():
            (self.bin / name).write_text(text, encoding="utf-8")
            (self.bin / name).chmod(0o755)
        self.calls = self.root / ".calls"

    def run_projector(self, *flags: str, session: str | None = "claude",
                      **extra: str) -> subprocess.CompletedProcess[str]:
        environment = {key: value for key, value in os.environ.items() if key not in SESSION_VARIABLES}
        environment.update({"PATH": os.pathsep.join((str(self.bin), "/usr/bin", "/bin")),
                            "CALLS": str(self.calls), "INSTALLED": "2.0.0.dev2", **extra})
        if session == "claude":
            environment["CLAUDE_CODE_SESSION_ID"] = "one"
        return subprocess.run([sys.executable, "scripts/agents/project.py", *flags], cwd=self.root,
                              capture_output=True, text=True, env=environment)

    def installed(self) -> list[str]:
        state = json.loads((self.root / ".specify/integration.json").read_text(encoding="utf-8"))
        return list(state["installed_integrations"])

    def test_the_running_harness_is_added_through_spec_kit_and_projected(self) -> None:
        done = self.run_projector()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.calls.read_text(encoding="utf-8"), "integration install claude\n")
        self.assertEqual(self.installed(), ["cursor-agent", "claude"])
        self.assertTrue((self.root / ".claude/commands/sail.md").is_file())
        self.assertTrue((self.root / ".claude/agents/sail-review-mate.md").is_file())
        self.assertTrue((self.root / ".cursor/skills/testing/SKILL.md").is_file(), "the installed one is kept")
        self.assertIn("Spec Kit added it", done.stdout)

    def test_a_refusal_from_spec_kit_is_said_and_the_project_is_projected_anyway(self) -> None:
        done = self.run_projector(REFUSE="1")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.installed(), ["cursor-agent"])
        self.assertTrue((self.root / ".claude/commands/sail.md").is_file())
        self.assertIn("a person's choice", done.stdout)
        self.assertIn("specify integration switch claude", done.stdout)

    def test_with_no_session_variable_it_projects_what_is_installed_and_says_it_could_not_tell(self) -> None:
        done = self.run_projector(session=None)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertFalse(self.calls.exists(), "nothing was guessed and nothing was added")
        self.assertFalse((self.root / ".claude/commands").exists())
        self.assertTrue((self.root / ".cursor/skills/testing/SKILL.md").is_file())
        self.assertIn("Could not tell which harness", done.stdout)

    def test_every_import_harness_gets_its_include_whatever_is_installed(self) -> None:
        done = self.run_projector(session=None)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("@AGENTS.md", (self.root / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_a_projection_whose_source_is_gone_is_removed_and_nothing_unstamped_is(self) -> None:
        self.assertEqual(self.run_projector().returncode, 0)
        mine = self.root / ".claude/commands/mine.md"
        mine.write_text("# a person's own command\n", encoding="utf-8")
        speckit = self.root / ".claude/skills/speckit-plan/SKILL.md"
        speckit.parent.mkdir(parents=True)
        speckit.write_text("---\nname: speckit-plan\n---\n", encoding="utf-8")
        (self.root / "commands/sail.md").unlink()
        (self.root / "skills/testing/SKILL.md").unlink()
        check = self.run_projector("--check")
        self.assertNotEqual(check.returncode, 0)
        self.assertIn(".claude/commands/sail.md: projected from a canonical file that no longer exists", check.stderr)
        done = self.run_projector()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertFalse((self.root / ".claude/commands/sail.md").exists())
        self.assertFalse((self.root / ".cursor/skills/testing").exists(), "the emptied skill directory goes too")
        self.assertTrue(mine.is_file())
        self.assertTrue(speckit.is_file())

    def test_a_newer_slipwai_is_said_and_migrate_is_named(self) -> None:
        newer = self.run_projector(INSTALLED="2.0.0")
        self.assertIn("slipwai 2.0.0 is installed", newer.stdout)
        self.assertIn("slipwai migrate", newer.stdout)
        same = self.run_projector()
        self.assertNotIn("slipwai migrate", same.stdout)

    def test_running_sets_up_only_where_the_harness_is_missing(self) -> None:
        first = self.run_projector("--running")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertTrue((self.root / ".claude/commands/sail.md").is_file())
        again = self.run_projector("--running")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(again.stdout, "")
        self.assertEqual(self.calls.read_text(encoding="utf-8"), "integration install claude\n")

    def test_running_with_no_session_variable_does_nothing(self) -> None:
        done = self.run_projector("--running", session=None)
        self.assertEqual((done.returncode, done.stdout), (0, ""))


class Pieces(unittest.TestCase):
    def test_the_keel_and_the_projector_spell_the_include_alike(self) -> None:
        self.assertEqual(IMPORT_REGION, projector().IMPORT_REGION + "\n")

    def test_a_generated_project_commits_the_include_and_ignores_none_of_it(self) -> None:
        files = context_imports()
        self.assertEqual(files, {"CLAUDE.md": IMPORT_REGION})
        ignored = projection_artifacts().splitlines()
        self.assertFalse([line for line in ignored if "CLAUDE.md" in line])

    def test_a_development_build_orders_below_its_release(self) -> None:
        version = projector().version_of
        self.assertLess(version("2.0.0.dev2"), version("2.0.0"))
        self.assertLess(version("2.0.0.dev1"), version("2.0.0.dev2"))
        self.assertLess(version("2.0.0"), version("2.0.1"))
        self.assertIsNone(version("unknown"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
