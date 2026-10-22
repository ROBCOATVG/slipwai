"""The voyage as a timeline, folded from the logs and drawn as a track.

Held to the recap day: three slots of work from 16:43 to 17:40, two refusals, two clears by hand, a park
of the catch-up stream standing from 14:59 to the next morning, and — with the record the later slices
write — pauses with a time on them.
"""
from __future__ import annotations

import unittest
from datetime import UTC, datetime

import checkout_packages  # noqa: F401
from test_recap_day import MORNING, copied, recorded

from slipwai import logs
from slipwai.fleet import fairways, harbour_log
from slipwai.timeline import runs_and_parks, spans
from slipwai.timeline_page import percent, ticks, timeline_card

NOW = MORNING.strftime("%Y-%m-%dT%H:%M:%SZ")


def folded(root):  # type: ignore[no-untyped-def]
    found, _ = fairways(root, harbour_log(root))
    return spans(found, NOW)


class FoldTest(unittest.TestCase):
    def test_the_window_runs_from_the_first_line_to_the_hour_after_now(self) -> None:
        data = folded(copied())
        self.assertEqual(data["from"], "2026-10-21T13:00:00Z")
        self.assertEqual(data["to"], "2026-10-22T09:00:00Z")
        self.assertEqual(data["now"], NOW)

    def test_the_library_ran_three_abreast_and_draws_three_slot_lanes(self) -> None:
        lanes = [lane for lane in folded(copied())["lanes"] if lane["fairway"] == "library" and "slot" in lane["name"]]
        self.assertEqual(len(lanes), 3, [lane["name"] for lane in lanes])

    def test_a_slice_claimed_twice_is_two_runs_ending_at_its_parks(self) -> None:
        found, _ = fairways(copied(), harbour_log(copied()))
        library = next(one for one in found if one.name == "library")
        runs, _parks = runs_and_parks(library, NOW)
        lb3 = [(run["from"], run["to"]) for run in runs if run["slice"] == "LB3"]
        self.assertEqual(len(lb3), 3)
        self.assertEqual(lb3[0], ("2026-10-21T13:35:15Z", "2026-10-21T13:58:56Z"))
        self.assertTrue(all(start < end for start, end in lb3))

    def test_the_catch_up_park_stands_from_the_first_refusal_to_now(self) -> None:
        lane = next(lane for lane in folded(copied())["lanes"] if lane["name"] == "catch-up · parked")
        park = lane["spans"][0]
        self.assertEqual((park["kind"], park["from"][:16], park["to"]), ("park", "2026-10-21T13:59", NOW))

    def test_a_person_s_two_clears_are_two_marks_and_the_rule_s_receipts_are_none(self) -> None:
        marks = folded(copied())["marks"]
        self.assertEqual([mark["t"][:16] for mark in marks if mark["kind"] == "person"],
                         ["2026-10-21T14:51", "2026-10-21T15:43"])
        self.assertEqual([mark["t"] for mark in marks if mark["kind"] == "now"], [NOW])
        self.assertEqual([mark for mark in marks if mark["kind"] == "limit"], [])

    def test_with_the_record_the_refusals_are_marks_and_the_parks_are_pauses_in_their_lanes(self) -> None:
        data = folded(recorded())
        limits = [mark["t"][:16] for mark in data["marks"] if mark["kind"] == "limit"]
        self.assertIn("2026-10-21T13:58", limits)
        self.assertIn("2026-10-21T16:40", limits)
        slots = [lane for lane in data["lanes"] if lane["fairway"] == "library" and "slot" in lane["name"]]
        pauses = [span for lane in slots for span in lane["spans"] if span["kind"] == "pause"]
        self.assertTrue(pauses)
        evening = [span for span in pauses if span["from"] > "2026-10-21T16:00"]
        self.assertTrue(all(span["to"] >= "2026-10-21T20:40:00Z" for span in evening))
        parked = next(lane for lane in data["lanes"] if lane["name"] == "library · parked")
        # The three on the host change, and the stream's own parks from the first afternoon, which name no slice.
        self.assertEqual(sorted({span["slice"] for span in parked["spans"] if span["slice"]}), ["LB6", "LB7", "LB8"])

    def test_an_open_pause_ahead_of_now_is_a_reset_mark(self) -> None:
        at = datetime(2026, 10, 21, 17, 5, tzinfo=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        found, _ = fairways(recorded(), harbour_log(recorded()))
        data = spans(found, at)
        self.assertEqual([mark["t"] for mark in data["marks"] if mark["kind"] == "reset"], ["2026-10-21T20:40:00Z"])

    def test_a_run_with_no_end_trails_the_last_line_naming_it_and_never_reaches_now(self) -> None:
        class Stream:
            name = "ORD"
            entries = [logs.Entry("claimed", {"fairway": "ORD", "slice": "ORD-01"}, t="2026-10-21T10:00:00Z"),
                       logs.Entry("heartbeat", {"fairway": "ORD", "slice": "ORD-01"}, t="2026-10-21T10:20:00Z")]
            receipts: list[logs.Entry] = []

        runs, _ = runs_and_parks(Stream(), "2026-10-21T12:00:00Z")
        self.assertEqual(runs[0]["to"], "2026-10-21T10:35:00Z")


class CardTest(unittest.TestCase):
    def test_positions_are_percentages_of_the_window(self) -> None:
        self.assertAlmostEqual(percent("2026-10-21T14:00:00Z", "2026-10-21T13:00:00Z", "2026-10-21T15:00:00Z"), 50.0)
        drawn = ticks("2026-10-21T13:00:00Z", "2026-10-21T15:00:00Z")
        self.assertEqual(drawn.count("tl-tick"), 3)
        self.assertIn('style="left:50.000%"', drawn)

    def test_the_card_draws_the_lanes_the_marks_and_the_dropdown_and_the_published_copy_has_no_dropdown(self) -> None:
        from slipwai.fleet import board

        found = board(recorded(), {"boilers": 3}, now=MORNING)
        said = timeline_card(found, controls=True)
        self.assertIn('id="timeline"', said)
        self.assertIn("library · slot 1", said)
        self.assertIn("library · parked", said)
        self.assertIn('class="tl-mark limit"', said)
        self.assertIn('class="tl-mark now"', said)
        self.assertIn('id="tl-scale"', said)
        self.assertIn("The whole voyage", said)
        still = timeline_card(found, controls=False)
        self.assertNotIn("<select", still)
        self.assertIn('class="tl-bar pause"', still)


if __name__ == "__main__":
    unittest.main()
