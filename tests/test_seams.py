"""A context boundary is tested three ways, on both profiles, and a shared noun settles nothing.

The context step asked the model one question — does any word mean two things? — and a product whose host,
player, organiser and trust record all say *listing* and mean the same listing came out as one fairway, 39
slices long. Game Finder is kept here as it was modelled (`tests/fixtures/game-finder/model.yaml`), and
what is held is the two halves of the characterisation: the evidence laid out from that model has to show
more than one candidate, and a one-stream model has to come out as one. Around that, the prose on both
profiles has to ask the same three questions, say that a shared noun is evidence for neither side, and no
longer tell a reader that one vocabulary is the whole decision.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
import yaml  # type: ignore[import-untyped]

from slipwai.project import commands

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "assets/toolkit/scripts/event-model"
GAME_FINDER = ROOT / "tests/fixtures/game-finder/model.yaml"
BOOKING = ROOT / "tests/fixtures/docs/model.yaml"

NINE_STEPS = ROOT / "assets/toolkit/skills/event-modeling/references/nine-steps.md"
EVENT_SKILL = ROOT / "assets/toolkit/skills/event-modeling/SKILL.md"
MODEL_SKILL = ROOT / "assets/toolkit/skills/global-event-model/SKILL.md"
CHART = ROOT / "assets/toolkit/commands/chart.md"
CONTEXTS = ROOT / "assets/toolkit/skills/domain-driven-design/resources/bounded-contexts.md"


def toolkit_module(name: str) -> Any:
    """A toolkit script, loaded from the asset. It runs in a project, so it is not importable by name."""
    specification = importlib.util.spec_from_file_location(f"toolkit_{name}", SCRIPTS / f"{name}.py")
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


seams = toolkit_module("seams")
check = toolkit_module("check")


def flat(text: str) -> str:
    return " ".join(text.split())


ONE_STREAM = """
version: 1
slices:
  - id: TD-01
    context: todo
    pattern: state-change
    actor: Person
    stream: list-{listId}
    frames:
      - {type: ui, name: ListPage}
      - {type: cmd, name: AddItem}
      - {type: evt, name: ItemAdded}
  - id: TD-02
    context: todo
    pattern: state-change
    actor: Person
    stream: list-{listId}
    frames:
      - {type: ui, name: ListPage}
      - {type: cmd, name: TickItem}
      - {type: evt, name: ItemTicked}
  - id: TD-03
    context: todo
    pattern: state-view
    actor: Person
    reads: [ItemAdded, ItemTicked]
    frames:
      - {type: rmo, name: TheList}
      - {type: ui, name: ListPage}
