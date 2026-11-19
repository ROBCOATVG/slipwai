"""`make agents` rewrites every elected extension's block in `AGENTS.md`, hook or no hook.

`check-extensions` said of a drifted block "run `make agents` or `slipwai migrate`", and for an extension with
no `project` hook neither rewrote it: the projection was the hook's alone, so only re-running the extension's
whole `init` did (`codegraph` 1.0.0 is one). A gate that names a fix that does not fix it costs a search. The
project here is a folder with the toolkit's own three scripts copied in, run as a project runs them, so it
shells out and is in the Makefile's SLOW list.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import ROOT

SCRIPTS = ROOT / "assets/toolkit/scripts/extensions"
STALE = "<!-- extension:indexer:begin -->\n## Indexer\nWhat an older package said.\n<!-- extension:indexer:end -->"
CURRENT = "<!-- extension:indexer:begin -->\n## Indexer\nWhat the package says now.\n<!-- extension:indexer:end -->"
#: An entry point as a publisher writes one: `GUIDANCE` as data, and a marker file whenever it is *run*, so a
#: test can tell a block rewritten from its text from one rewritten by running the extension's set-up again.
INIT = f'''from pathlib import Path
GUIDANCE = """
{CURRENT}
"""
if __name__ == "__main__":
    Path(__file__).with_name("ran").write_text("set up again")
'''


class ProjectionTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        place = self.root / "scripts/extensions"
        (place / "indexer").mkdir(parents=True)
        for name in ("project.py", "guidance.py", "hooks.py"):
            shutil.copy2(SCRIPTS / name, place / name)
        (place / "indexer/init.py").write_text(INIT, encoding="utf-8")
        (self.root / "project.json").write_text("{}\n", encoding="utf-8")
        (self.root / ".slipwai").mkdir()
        (self.root / ".slipwai/extensions.json").write_text(
            json.dumps({"schemaVersion": 1, "extensions": ["indexer"]}), encoding="utf-8")
        self.agents = self.root / "AGENTS.md"
        self.agents.write_text(f"# Repository guidance\n\nThe project's own words.\n\n{STALE}\n\nAnd after.\n",
                               encoding="utf-8")

    def run_projector(self, *flags: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "scripts/extensions/project.py", *flags], cwd=self.root, text=True,
                              capture_output=True, check=False)

    def test_a_drifted_block_fails_the_gate_naming_the_command_that_rewrites_it(self) -> None:
        checked = self.run_projector("--check")
        self.assertEqual(checked.returncode, 1)
        self.assertIn("the indexer extension block has drifted", checked.stderr)
        self.assertIn("`make agents`", checked.stderr)

    def test_the_command_it_names_rewrites_the_block_of_an_extension_with_no_project_hook(self) -> None:
        projected = self.run_projector()
        self.assertEqual(projected.returncode, 0, projected.stderr)
        text = self.agents.read_text(encoding="utf-8")
        self.assertIn(CURRENT, text)
        self.assertNotIn("What an older package said.", text)
        self.assertTrue(text.startswith("# Repository guidance\n\nThe project's own words.\n\n"), text)
        self.assertTrue(text.endswith("\n\nAnd after.\n"), "the block is replaced where it was")
        self.assertFalse((self.root / "scripts/extensions/indexer/ran").exists(),
                         "the block comes from GUIDANCE as data: the extension's set-up is not run again")
        checked = self.run_projector("--check")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn("1 elected extension block(s) match", checked.stdout)

    def test_a_block_already_current_and_a_file_that_is_not_there_are_left_alone(self) -> None:
        self.agents.write_text(f"# Guidance\n\n{CURRENT}\n", encoding="utf-8")
        before = self.agents.stat().st_mtime_ns
        self.assertEqual(self.run_projector().returncode, 0)
        self.assertEqual(self.agents.stat().st_mtime_ns, before, "nothing to rewrite, so nothing is written")
        self.agents.unlink()
        self.assertEqual(self.run_projector().returncode, 0)
        self.assertFalse(self.agents.exists())

    def test_an_extension_that_declares_no_guidance_is_not_a_reason_the_others_go_unwritten(self) -> None:
        other = self.root / "scripts/extensions/quiet"
        other.mkdir()
        (other / "init.py").write_text("pass\n", encoding="utf-8")
        (self.root / ".slipwai/extensions.json").write_text(
            json.dumps({"schemaVersion": 1, "extensions": ["indexer", "quiet"]}), encoding="utf-8")
        self.assertEqual(self.run_projector().returncode, 0)
        self.assertIn(CURRENT, self.agents.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
