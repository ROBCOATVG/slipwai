"""Feedback from the board: what a person said after using the app, where it goes, and what it became.

The record is the state, so most of these write a record, change it the way triage or a person would, and
read back what the board would show and what was handed on: an intake idea, a design note, or a `told` to
the slice's captain that answers no park.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai import feedback, logs
from slipwai.deck import entries
from slipwai.feedback_card import act, card, list_html, payload
from slipwai.fleet import for_someone_else
from slipwai.voyage_page import tabs_html

CHART = """v: 1
feature: ordering
fairways:
  ORD:
    context: ordering
slices:
  L01:
    fairway: ORD
    capability: basket
  L02:
    fairway: BIL
    capability: invoice
"""


class Project(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        path = self.root / logs.deck_path("ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(logs.entry("claimed", fairway="ORD", slice="L01").line(), encoding="utf-8")

    def proposed(self, words: str, route: str, **fields: str) -> feedback.Item:
        """A record as triage leaves it: a route, what it becomes, and its reasons."""
        item = feedback.capture(self.root, words, {"slice": fields.pop("slice", "L01"), "fairway": "ORD"})
        item.fields.update(route=route, about="the closing date", becomes="a fix slice after L01",
                           proposed="2026-10-21T11:06:40Z", **fields)
        item.proposed = "L01's example 4 dates the closure by when it was accepted."
        feedback.write(item)
        return item

    def told(self) -> list[logs.Entry]:
        found, _ = entries(self.root, "ORD", "ordering")
        return [one for one in found if one.kind == "told"]


class CaptureTest(Project):
    def test_a_capture_is_the_next_numbered_file_with_the_context_the_board_knew(self) -> None:
        first = feedback.capture(self.root, "The closing date is before the resignation.",
                                 {"slice": "L01", "trunk": "a863c3c", "secret": "never written"})
        second = feedback.capture(self.root, "Who accepted it?")
        self.assertEqual((first.number, second.number), ("0001", "0002"))
        self.assertEqual(first.path.name, "0001-the-closing-date-is-before-the-resignation.md")
        read = feedback.parse(first.path)
        assert read is not None
        self.assertEqual((read.fields["slice"], read.fields["trunk"], read.fields["by"]), ("L01", "a863c3c", "person"))
        self.assertNotIn("secret", read.fields)
        self.assertEqual(read.said, "The closing date is before the resignation.")
        self.assertEqual(read.state, "triaging")

    def test_nothing_said_or_a_slice_that_is_not_one_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            feedback.capture(self.root, "   ")
        with self.assertRaises(ValueError):
            feedback.capture(self.root, "words", {"slice": "../etc"})
        self.assertEqual(feedback.items(self.root), [])

    def test_a_line_of_context_cannot_add_a_line_to_the_front_matter(self) -> None:
        item = feedback.capture(self.root, "words", {"page": "/records\nroute: defect"})
        read = feedback.parse(item.path)
        assert read is not None
        self.assertNotIn("route", read.fields)
        self.assertEqual(read.state, "triaging")


class ConfirmTest(Project):
    def test_new_scope_becomes_an_intake_idea_from_the_persons_words(self) -> None:
        item = self.proposed("A reminder a week before the final day.", "scope")
        said = feedback.confirm(self.root, item.number, [])
        self.assertIn("docs/intake/a-reminder-a-week-before-the-final-day", said)
        brief = self.root / "docs/intake/a-reminder-a-week-before-the-final-day/brief.md"
        self.assertIn("A reminder a week before the final day.", brief.read_text(encoding="utf-8"))
        self.assertEqual(feedback.find(self.root, item.number).state, "confirmed")

    def test_a_note_goes_under_its_own_heading_in_the_design_page(self) -> None:
        (self.root / "docs").mkdir()
        (self.root / "docs/design.md").write_text("# Design\n\nThe floor.\n", encoding="utf-8")
        feedback.confirm(self.root, self.proposed("Date first.", "note").number, [])
        feedback.confirm(self.root, self.proposed("Bigger buttons.", "note").number, [])
        text = (self.root / "docs/design.md").read_text(encoding="utf-8")
        self.assertEqual(text.count(feedback.DESIGN_HEADING), 1)
        self.assertIn("- Date first. (feedback 0001", text)
        self.assertIn("- Bigger buttons. (feedback 0002", text)
        self.assertTrue(text.startswith("# Design\n\nThe floor."))

    def test_a_defect_is_told_to_the_slices_captain_and_answers_no_park(self) -> None:
        item = self.proposed("Closed before it was resigned.", "defect")
        feedback.confirm(self.root, item.number, [{"slice": "L01", "fairway": "ORD", "state": "done"}])
        [told] = self.told()
        self.assertEqual((told.fields["by"], told.fields["slice"]), ("feedback", "L01"))
        self.assertIn("add a fix slice after it", told.fields["message"])
        self.assertIn("docs/feedback/0001-", told.fields["message"])
        # Addressed to the captain, so it is not a note under Waiting on you, and not a person's, so the
        # harbourmaster clears nothing with it.
        self.assertTrue(for_someone_else(told))
        self.assertEqual(feedback.find(self.root, item.number).fields["became"], "told ORD about L01")

    def test_a_defect_in_a_slice_still_in_flight_is_fixed_before_it_merges(self) -> None:
        item = self.proposed("Closed before it was resigned.", "defect")
        feedback.confirm(self.root, item.number, [{"slice": "L01", "fairway": "ORD", "state": "working"}])
        self.assertIn("fix it in L01 before it merges", self.told()[0].fields["message"])

    def test_a_change_in_flight_says_which_a_person_chose(self) -> None:
        rows = [{"slice": "L01", "fairway": "ORD", "state": "working"}]
        parked = self.proposed("More than ten questions.", "change", **{"in-flight": "L01"})
        held = self.proposed("Fewer questions.", "change", **{"in-flight": "L01"})
        feedback.confirm(self.root, parked.number, rows, hold="park")
        feedback.confirm(self.root, held.number, rows, hold="after-merge")
        first, second = self.told()
        self.assertIn("park L01 at its next boundary", first.fields["message"])
        self.assertIn("leave L01 as it is while it is in flight", second.fields["message"])
        self.assertEqual(feedback.find(self.root, parked.number).fields["hold"], "park")

    def test_a_slice_nobody_has_claimed_is_told_to_the_stream_its_chart_names(self) -> None:
        item = self.proposed("The list is missing.", "planned")
        feedback.confirm(self.root, item.number, [])
        self.assertIn("already planned in L01", self.told()[0].fields["message"])

    def test_a_slice_on_a_stream_with_no_log_yet_is_said_rather_than_lost(self) -> None:
        item = self.proposed("The invoice total.", "defect", slice="L02")
        with self.assertRaises(ValueError) as refused:
            feedback.confirm(self.root, item.number, [])
        self.assertIn("BIL has no log here", str(refused.exception))
        self.assertEqual(feedback.find(self.root, item.number).state, "proposed")

    def test_routing_it_differently_is_recorded_beside_what_triage_proposed(self) -> None:
        item = self.proposed("Who accepted it.", "defect")
        feedback.confirm(self.root, item.number, [], route="note")
        read = feedback.find(self.root, item.number)
        self.assertEqual((read.fields["route"], read.fields["routed"], read.route), ("defect", "note", "note"))

    def test_a_route_about_a_slice_needs_the_slice(self) -> None:
        item = self.proposed("Something.", "scope", slice="")
        with self.assertRaises(ValueError):
            feedback.confirm(self.root, item.number, [], route="defect")

    def test_an_item_is_handed_on_once_and_a_dropped_one_never(self) -> None:
        item = self.proposed("Date first.", "note")
        feedback.confirm(self.root, item.number, [])
        with self.assertRaises(ValueError):
            feedback.confirm(self.root, item.number, [])
        gone = self.proposed("Never mind.", "note")
        feedback.drop(self.root, gone.number)
        with self.assertRaises(ValueError):
            feedback.confirm(self.root, gone.number, [])
        self.assertEqual(feedback.find(self.root, gone.number).state, "dropped")


class CardTest(Project):
    fleet = {"demo_due_in": {"basket": "ORD"}}

    def test_send_writes_the_record_and_starts_reading_it(self) -> None:
        started: list[int] = []

        def start() -> bool:
            started.append(1)
            return True

        said = act(self.root, {"verb": "send", "words": "It broke.", "context": {"slice": "L01"}}, [], {}, start)
        self.assertEqual(said, "feedback 0001 written; reading it now")
        self.assertEqual(started, [1])

    def test_a_board_that_is_busy_keeps_the_record_and_says_how_to_read_it_later(self) -> None:
        said = act(self.root, {"verb": "send", "words": "It broke."}, [], {}, lambda: False)
        self.assertIn("Triage now reads it when the board is free", said)
        self.assertIn("Triage now", list_html(self.root, [], {}, False))

    def test_accept_is_a_persons_verdict_told_to_the_capabilitys_stream(self) -> None:
        act(self.root, {"verb": "accept", "capability": "basket", "fairway": "ORD"}, [], self.fleet, lambda: True)
        [told] = self.told()
        self.assertEqual(told.fields["by"], "person")
        self.assertIn("basket capability: accepted", told.fields["message"])
        with self.assertRaises(ValueError):
            act(self.root, {"verb": "accept", "capability": "invoice", "fairway": "ORD"}, [], self.fleet,
                lambda: True)

    def test_not_yet_is_told_as_the_verdict_and_kept_as_feedback(self) -> None:
        act(self.root, {"verb": "send", "words": "Needs who accepted it.", "verdict": "not-yet",
                        "context": {"capability": "basket", "fairway": "ORD"}}, [], self.fleet, lambda: True)
        [told] = self.told()
        self.assertIn("not accepted yet (behaviour). Needs who accepted it.", told.fields["message"])
        self.assertEqual(feedback.items(self.root)[0].fields["capability"], "basket")

    def test_a_proposal_shows_its_reasons_and_a_change_in_flight_offers_both_holds(self) -> None:
        self.proposed("More than ten.", "change", **{"in-flight": "L01"})
        html = list_html(self.root, [{"slice": "L01", "state": "working"}], self.fleet, False)
        self.assertIn("dates the closure by when it was accepted", html)
        self.assertIn("Confirm and park L01", html)
        self.assertIn("Hold until L01 merges", html)
        self.assertIn("basket</b> · ready for you to see", html)

    def test_what_was_handed_on_is_listed_with_what_it_became(self) -> None:
        (self.root / "docs").mkdir()
        feedback.confirm(self.root, self.proposed("Date first.", "note").number, [])
        html = card(self.root, [], {}, False, "a863c3c0")
        self.assertIn("Every item, and what it turned into", html)
        self.assertIn("docs/design.md", html)
        self.assertIn('id="feedback-box" hidden', html)

    def test_the_poll_says_the_same_line_until_something_changes(self) -> None:
        first = json.loads(payload(self.root, [], {}, False))
        self.assertEqual(first["said"], json.loads(payload(self.root, [], {}, False))["said"])
        feedback.capture(self.root, "It broke.")
        self.assertNotEqual(first["said"], json.loads(payload(self.root, [], {}, True))["said"])


class TabsTest(unittest.TestCase):
    def test_an_empty_band_has_no_tab_and_only_the_first_is_shown(self) -> None:
        html = tabs_html([("work", "Work", "<p>w</p>"), ("model", "Model", ""), ("fleet", "Fleet", "<p>f</p>")])
        self.assertNotIn('data-tab="model"', html)
        self.assertIn('<section class="tab" data-tab="work" role="tabpanel"><p>w</p>', html)
        self.assertIn('<section class="tab" data-tab="fleet" role="tabpanel" hidden>', html)


class TriageScriptTest(unittest.TestCase):
    """The toolkit script finds what nobody has proposed a route for, and starts nothing without one."""

    def load(self, root: Path) -> Any:
        here = Path(__file__).resolve().parents[1] / "assets/toolkit/scripts/agents"
        sys.path.insert(0, str(here))
        try:
            spec = importlib.util.spec_from_file_location("triage_under_test", here / "triage.py")
            assert spec and spec.loader
            module: Any = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(here))
        module.PLACE = root / "docs/feedback"
        return module

    def test_only_records_nobody_has_proposed_dropped_or_confirmed_are_waiting(self) -> None:
        root = Path(tempfile.mkdtemp())
        waiting = feedback.capture(root, "It broke.")
        done = feedback.capture(root, "Date first.")
        done.fields.update(route="note", proposed="2026-10-21T11:06:40Z")
        feedback.write(done)
        gone = feedback.capture(root, "Never mind.")
        feedback.drop(root, gone.number)
        module = self.load(root)
        self.assertEqual([path.name for path in module.waiting()], [waiting.path.name])

    def test_nothing_waiting_starts_no_session(self) -> None:
        module = self.load(Path(tempfile.mkdtemp()))
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.assertEqual(module.main([]), 0)
        self.assertIn("nothing waiting", said.getvalue())


if __name__ == "__main__":
    unittest.main()
