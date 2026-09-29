"""`slipwai generate` in an empty folder makes that folder the project.

People make a folder for the project and run `generate` in it, then start their agent there: in the first real
run that found no commands, because the project had gone into a new folder beneath it (`slipwai-test/test`) and
Claude Code was started in `slipwai-test`. So an empty folder offers its own name and is written into, and the
output-parent question is not asked; anywhere else a new folder is made, as before.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import ROOT


class GenerateHereTest(FactoryTestCase):
    def test_an_empty_folder_is_the_project_and_is_offered_as_its_name(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            here = Path(parent) / "ledger"
            here.mkdir()
            result = subprocess.run(
                [str(ROOT / "slipwai"), "generate"], cwd=here, input="\n" * 20, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Project name [ledger]:", result.stdout)
            self.assertNotIn("Output parent", result.stdout)
            self.assertIn(f"created: {here}", result.stdout)
            self.assertEqual(json.loads((here / "project.json").read_text())["name"], "ledger")
            self.assertTrue((here / ".git").is_dir())
            self.assertFalse((here / "ledger").exists(), "a folder was made beneath the one the person stood in")
            self.assertEqual([p.name for p in Path(parent).iterdir()], ["ledger"], "staging left behind")

    def test_a_folder_that_is_not_empty_still_gets_a_new_folder(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            here = Path(parent)
            (here / "notes.txt").write_text("mine\n")
            # Name, then twelve defaults (the questions `test_cli` walks), then the output parent — answered, since
            # a checkout's default parent is the folder beside the checkout.
            result = subprocess.run(
                [str(ROOT / "slipwai"), "generate"], cwd=here, input="shop\n" + "\n" * 12 + f"{here}\n",
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Output parent", result.stdout)
            self.assertTrue((here / "shop/project.json").is_file())


class GenerateHereNamesTest(FactoryTestCase):
    def test_a_different_name_is_a_project_of_that_name_inside_the_empty_folder(self) -> None:
        """Typing `shop` in an empty `work` must not leave a `shop` project whose folder is called `work`."""
        with tempfile.TemporaryDirectory() as parent:
            here = Path(parent) / "work"
            here.mkdir()
            result = subprocess.run(
                [str(ROOT / "slipwai"), "generate"], cwd=here, input="shop\n" + "\n" * 20, text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((here / "shop/project.json").is_file())
            self.assertEqual([p.name for p in here.iterdir()], ["shop"], "staging or stray files left in the folder")

    def test_the_parent_of_an_empty_folder_need_not_be_writable(self) -> None:
        """A devcontainer's `/workspaces/app` under a root-owned `/workspaces`: staging goes inside the folder."""
        import os

        if os.geteuid() == 0:
            self.skipTest("root writes through permissions")
        with tempfile.TemporaryDirectory() as parent:
            here = Path(parent) / "app"
            here.mkdir()
            os.chmod(parent, 0o555)
            try:
                result = subprocess.run(
                    [str(ROOT / "slipwai"), "generate"], cwd=here, input="\n" * 20, text=True, capture_output=True,
                )
            finally:
                os.chmod(parent, 0o755)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((here / "project.json").is_file())


class OutputEncodingTest(FactoryTestCase):
    def test_a_redirected_stream_in_a_legacy_code_page_does_not_crash_the_questions(self) -> None:
        """Windows gives a redirected stdout cp1252, and the questions print `—` and `↑`: generate died with
        UnicodeEncodeError the moment its output went to a pipe or a CI log. Reproduced here by asking for cp1252."""
        import os

        with tempfile.TemporaryDirectory() as parent:
            here = Path(parent) / "ledger"
            here.mkdir()
            result = subprocess.run(
                [str(ROOT / "slipwai"), "generate"], cwd=here, input="\n" * 20, text=True, encoding="utf-8",
                capture_output=True, env=os.environ | {"PYTHONIOENCODING": "cp1252"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("UnicodeEncodeError", result.stderr)
            self.assertIn("event-modelling — Event Modeling", result.stdout)
