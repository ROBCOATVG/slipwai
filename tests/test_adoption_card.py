"""The voyage's adoption card: the sequence `adopt --next` reads, for a repository that was adopted."""
from __future__ import annotations

import datetime
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import adoption_card as card
from slipwai.assets import TOOLKIT_ROOT
from slipwai.next_steps import Step


class AdoptionCardTest(unittest.TestCase):
    def test_a_generated_project_has_no_card(self) -> None:
        root = Path(tempfile.mkdtemp())
        self.assertEqual(card.adoption_card(root), "")
        (root / "project.json").write_text(json.dumps({"name": "made"}))
        with mock.patch.object(card, "adoption_of", return_value=None):
            self.assertEqual(card.adoption_card(root), "")

    def test_the_first_step_not_done_is_the_one_to_do_now(self) -> None:
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text(json.dumps({"name": "kept"}))
        said = [Step("./adopt/init", "installs", True), Step("/ground, in the agent", "asks", False),
                Step("/verify", "the gate", False)]
        with mock.patch.object(card, "read_manifest", return_value={}), \
                mock.patch.object(card, "adoption_of", return_value=mock.Mock(strategy={})), \
                mock.patch.object(card, "layout_of"), mock.patch.object(card, "apps_from_manifest"), \
                mock.patch.object(card.next_steps, "steps", return_value=said):
            page = card.adoption_card(root)
        self.assertIn('<li class="done"><b>done</b> ./adopt/init', page)
        self.assertIn('<li class="now"><b>now</b> /ground, in the agent', page)
        self.assertIn('<li class="then"><b>then</b> /verify', page)

    def test_from_the_first_specification_the_strip_takes_over(self) -> None:
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text(json.dumps({"name": "kept"}))
        said = [Step("/speckit-specify, in the agent", "the first feature", True),
                Step("/sail, in the agent", "", False)]
        with mock.patch.object(card, "read_manifest", return_value={}), \
                mock.patch.object(card, "adoption_of", return_value=mock.Mock(strategy={})), \
                mock.patch.object(card, "layout_of"), mock.patch.object(card, "apps_from_manifest"), \
                mock.patch.object(card.next_steps, "steps", return_value=said):
            self.assertEqual(card.adoption_card(root), "")

    def test_a_checkpoint_after_the_first_specification_stands_above_the_strip_not_in_its_place(self) -> None:
        """A card in the adoption's place is drawn instead of the strip, and the page's script wires no button
        without the strip: a rewrite's storyboard could not be approved while its checkpoint was shown there."""
        from slipwai.voyage_page import page as voyage
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text(json.dumps({"name": "kept"}))
        said = [Step("/speckit-specify, in the agent", "the first feature", True)]
        checkpoint = mock.Mock(strategy={"decided": "rewrite", "lines": {"Checkpoint": "2999-01-01"}})
        with mock.patch.object(card, "read_manifest", return_value={}), \
                mock.patch.object(card, "adoption_of", return_value=checkpoint), \
                mock.patch.object(card, "layout_of"), mock.patch.object(card, "apps_from_manifest"), \
                mock.patch.object(card.next_steps, "steps", return_value=said):
            self.assertEqual(card.adoption_card(root), "")
            dates = card.strategy_dates(root)
        self.assertIn('id="strategy-dates"', dates)
        page = voyage(root, [], [], "", "", "", "", None, False, dates=dates)
        self.assertIn('class="passage"', page)
        self.assertLess(page.index('id="strategy-dates"'), page.index('class="passage"'))

    def test_while_a_step_runs_there_is_nothing_to_press_a_second_time(self) -> None:
        """A control drawn while `./init` ran was still there when it ended, and pressed, ran it again."""
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text(json.dumps({"name": "kept"}))
        said = [Step("./adopt/init", "installs", False), Step("/verify", "the gate", False)]
        with mock.patch.object(card, "read_manifest", return_value={}), \
                mock.patch.object(card, "adoption_of", return_value=mock.Mock(strategy={})), \
                mock.patch.object(card, "layout_of"), mock.patch.object(card, "apps_from_manifest"), \
                mock.patch.object(card.next_steps, "steps", return_value=said):
            idle, running = card.adoption_card(root), card.adoption_card(root, running=True)
        self.assertIn('data-step="init"', idle)
        self.assertNotIn("data-step=", running)
        self.assertIn('id="step-running"', running)


class DatesTest(unittest.TestCase):
    """The strategy's checkpoint, or a left system's review, runs the length of the programme."""

    def test_a_date_ahead_is_said_and_a_date_passed_puts_the_decision_again(self) -> None:
        root = Path(tempfile.mkdtemp())
        record = {"decided": "strangler-fig", "lines": {"Checkpoint": "2027-04-26"}}
        ahead = card.dates_card(root, {"name": "shop"}, record, today=datetime.date(2027, 4, 20))
        self.assertIn("in 6 days", ahead)
        self.assertNotIn("data-step", ahead)
        with mock.patch.object(card, "proposed", return_value=None):
            passed = card.dates_card(root, {"name": "shop"}, record, today=datetime.date(2027, 5, 1))
        self.assertIn("The checkpoint has passed", passed)
        self.assertIn("`End: partial`", passed, "a strangler fig is offered what it can change, not itself")
        rewrite = {"decided": "rewrite", "lines": {"Checkpoint": "2027-04-26"}}
        with mock.patch.object(card, "proposed", return_value=None):
            later = card.dates_card(root, {}, rewrite, today=datetime.date(2027, 5, 1))
        self.assertIn("switch to a strangler fig", later)
        self.assertIn('data-step="strategy"', passed, "deciding again is one press away")

    def test_a_left_system_is_dated_by_its_review_and_nothing_else_has_no_card(self) -> None:
        root = Path(tempfile.mkdtemp())
        left = {"decided": "leave-it", "lines": {"Review": "2027-01-01"}}
        self.assertIn("<b>Review</b>", card.dates_card(root, {}, left, today=datetime.date(2026, 12, 1)))
        self.assertEqual(card.dates_card(root, {}, {"decided": "in-place", "lines": {}}), "")


class DraftTest(unittest.TestCase):
    def test_an_adopted_repository_drafts_from_the_prd_under_its_delivery_folder(self) -> None:
        """The board writes `adopt/docs/prd.md`; the draft looked for `docs/prd.md` at the root, and stopped."""
        root = Path(tempfile.mkdtemp())
        (root / "project.json").write_text("{}")
        shutil.copytree(TOOLKIT_ROOT / "scripts/agents", root / "adopt/scripts/agents")
        ran = subprocess.run([sys.executable, str(root / "adopt/scripts/agents/draft.py")], cwd=root,
                             capture_output=True, text=True, check=False)
        self.assertEqual(ran.returncode, 2)
        self.assertIn("adopt/docs/prd.md is not a file", ran.stderr)


if __name__ == "__main__":
    unittest.main()
