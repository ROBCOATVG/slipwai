"""A further feature is asked about itself: its own storyboard, its own slices in the model, its own split.

A project that had finished its first feature took a second one through hand-over and specification, and
**Continue the build** exited 0 in a second: the model named a slice, a chart named a slice, so every stage
above the chart read as done, and the fleet was cast off on a chart with nothing left to start (#131). Each
question is now asked of the feature in hand, and these hold that a first feature's answers are not a later
one's — and that a project with one feature reads exactly as it did.
"""
from __future__ import annotations

import html
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import board_settings, stage_session
from slipwai.board_settings import Launch
from slipwai.feature_stages import approved_for, claims, home, in_hand, modelled_for, name_in_hand, split_for
from slipwai.init_run import CRUISE
from slipwai.launch_lock import held_for, line, unlock
from slipwai.passage import current, drawn_in_hand, modelled_in_hand, stages
from slipwai.stage_steps import launch_steps
from slipwai.upstream import drawing_of
from slipwai.voyage_page import now_said, passage_card

ROOT = Path(__file__).resolve().parent.parent
AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
STAND_IN = Launch("stand-in", "Stand-in", (sys.executable, str(AGENT)), "a script")
FIRST, FURTHER = "001-first", "002-further"
#: A model as a person writes one, and a chart as `make chart` dumps one: a list, and a mapping by id.
MODEL = ("version: 1\nslices:\n  - id: S1\n    name: one\n    frames:\n      - type: evt\n"
         "        feature: not-a-slice-key\n")
CHART = "v: 1\nfeature: 001-first\nfairways: {}\nslices:\n  S1:\n    fairway: a\n    sets: []\n"


def toolkit(name: str) -> Any:
    """A project script, loaded from the toolkit: it runs in a project, so it is not importable by name."""
    found = importlib.util.spec_from_file_location(f"toolkit_{name.replace('-', '_')}",
                                                   ROOT / "assets/toolkit/scripts" / name)
    assert found is not None and found.loader is not None
    module = importlib.util.module_from_spec(found)
    found.loader.exec_module(module)
    return module


