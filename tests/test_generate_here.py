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
