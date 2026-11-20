"""How long a storyboard drawing may take, read once for the board and for the project's script.

A drawing of twenty surfaces was ended at fifteen minutes with its pages half written and no storyboard, and
the board had ended it at a fixed nine hundred seconds without reading `harbour.json` at all. These hold the
ceiling to an hour, and the board's drawing — first, or carried on — to the same reading the script takes.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import board_settings, drawing_budget, stage_session
from slipwai.board_settings import Launch
from slipwai.init_run import draw, resumed

AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
STAND_IN = Launch("stand-in", "Stand-in", (sys.executable, str(AGENT)), "a script")


class CeilingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.harbour = self.root / "harbour.json"

    def test_a_first_drawing_has_an_hour_and_a_redraw_half_of_one(self) -> None:
        self.assertEqual(drawing_budget.seconds(self.harbour, redraw=False), 60 * 60)
        self.assertEqual(drawing_budget.seconds(self.harbour, redraw=True), 30 * 60)

    def test_a_row_a_person_wrote_is_read_as_it_stands_and_the_default_moves_with_the_telegraph(self) -> None:
        self.harbour.write_text(json.dumps({"stage_scale": 0.5, "stages": {"surfaces": {"minutes": 15}}}),
                                encoding="utf-8")
        self.assertEqual(drawing_budget.seconds(self.harbour, redraw=False), 15 * 60)
        self.assertEqual(drawing_budget.seconds(self.harbour, redraw=True), 15 * 60, "no row: thirty, halved")

    def test_the_session_is_told_its_minutes_and_when_they_end(self) -> None:
        told = drawing_budget.told(3600.0, started=0.0)
        self.assertEqual(told["SLIPWAI_BUDGET_MINUTES"], "60")
        self.assertRegex(told["SLIPWAI_BUDGET_ENDS"], r"^\d\d:\d\d$")


class BoardDrawingTest(unittest.TestCase):
    """The board's own drawing, over the protocol: the same ceiling, not a number of its own."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "specs" / "001-x").mkdir(parents=True)
        (self.root / "specs" / "001-x" / "spec.md").write_text("# spec\n", encoding="utf-8")
        for patched in (mock.patch.object(board_settings, "SETTINGS", self.root / "board.json"),
                        mock.patch.object(stage_session, "launchable", return_value=STAND_IN),
                        mock.patch("slipwai.init_run.Fitting")):
            patched.start()
            self.addCleanup(patched.stop)

    def limit(self, feature: str = "") -> float:
        with mock.patch.object(stage_session, "StageSession") as made:
            draw(self.root, None, feature)
        return float(made.call_args.kwargs["limit"])

    def test_a_drawing_the_board_runs_has_the_hour_and_a_redraw_the_half(self) -> None:
        self.assertEqual(self.limit(), 60 * 60)
        self.assertEqual(self.limit("001-x"), 30 * 60, "a named feature is a redraw after a no")

    def test_it_reads_the_row_in_harbour_json_as_make_surfaces_does(self) -> None:
        (self.root / "harbour.json").write_text(json.dumps({"stages": {"surfaces": {"minutes": 90}}}),
                                                encoding="utf-8")
        self.assertEqual(self.limit(), 90 * 60)


class CarriedOnTest(unittest.TestCase):
    def test_a_drawing_carried_on_has_a_first_drawing_s_ceiling_again(self) -> None:
        root = Path(tempfile.mkdtemp())
        with mock.patch.object(board_settings, "SETTINGS", root / "board.json"):
            fitting = resumed(root, "mockups")
        self.assertEqual(fitting.stage.limit, 60 * 60)


if __name__ == "__main__":
    unittest.main()
