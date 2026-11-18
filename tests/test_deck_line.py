"""The door a slice's session writes its `mark-set` and `demo` lines through.

game-club-manager's TB1 was built and accepted and could not say so: there was no command for either line,
the session appended them by hand, and its harness refused a session editing the record it is judged by.
The command is held to what a hand never was — the chart's `sets`, and the three verdicts a demo can have.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"
CHART = """slices:
  TB1:
    fairway: tables
    sets: [ClubWeekSet]
    steers_by: []
  TB2:
    fairway: tables
    sets: [TableBooked]
    steers_by: [ClubWeekSet]
"""


class DeckLineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts/agents").mkdir(parents=True)
        for name in ("deck_line.py", "clearance.py", "logs.py", "capabilities.py"):
            shutil.copy(AGENTS / name, self.tree / "scripts/agents" / name)
        (self.tree / "project.json").write_text("{}", encoding="utf-8")
        (self.tree / "specs/001-club").mkdir(parents=True)
        (self.tree / "specs/001-club/chart.yaml").write_text(CHART, encoding="utf-8")

    def run_line(self, *argv: str, fairway: str = "") -> subprocess.CompletedProcess[str]:
        env = {key: value for key, value in os.environ.items() if key != "SLIPWAI_FAIRWAY"}
        with mock.patch.dict(os.environ, env | ({"SLIPWAI_FAIRWAY": fairway} if fairway else {}), clear=True):
            return subprocess.run([sys.executable, "-B", "scripts/agents/deck_line.py", *argv], cwd=self.tree,
                                  capture_output=True, text=True, check=False, env=dict(os.environ))

    def deck(self, fairway: str = "tables") -> list[logs.Entry]:
        path = logs.deck_path(self.tree, "001-club", fairway)
        return logs.fold(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else []

    def test_a_mark_the_chart_says_the_slice_sets_is_written_to_its_fairway_s_log(self) -> None:
        done = self.run_line("mark-set", "--slice", "TB1", "--mark", "ClubWeekSet")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("mark-set: TB1 — ClubWeekSet", done.stdout)
        [line] = self.deck()
        self.assertEqual((line.kind, line.fields["slice"], line.fields["mark"], line.fields["fairway"]),
                         ("mark-set", "TB1", "ClubWeekSet", "tables"))

    def test_a_mark_another_slice_sets_is_refused_and_nothing_is_written(self) -> None:
        done = self.run_line("mark-set", "--slice", "TB1", "--mark", "TableBooked")
        self.assertEqual(done.returncode, 1)
        self.assertIn("the chart says TB1 sets ClubWeekSet, not 'TableBooked'", done.stderr)
        self.assertEqual(self.deck(), [])

    def test_a_slice_the_chart_does_not_hold_is_refused(self) -> None:
        done = self.run_line("demo", "--slice", "TB9", "--verdict", "accepted")
        self.assertEqual(done.returncode, 1)
        self.assertIn("TB9 is not a slice on specs/001-club/chart.yaml", done.stderr)

    def test_a_demo_carries_one_of_the_three_verdicts(self) -> None:
        self.assertEqual(self.run_line("demo", "--slice", "TB1", "--verdict", "accepted", "--by",
                                       "sail-demo-hand", "--log", "specs/001-club/slices/TB1/demo-log.md")
                         .returncode, 0)
        self.assertEqual(self.deck()[0].fields["by"], "sail-demo-hand")
        refused = self.run_line("demo", "--slice", "TB1", "--verdict", "fine")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("deck_line: no `demo` line for TB1", refused.stderr)
        self.assertEqual([(e.kind, e.fields["verdict"]) for e in self.deck()], [("demo", "accepted")])

    def test_the_captain_s_fairway_is_where_a_dispatched_session_s_line_goes(self) -> None:
        self.assertEqual(self.run_line("demo", "--slice", "TB1", "--verdict", "behaviour",
                                       fairway="clubs").returncode, 0)
        self.assertEqual([e.fields["fairway"] for e in self.deck("clubs")], ["clubs"])
        self.assertEqual(self.deck("tables"), [])


if __name__ == "__main__":
    unittest.main()