class FurtherFeatureTest(unittest.TestCase):
    """One feature built — modelled, charted, split — and a second with its specification and nothing else."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        for name in (FIRST, FURTHER):
            (self.root / "specs" / name).mkdir(parents=True)
            (self.root / "specs" / name / "spec.md").write_text("# spec\n", encoding="utf-8")
        (self.root / "docs" / "event-model").mkdir(parents=True)
        self.model = self.root / "docs/event-model/model.yaml"
        self.model.write_text(MODEL, encoding="utf-8")
        self.chart = self.root / "specs" / FIRST / "chart.yaml"
        self.chart.write_text(CHART, encoding="utf-8")
        (self.root / "project.json").write_text(json.dumps({"profile": "event-modelling"}), encoding="utf-8")
        (self.root / ".specify").mkdir()
        (self.root / ".specify/feature.json").write_text(
            json.dumps({"feature_directory": f"specs/{FURTHER}"}), encoding="utf-8")
        for patched in (mock.patch.object(board_settings, "SETTINGS", self.root / "board.json"),
                        mock.patch.object(stage_session, "launchable", return_value=STAND_IN)):
            patched.start()
            self.addCleanup(patched.stop)

    def test_the_feature_in_hand_is_the_one_the_pointer_names(self) -> None:
        self.assertEqual(name_in_hand(self.root), FURTHER)
        (self.root / ".specify/feature.json").unlink()
        self.assertEqual(in_hand(self.root), self.root / "specs" / FURTHER, "the only one no chart holds")

    def test_slices_that_name_no_feature_are_the_feature_s_the_chart_is_written_under(self) -> None:
        self.assertEqual(claims(self.model), (set(), True), "a key nested in a frame is not the slice's")
        self.assertEqual(claims(self.chart), (set(), True))
        self.assertEqual(home(self.root), FIRST)
        self.assertTrue(modelled_for(self.root, FIRST))
        self.assertTrue(split_for(self.root, FIRST))

    def test_the_first_feature_s_model_and_chart_are_not_the_further_feature_s(self) -> None:
        self.assertFalse(modelled_for(self.root, FURTHER))
        self.assertFalse(split_for(self.root, FURTHER))
        self.assertFalse(modelled_in_hand(self.root))

    def test_a_slice_that_names_the_feature_puts_it_in_the_model_and_then_in_the_split(self) -> None:
        self.model.write_text(MODEL + f"  - id: S2\n    feature: {FURTHER}\n    name: two\n", encoding="utf-8")
        self.assertEqual(claims(self.model), ({FURTHER}, True))
        self.assertTrue(modelled_for(self.root, FURTHER))
        self.assertFalse(split_for(self.root, FURTHER), "modelled is not charted")
        self.chart.write_text(CHART + f"  S2:\n    fairway: a\n    feature: '{FURTHER}'\n", encoding="utf-8")
        self.assertTrue(split_for(self.root, FURTHER))
        self.assertTrue(split_for(self.root, FIRST))

    def test_a_dash_at_the_margin_is_read_as_a_list_too(self) -> None:
        self.model.write_text(f"slices:\n- feature: {FURTHER}\n  id: S9\n- id: S1\nstreams: {{}}\n", encoding="utf-8")
        self.assertEqual(claims(self.model), ({FURTHER}, True))

    def test_a_launch_of_the_further_feature_charts_and_splits_it_before_it_casts_off(self) -> None:
        steps = launch_steps(self.root)
        self.assertEqual(len(steps), 3, "the first feature's chart named a slice, and the launch only cast off")
        self.assertIsNotNone(steps[0].session)
        self.assertEqual(steps[0].about, FURTHER)
        self.chart.write_text(CHART + f"  S2:\n    fairway: a\n    feature: {FURTHER}\n", encoding="utf-8")
        self.assertEqual([one.argv for one in launch_steps(self.root)][-1], CRUISE)
        self.assertEqual(len(launch_steps(self.root)), 2, "its own slices are charted: enable and cast off")

    def test_the_storyboard_drawn_is_the_further_feature_s_and_an_earlier_one_is_not_it(self) -> None:
        self.assertEqual(drawing_of(self.root), FURTHER)
        earlier = self.root / "specs" / FIRST / "mockups"
        earlier.mkdir()
        (earlier / "mock-states.md").write_text("- Home · empty — approved\n", encoding="utf-8")
        (earlier / "home.html").write_text("<html></html>", encoding="utf-8")
        self.assertFalse(drawn_in_hand(self.root))
        self.assertTrue(approved_for(self.root, FIRST))
        self.assertFalse(approved_for(self.root, FURTHER), "the model waits on this feature's verdict")

    def test_a_drawn_further_feature_waits_on_its_own_verdict_and_not_an_earlier_one_s(self) -> None:
        """manda: the second feature's 44 states were all approved, the third was drawn and waiting, and the
        strip read "44 of 44 states approved", ticked the storyboard and sent the person to cast off."""
        earlier = self.root / "specs" / FIRST / "mockups"
        earlier.mkdir()
        (earlier / "mock-states.md").write_text("## Surface: Home\n- empty \u2014 approved\n"
                                                 "- populated \u2014 approved\n", encoding="utf-8")
        (earlier / "home.html").write_text("<html></html>", encoding="utf-8")
        drawing = self.root / "specs" / FURTHER / "mockups"
        drawing.mkdir()
        (drawing / "nda.html").write_text("<html></html>", encoding="utf-8")
        found = {stage.key: stage for stage in stages(self.root, slices={"done": 1})}
        self.assertEqual(found["storyboard"].state, "waiting")
        self.assertNotIn("2 of 2", found["storyboard"].detail, "the earlier feature's verdicts are not this one's")
        self.assertEqual(current(list(found.values())).key, "storyboard",  # type: ignore[union-attr]
                         "the verdict is what moves the project, not the fleet")
        self.assertIn("Approve storyboard", now_said(list(found.values())))
        (drawing / "mock-states.md").write_text("## Surface: NDA\n- ready \u2014 approved\n", encoding="utf-8")
        found = {stage.key: stage for stage in stages(self.root, slices={"done": 1})}
        self.assertEqual((found["storyboard"].state, found["storyboard"].detail), ("done", "1 of 1 states approved"))

    def test_a_modelled_further_feature_is_on_its_chart_and_not_on_an_earlier_one_s_stopped_fleet(self) -> None:
        """manda: the third feature approved and modelled, the second's fleet stopped on a park, and the board
        said *Now: slices — stopped until you act … Next: make cruise* over the chart that moved the project."""
        drawing = self.root / "specs" / FURTHER / "mockups"
        drawing.mkdir()
        (drawing / "nda.html").write_text("<html></html>", encoding="utf-8")
        (drawing / "mock-states.md").write_text("## Surface: NDA\n- ready \u2014 approved\n", encoding="utf-8")
        self.model.write_text(MODEL + f"  - id: S2\n    name: two\n    feature: {FURTHER}\n", encoding="utf-8")
        (self.root / ".specify/integration.json").write_text('{"default_integration": "claude"}', encoding="utf-8")
        (self.root / ".specify/memory").mkdir()
        (self.root / ".specify/memory/constitution.md").write_text("# Ratified\n", encoding="utf-8")
        stopped = {"inbox": [{"kind": "parked", "fairway": "a", "slice": "S1", "what": "S1: stuck."}]}
        found = stages(self.root, fleet=stopped, slices={"done": 1})
        said = {stage.key: stage for stage in found}
        self.assertEqual((said["model"].state, said["chart"].state, said["slices"].state), ("done", "todo", "waiting"))
        self.assertEqual(current(found).key, "chart")  # type: ignore[union-attr]
        line = now_said(found)
        self.assertTrue(line.startswith(f"Now: chart & split — {FURTHER} is not charted or split yet."), line)
        self.assertIn("Meanwhile, the earlier features' slices: stopped until you act: 1 park.", line,
                      "the earlier feature's stop is still said, after the step that moves this one")
        reason = "the storyboard for 001-first has changed since its verdict (Home): approve it again first"
        card = passage_card("manda", found, False, False, held=held_for(found, reason))
        self.assertIn('id="launch" disabled>Continue the build', card, "locked and shown, never hidden")
        self.assertIn(html.escape(reason), card)
        self.assertIn('href="#mockups">Open the storyboard to approve it</a>', card, "the way to unlock it is a link")

    def test_a_launch_held_by_an_earlier_storyboard_carries_that_storyboard_s_verdict(self) -> None:
        """manda: the lock said to approve 002's storyboard again, and the only Approve on the page was 003's,
        given already and disabled; the person had nothing to press."""
        earlier = self.root / "specs" / FIRST / "mockups"
        earlier.mkdir()
        (earlier / "home.html").write_text("<html></html>", encoding="utf-8")
        (earlier / "mock-states.md").write_text("## Surface: Home\n- empty \u2014 approved\n", encoding="utf-8")
        held = f"the storyboard for {FIRST} has changed since its verdict (Home): approve or disapprove it again first"
        form = unlock(self.root, held)
        self.assertIn(f'data-storyboard="{FIRST}" data-verdict="approved"', form)
        self.assertIn(f"specs/{FIRST}/mockups/storyboard.html", form)
        self.assertEqual(unlock(self.root, "a fleet is running in this project"), "", "only a storyboard's lock")
        drawn = line(held, form)
        self.assertIn(form, drawn)
        self.assertIn('href="#mockups" hidden>', drawn, "the tab link gives way to the verdict itself")

    def test_the_session_poll_leaves_a_locked_launch_shown(self) -> None:
        """manda's live board hid the locked button again: the session card's poll set `hidden` from
        `launchable` alone, after the strip's poll had shown it disabled."""
        from slipwai.bridge_page import SCRIPT
        self.assertIn("launch.hidden = !said.launchable && !(launch.disabled && launch.id === 'launch')", SCRIPT)

    def test_a_held_launch_is_not_shown_where_the_chart_is_not_the_next_step(self) -> None:
        found = stages(self.root, slices={"done": 1})
        self.assertNotEqual(current(found).key, "chart")  # type: ignore[union-attr]
        self.assertEqual(held_for(found, "anything"), "")
        self.assertIn('id="launch" hidden>', passage_card("manda", found, False, False, held=held_for(found, "x")))

    def test_the_strip_says_the_further_feature_is_not_modelled_or_split(self) -> None:
        found = {stage.key: stage for stage in stages(self.root, slices={"done": 1})}
        self.assertEqual((found["model"].state, found["chart"].state), ("todo", "todo"))
        self.assertIn(FURTHER, found["model"].detail)
        self.assertIn(FURTHER, found["chart"].detail)

    def test_the_project_s_scripts_hear_the_same_answer(self) -> None:
        carried = toolkit("agents/feature_stages.py")
        self.assertFalse(carried.split_for(self.root, FURTHER))
        self.assertTrue(carried.split_for(self.root, FIRST))
        self.assertEqual(carried.name_in_hand(self.root), FURTHER)


