"""A hand-back's need and question carry a plain line, and `fleet.py tell --need` refuses one without it (#172).

manda's board was written in the slice agent's words for another agent: file paths, line numbers,
`maxReceiveCount`, `S110-decide-2: docs/event-model/model.yaml, per D523: …`. Whoever used only the board could
not tell what was asked or why it was theirs. The plain line is held to the rule a decision's **In short** is.
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

PLAIN = "The several-signatories screen cannot be tried, because the staff list has only two people."


class PlainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
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
        return self.lines("told")[-1]

    def lines(self, kind: str) -> list[logs.Entry]:
        return [e for e in logs.fold(self.log.read_text(encoding="utf-8").splitlines()) if e.kind == kind]

    def test_a_need_carries_its_plain_line(self) -> None:
        done = self.tell("--slice", "ORD-01", "--need", "a third BD in seed/staff.json", "--plain", PLAIN,
                         "--check", "text:seed/staff.json:Priya", "the walk could not reach it")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.told().fields["needs"][0]["plain"], PLAIN)

    def test_a_need_without_one_or_with_a_path_in_it_is_refused(self) -> None:
        for argv in (("--need", "a third BD", "--check", "text:seed/staff.json:Priya", "no plain"),
                     ("--need", "a third BD", "--plain", "Add Priya to apps/app/seed/staff.json.", "a path"),
                     ("--need", "one", "--need", "two", "--plain", PLAIN, "one plain for two needs")):
            with self.subTest(argv=argv):
                done = self.tell("--slice", "ORD-01", *argv)
                self.assertNotEqual(done.returncode, 0)
                self.assertIn("--plain", done.stderr)
        self.assertEqual(self.lines("told"), [], "nothing was written")

    def test_a_question_asked_for_a_decision_carries_the_need_s_plain_line(self) -> None:
        done = self.tell("--slice", "ORD-01", "--need", "a follow-up slice for the help links", "--plain", PLAIN,
                         "--check", "decide", "a follow-up slice is recommended")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines("question")[-1].fields["plain"], PLAIN)

    def test_a_model_patch_is_not_asked_as_a_question(self) -> None:
        """manda's careen handed back a patch that brought the model in line with events.ts, and it was asked
        as a decision nobody needed to make; it lands with the careen's merge."""
        done = self.tell("--slice", "ORD-01", "--need",
                         "apply specs/ordering/slices/ORD-01/handback/model-frame.patch", "--plain", PLAIN,
                         "--check", "text:docs/event-model/model.yaml:name: OrderPlaced", "the frame is the host's")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.lines("question"), [])
        self.assertNotIn("decide", self.told().fields["needs"][0])


if __name__ == "__main__":
    unittest.main()
