"""Waiting on you as an inbox: a compact row and one button per thing, in sections (`waiting_inbox`)."""
from __future__ import annotations

import html
import json
import re
import unittest

import checkout_packages  # noqa: F401

from slipwai.fleet_record import groups
from slipwai.waiting_inbox import inbox

LANDS = {"what": "base.css: the picker rule", "by": "fleet", "met": "no", "index": 0,
         "check": {"kind": "text", "path": "base.css", "has": ".picker"}}
HANDS = {"what": "free a Docker network pool", "by": "person", "met": "no", "index": 0}


def row(**fields: object) -> dict:
    return {"fairway": "intake", "t": "2026-11-24T09:00:00Z", "slice": "", "what": "", **fields}


def posts(drawn: str, face: str) -> list:
    """The calls the button with this face posts."""
    found = re.search(r"data-w-post='([^']*)'>" + re.escape(face) + "<", drawn)
    assert found, face
    return json.loads(html.unescape(found.group(1)))


class InboxTest(unittest.TestCase):
    def setUp(self) -> None:
        rows = [row(kind="question", slice="chart", id="D495", what="Which contexts does 003 touch (D495)? Taken."),
                row(kind="told", slice="S53", t="2026-11-24T09:01:00Z", what="S53 hands back the picker rule",
                    needs=[LANDS]),
                row(kind="told", slice="S58", t="2026-11-24T09:02:00Z", what="S58 cannot seed", needs=[HANDS]),
                row(kind="told", slice="S61", t="2026-11-24T09:03:00Z", what="S61 lint", needs=[{**HANDS}],
                    probably="yes"),
                row(kind="parked", t="2026-11-18T13:51:39Z", what="name the next lane", obsolete="1.5.1 → 2.1.0"),
                row(kind="decisions", blocking="yes",
                    decisions=[{"t": "2026-11-24T08:00:00Z", "id": "D1", "what": "one"},
                               {"t": "2026-11-24T08:01:00Z", "id": "D2", "what": "two"}]),
                row(kind="told", t="2026-11-24T09:04:00Z", what="For the host: S12 is demoable.")]
        self.drawn = inbox({"inbox": rows, "groups": groups(rows), "streams": {}})

    def test_the_sections_come_in_the_order_attention_goes_with_their_counts(self) -> None:
        order = [self.drawn.index(f'id="w-{key}"') for key in ("judgement", "harness", "hands", "tidy")]
        self.assertEqual(order, sorted(order))
        self.assertIn("<b>2</b> need you", self.drawn, "the question and the thing on this machine")
        self.assertIn("<b>1</b> the harness can do", self.drawn)
        self.assertIn("<b>4</b> to tidy", self.drawn)

    def test_a_chart_question_is_kept_in_one_press_and_its_title_is_the_question(self) -> None:
        self.assertEqual(posts(self.drawn, "Keep the recommendation"), [["/keep", {"fairway": "intake", "id": "D495"}]])
        self.assertIn("<b>Which contexts does 003 touch (D495)?</b>", self.drawn)

    def test_a_hand_back_the_mender_can_land_is_landed_or_marked_done(self) -> None:
        self.assertEqual(posts(self.drawn, "Land it"),
                         [["/mend-again", {"fairway": "intake", "parked": "2026-11-24T09:01:00Z"}]])
        self.assertIn(["/need", {"fairway": "intake", "parked": "2026-11-24T09:01:00Z", "need": 0}],
                      posts(self.drawn, "Mark done"))
        self.assertIn('data-w-bulk="w-tidy"', self.drawn, "a section of several is cleared in one press")

    def test_tidying_confirms_dismisses_and_reads(self) -> None:
        self.assertEqual(posts(self.drawn, "Confirm it landed")[0][0], "/need")
        self.assertEqual(posts(self.drawn, "Dismiss"), [["/dismiss", {"fairway": "intake",
                                                                     "told": "2026-11-18T13:51:39Z"}]])
        self.assertEqual(posts(self.drawn, "Mark all read"),
                         [["/read", {"fairway": "intake",
                                     "decisions": ["2026-11-24T08:00:00Z", "2026-11-24T08:01:00Z"]}]])
        self.assertEqual(posts(self.drawn, "Raise the limit to 2"), [["/set", {"pairs": ["decision_ceiling=2"]}]])
        self.assertEqual(posts(self.drawn, "Done"),
                         [["/dismiss", {"fairway": "intake", "told": "2026-11-24T09:04:00Z"}]])

    def test_a_question_is_answered_from_a_box_in_its_own_row(self) -> None:
        """manda: Answer opened the row's Details, whose question was folded again, and nothing showed."""
        rows = [row(kind="question", slice="S102", aim="S102", id="S102-decide-1", key="question:S102-decide-1",
                    what="Add idempotencyKey to three events? The story seeds one holder meanwhile.")]
        drawn = inbox({"inbox": rows, "groups": [], "streams": {}})
        top = drawn.split("<details>")[0]
        self.assertIn('data-tell="intake"', top, "the box is in the row, not behind Details")
        self.assertIn('data-question="S102-decide-1" data-slice="S102" data-of="question:S102-decide-1"', top)
        self.assertNotIn("data-w-open", top)

    def test_every_row_keeps_its_card_under_details(self) -> None:
        self.assertEqual(self.drawn.count('class="w-row"'), self.drawn.count("<summary>Details</summary>"))

    def test_nothing_waiting_says_so(self) -> None:
        self.assertIn("Nothing is waiting on you.", inbox({"inbox": [], "groups": []}))


if __name__ == "__main__":
    unittest.main()