"""


class GameFinderCharacterisationTest(unittest.TestCase):
    """The run that produced one fairway: the evidence the rule now reads has to show more than that."""

    def setUp(self) -> None:
        self.found = seams.seams(yaml.safe_load(GAME_FINDER.read_text(encoding="utf-8")))

    def test_the_fixture_is_the_run_as_it_was_left(self) -> None:
        """One context, `finding`, on every slice — the fixture is not pre-corrected."""
        model = yaml.safe_load(GAME_FINDER.read_text(encoding="utf-8"))
        self.assertEqual(len(model["slices"]), 39)
        self.assertEqual({item["context"] for item in model["slices"]}, {"finding"})

    def test_more_than_one_candidate_comes_out_of_one_vocabulary(self) -> None:
        streams = [item["stream"] for item in self.found["candidates"]]
        self.assertEqual(streams, ["account", "listing", "feedback", "community"])

    def test_the_host_side_is_its_own_candidate_with_its_own_actors_and_reasons(self) -> None:
        """Publishing, seating and the night's end are one stream, and that stream is not `finding`'s."""
        listing = next(item for item in self.found["candidates"] if item["stream"] == "listing")
        self.assertEqual(listing["actors"], ["Host", "Player"])
        self.assertIn("ListingPublished", listing["events"])
        self.assertIn("SeatAccepted", listing["events"])
        self.assertIn("NightCancelled", listing["events"])
        self.assertIn("Host a table", listing["capabilities"])

    def test_a_stream_is_never_cut_into_stages(self) -> None:
        """Every writer of `listing` is in the one candidate, whatever capability it was split into."""
        listing = next(item for item in self.found["candidates"] if item["stream"] == "listing")
        self.assertEqual(len(listing["writers"]), 15)
        self.assertEqual(self.found["split_streams"], [])

    def test_the_discovery_views_are_shown_reading_across(self) -> None:
        """What `finding` was named after writes nothing and folds three streams — said, not hidden."""
        across = {view["slice"]: view for view in self.found["across"]}
        self.assertIn("S34", across)
        self.assertEqual(set(across["S34"]["folds"]), {"listing", "community", "feedback"})
        self.assertEqual(across["S34"]["name"], "See tables near you")

    def test_the_report_names_the_candidates_and_points_at_the_method(self) -> None:
        text = seams.report(self.found)
        self.assertIn("4 candidates", text)
        self.assertIn("in 1 context today", text)
        self.assertIn("reads across several candidates", text)
        self.assertIn("The Seam Tests", text)
        self.assertNotIn("One stream, so one candidate", text)


class SingleContextStaysOneTest(unittest.TestCase):
    """The other half: a product with one stream is one candidate, and the rule says so."""

    def test_one_stream_is_one_candidate_and_no_seam(self) -> None:
        found = seams.seams(yaml.safe_load(ONE_STREAM))
        self.assertEqual([item["stream"] for item in found["candidates"]], ["list"])
        self.assertEqual(found["candidates"][0]["slices"], ["TD-01", "TD-02", "TD-03"])
        self.assertEqual(found["across"], [])
        self.assertIn("One stream, so one candidate and no seam to test", seams.report(found))

    def test_two_contexts_already_found_are_shown_with_their_crossing(self) -> None:
        """The booking fixture is two contexts on two streams; the crossing is the one event between them."""
        found = seams.seams(yaml.safe_load(BOOKING.read_text(encoding="utf-8")))
        self.assertEqual([item["stream"] for item in found["candidates"]], ["booking", "table"])
        self.assertEqual(found["crossings"], [{"from": "booking", "to": "table", "events": ["BookingHeld"]}])

    def test_an_empty_model_has_nothing_to_group(self) -> None:
        self.assertIn("nothing to group", seams.report(seams.seams({"slices": []})))


class StreamInOneContextGateTest(unittest.TestCase):
    """`check-model` holds the seam tests' one hard rule: a stream sits in one context."""

    def test_a_stream_written_from_two_contexts_is_refused(self) -> None:
        model = yaml.safe_load(ONE_STREAM)
        model["slices"][1]["context"] = "ticking"
        findings = check.one_stream_one_context(model["slices"])
        self.assertEqual(len(findings), 1)
        self.assertIn("stream list is written from 2 contexts", findings[0])
        self.assertIn("todo: TD-01", findings[0])
        self.assertIn("ticking: TD-02", findings[0])

    def test_one_context_per_stream_passes_and_so_does_game_finder(self) -> None:
        self.assertEqual(check.one_stream_one_context(yaml.safe_load(ONE_STREAM)["slices"]), [])
        model = yaml.safe_load(GAME_FINDER.read_text(encoding="utf-8"))
        self.assertEqual(check.one_stream_one_context(model["slices"]), [])

    def test_the_gate_runs_it(self) -> None:
        model = yaml.safe_load(ONE_STREAM)
        model["slices"][1]["context"] = "ticking"
        self.assertTrue(any("written from 2 contexts" in finding for finding in check.validate(model)))


class BothProfilesAskTheSameQuestionTest(unittest.TestCase):
    """The three tests are named, in the same words, everywhere the decision is taken."""

    def pages(self) -> dict[str, str]:
        return {
            "nine-steps": flat(NINE_STEPS.read_text(encoding="utf-8")),
            "event-modeling skill": flat(EVENT_SKILL.read_text(encoding="utf-8")),
            "global-event-model skill": flat(MODEL_SKILL.read_text(encoding="utf-8")),
            "chart": flat(CHART.read_text(encoding="utf-8")),
            "bounded-contexts": flat(CONTEXTS.read_text(encoding="utf-8")),
            "sail (event)": flat(commands.sail_command(event=True, apps=[], target="none")),
            "sail (standard)": flat(commands.sail_command(event=False, apps=[], target="none")),
        }

    def test_a_shared_noun_is_evidence_for_neither_side_on_both_profiles(self) -> None:
        for name, text in self.pages().items():
            with self.subTest(page=name):
                self.assertIn("shared noun is evidence for neither side", text)

    def test_the_three_tests_are_named_where_the_decision_is_worked_out(self) -> None:
        for name in ("nine-steps", "chart", "bounded-contexts"):
            text = self.pages()[name]
            with self.subTest(page=name):
                for test in ("**Language", "**Change", "**Flow"):
                    self.assertIn(test, text)
                self.assertIn("never split", text)

    def test_the_rule_is_in_the_markdown_and_the_ladder_points_at_it(self) -> None:
        """Large text lives in the skill and the command; `sail.md` sends a reader there."""
        event = self.pages()["sail (event)"]
        standard = self.pages()["sail (standard)"]
        self.assertIn("make seams", event)
        self.assertIn("*Apply Conway's Law*", event)
        self.assertIn("*The Seam Tests*", standard)
        self.assertIn("*The Seam Tests*", self.pages()["chart"])
        self.assertIn("*The Seam Tests*", self.pages()["nine-steps"])

    def test_one_vocabulary_is_no_longer_the_whole_decision(self) -> None:
        for name, text in self.pages().items():
            with self.subTest(page=name):
                self.assertNotIn("say so and move on", text)
                self.assertNotIn("saying so is the whole decision", text)
                self.assertNotIn("One vocabulary is one context", text)

    def test_the_seams_target_ships_on_the_event_profile(self) -> None:
        from slipwai.project.model_targets import model_targets
        self.assertIn("seams:", model_targets(event=True))
        self.assertIn("scripts/event-model/seams.py", model_targets(event=True))
        self.assertEqual(model_targets(event=False), "")