class OneFeatureTest(unittest.TestCase):
    """What every project was before this: one feature, and slices that say nothing about which."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "specs" / FIRST).mkdir(parents=True)
        (self.root / "specs" / FIRST / "spec.md").write_text("# spec\n", encoding="utf-8")
        (self.root / "docs" / "event-model").mkdir(parents=True)
        (self.root / "project.json").write_text(json.dumps({"profile": "event-modelling"}), encoding="utf-8")

    def test_nothing_modelled_is_nothing_modelled(self) -> None:
        self.assertFalse(modelled_in_hand(self.root))
        self.assertFalse(split_for(self.root, FIRST))

    def test_a_model_and_a_chart_that_name_no_feature_are_this_one_s(self) -> None:
        (self.root / "docs/event-model/model.yaml").write_text(MODEL, encoding="utf-8")
        self.assertTrue(modelled_in_hand(self.root))
        self.assertFalse(split_for(self.root, FIRST))
        (self.root / "specs" / FIRST / "chart.yaml").write_text(CHART, encoding="utf-8")
        self.assertTrue(split_for(self.root, FIRST))

    def test_a_chart_under_a_directory_with_no_specification_is_the_first_feature_s(self) -> None:
        (self.root / "docs/event-model/model.yaml").write_text(MODEL, encoding="utf-8")
        (self.root / "specs" / "model").mkdir()
        (self.root / "specs" / "model" / "chart.yaml").write_text(CHART, encoding="utf-8")
        self.assertEqual(home(self.root), FIRST)
        self.assertTrue(modelled_for(self.root, FIRST))
        self.assertTrue(split_for(self.root, FIRST))

    def test_an_empty_list_names_nobody(self) -> None:
        (self.root / "docs/event-model/model.yaml").write_text("slices: []\n", encoding="utf-8")
        self.assertEqual(claims(self.root / "docs/event-model/model.yaml"), (set(), False))
        self.assertFalse(modelled_for(self.root, FIRST))


class ChartCarriesTheFeatureTest(unittest.TestCase):
    def test_the_chart_says_which_feature_a_slice_is_only_where_the_model_does(self) -> None:
        chart = toolkit("event-model/chart.py")
        model = {"slices": [{"id": "S1", "context": "a", "frames": []},
                            {"id": "S2", "context": "a", "feature": FURTHER, "frames": []}]}
        rendered = chart.render(model, {"api": {"path": "services/api", "contexts": ["a"]}})["slices"]
        self.assertNotIn("feature", rendered["S1"])
        self.assertEqual(rendered["S2"]["feature"], FURTHER)


if __name__ == "__main__":
    unittest.main()
