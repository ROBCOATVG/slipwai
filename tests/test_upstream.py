"""The steps above the chart, advanced without a person where the project says so.

`next_step` is the whole decision and is tested as one: which button the board would press next, given what
the tree holds and whether the board is idle. `advance` is the press, against a stand-in for the bridge.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project.cruise import cruise_config
from slipwai.upstream import APPROVED_BY, advance, next_step, unjudged
from slipwai.wheel import CONFIG, orders


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".specify").mkdir()
        (self.root / CONFIG).write_text(cruise_config(), encoding="utf-8")
        (self.root / "specs/001-orders").mkdir(parents=True)
        (self.root / "specs/001-orders/spec.md").write_text("# Orders\n", encoding="utf-8")

    def answer(self, **given: str) -> None:
        held = json.loads((self.root / CONFIG).read_text(encoding="utf-8"))
        (self.root / CONFIG).write_text(json.dumps({**held, **given}), encoding="utf-8")

    def draw(self) -> None:
        mockups = self.root / "specs/001-orders/mockups"
        mockups.mkdir(parents=True, exist_ok=True)
        (mockups / "basket.html").write_text("<title>Basket</title><article><h2>Empty</h2></article>",
                                             encoding="utf-8")

    def judge(self, verdict: str) -> None:
        (self.root / "specs/001-orders/mockups/mock-states.md").write_text(
            f"## Surface: Basket\n- Empty — {verdict}\n", encoding="utf-8")


class NextStepTest(Fixture):
    def test_a_fresh_project_stops_for_a_person_at_every_step(self) -> None:
        """The default is the stop the board has always made: a specification somebody has read."""
        self.assertEqual(orders(self.root)["upstream"], "park")
        self.assertEqual(next_step(self.root, idle=True, drawable=True, launchable=True), "")

    def test_advancing_draws_the_storyboard_after_the_specification(self) -> None:
        self.answer(upstream="advance")
        self.assertEqual(next_step(self.root, idle=True, drawable=True, launchable=True), "draw")

    def test_a_drawn_storyboard_with_no_verdict_is_approved_next(self) -> None:
        self.answer(upstream="advance")
        self.draw()
        self.assertEqual(unjudged(self.root), "001-orders")
        self.assertEqual(next_step(self.root, idle=True, drawable=False, launchable=True), "approve 001-orders")

    def test_an_approved_storyboard_continues_the_build(self) -> None:
        self.answer(upstream="advance")
        self.draw()
        self.judge("approved")
        self.assertEqual(next_step(self.root, idle=True, drawable=False, launchable=True), "launch")

    def test_a_disapproved_storyboard_is_a_person_s_no_and_nothing_advances(self) -> None:
        self.answer(upstream="advance")
        self.draw()
        self.judge("parked: the basket needs a total")
        self.assertEqual(next_step(self.root, idle=True, drawable=False, launchable=True), "")

    def test_nothing_is_pressed_while_a_step_runs_or_after_one_failed(self) -> None:
        self.answer(upstream="advance")
        self.assertEqual(next_step(self.root, idle=False, drawable=True, launchable=True), "")

    def test_a_stage_that_found_nothing_to_draw_is_not_drawn_again(self) -> None:
        """It writes `mock-states.md` and no page, and `drawable` reads pages."""
        self.answer(upstream="advance")
        (self.root / "specs/001-orders/mockups").mkdir()
        (self.root / "specs/001-orders/mockups/mock-states.md").write_text("surfaces: none\n", encoding="utf-8")
        self.assertEqual(next_step(self.root, idle=True, drawable=True, launchable=True), "launch")


class Board:
    """The bridge as `advance` sees it: a project, its running child, and the buttons' own guards."""

    def __init__(self, root: Path, drawable: bool = False, launchable: bool = False) -> None:
        self.root, self.fitting, self.launched = root, None, False
        self._drawable, self._launchable = drawable, launchable
        self.verdicts: list[str] = []

    def drawable(self) -> bool:
        return self._drawable

    def launchable(self) -> bool:
        return self._launchable

    def after_storyboard(self, said: str) -> str:
        self.verdicts.append(said)
        return said


class AdvanceTest(Fixture):
    def test_an_approval_the_board_gave_says_it_was_not_a_person(self) -> None:
        """`mock-states.md` is what the model and the chart read as a person's verdict."""
        self.answer(upstream="advance")
        self.draw()
        board = Board(self.root)
        advance(board)
        self.assertEqual(board.verdicts, ["approved"], "and the step after it is started as a person's would be")
        written = (self.root / "specs/001-orders/mockups/mock-states.md").read_text(encoding="utf-8")
        self.assertTrue(written.startswith(APPROVED_BY))
        self.assertIn("— approved", written)

    def test_a_project_left_at_park_is_never_pressed_for(self) -> None:
        self.draw()
        board = Board(self.root, launchable=True)
        advance(board)
        self.assertEqual((board.verdicts, board.fitting, board.launched), ([], None, False))


class SettingTest(Fixture):
    def run_script(self, *argv: str) -> subprocess.CompletedProcess:
        place = self.root / "scripts/agents"
        place.mkdir(parents=True, exist_ok=True)
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        (place / "cruise.py").write_text((TOOLKIT_ROOT / "scripts/agents/cruise.py").read_text(encoding="utf-8"),
                                         encoding="utf-8")
        return subprocess.run([sys.executable, str(place / "cruise.py"), *argv], capture_output=True,
                              text=True, cwd=self.root, timeout=30)

    def test_a_project_written_before_the_setting_still_passes_its_own_check(self) -> None:
        held = json.loads((self.root / CONFIG).read_text(encoding="utf-8"))
        del held["upstream"]
        (self.root / CONFIG).write_text(json.dumps(held), encoding="utf-8")
        done = self.run_script("--check")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(orders(self.root)["upstream"], "park", "and the card shows it at its default")

    def test_the_project_s_own_script_turns_it_on_and_off(self) -> None:
        for value in ("advance", "park"):
            done = self.run_script("--set", f"upstream={value}")
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(orders(self.root)["upstream"], value)
        self.assertNotEqual(self.run_script("--set", "upstream=sometimes").returncode, 0)


if __name__ == "__main__":
    unittest.main()
