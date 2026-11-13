"""`fleet.py tell --dark`: a hand-back that says which story it keeps dark, the one the merge gate accepts.

A hand-back about anything else let a slice with a dark story merge: recap's LB13 went through on one about its
design page, with a story whose data belonged to a subject nobody signs in as.
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
from captain_fixture import CHART

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT


class DarkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(TOOLKIT_ROOT / "scripts/agents", self.root / "scripts/agents")
        (self.root / "project.json").write_text(json.dumps({"layout": {"delivery": "."}}), encoding="utf-8")
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        self.log = logs.deck_path(self.root, "ordering", "ORD")
        self.log.parent.mkdir(parents=True)
        self.log.write_text(logs.entry("claimed", fairway="ORD", slice="ORD-01").line(), encoding="utf-8")

    def tell(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / "scripts/agents/fleet.py"), "tell", "ORD", *argv],
                              capture_output=True, text=True, cwd=self.root, check=False)

    def told(self) -> logs.Entry:
        return [e for e in logs.fold(self.log.read_text(encoding="utf-8").splitlines()) if e.kind == "told"][-1]

    def test_a_dark_hand_back_names_the_story_it_keeps_dark(self) -> None:
        # The message after the options, as `sail.md` spells it, which the plain parse refused.
        done = self.tell("--slice", "ORD-01", "--dark", "--need", "add the JWT library", "dark until it lands")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.told().fields["story"], "specs/ordering/slices/ORD-01/try-it.json")

    def test_a_hand_back_that_is_not_dark_names_no_story(self) -> None:
        self.tell("--slice", "ORD-01", "--need", "land the patterns in docs/design.md", "the page is the host's")
        self.assertNotIn("story", self.told().fields)

    def test_dark_needs_a_slice_and_a_need_to_mean_anything(self) -> None:
        for argv in (("--dark", "--need", "x", "no slice"), ("--slice", "ORD-01", "--dark", "no need")):
            with self.subTest(argv=argv):
                done = self.tell(*argv)
                self.assertNotEqual(done.returncode, 0)
                self.assertIn("--dark", done.stderr)


if __name__ == "__main__":
    unittest.main()
