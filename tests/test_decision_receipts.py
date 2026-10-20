"""A decision a person has read can be marked read from the board, and one a person took is never owed.

hr-test-2 parked over its decision ceiling with fourteen decisions the skipper took and five `decide for me`
answers its owner had typed, and the board could show every one of them and take none of them off: the
`read` receipt the ceiling counts could only be written by hand in a terminal.
"""
from __future__ import annotations

from dataclasses import replace

import checkout_packages  # noqa: F401
from board_fixture import BoardTest, Fixture

from slipwai import logs
from slipwai.deck import mark_read


def decided(ident: str, at: str, by: str = "") -> logs.Entry:
    made = logs.entry("decision", fairway="ORD", id=ident, what=f"answer to {ident}")
    return replace(made, t=at, fields={**made.fields, "decided_by": by} if by else made.fields)


class ReceiptTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.deck("ORD", decided("D28", "2026-10-19T10:00:00Z"), decided("D29", "2026-10-19T10:01:00Z"),
                  decided("L01-Q1", "2026-10-19T10:02:00Z", by="human"))

    def test_only_the_decisions_nobody_has_read_are_waiting_and_a_person_s_own_is_not_one(self) -> None:
        said = self.rendered()
        waiting = said[said.index("Waiting on you"):said.index("Streams")]
        self.assertIn("2 decision(s) nobody has read yet", waiting)
        self.assertIn("D28", waiting)
        self.assertNotIn("L01-Q1", waiting)
        self.assertIn('data-read="ORD" data-stamps="2026-10-19T10:00:00Z"', waiting)
        self.assertIn('data-stamps="2026-10-19T10:00:00Z,2026-10-19T10:01:00Z"', waiting, "and one for all")

    def test_marking_one_read_writes_the_receipt_the_ceiling_counts(self) -> None:
        self.assertIn("marked 1", mark_read(self.root, "ORD", ["2026-10-19T10:00:00Z"]))
        receipts = [e.fields["told"] for e in self.read("ORD") if e.kind == "read"]
        self.assertEqual(receipts, ["2026-10-19T10:00:00Z"])
        self.assertNotIn("D28", self.rendered().split("Streams")[0].split("Waiting on you")[1])

    def test_an_instant_that_is_no_decision_or_already_read_writes_nothing(self) -> None:
        mark_read(self.root, "ORD", ["2026-10-19T10:00:00Z"])
        with self.assertRaises(ValueError):
            mark_read(self.root, "ORD", ["2026-10-19T10:00:00Z", "1999-01-01T00:00:00Z"])
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "read"]), 1)

    def test_the_page_with_nothing_to_press_shows_them_and_offers_no_button(self) -> None:
        said = self.rendered(controls=False)
        self.assertIn("D29", said)
        self.assertNotIn("data-read", said)


class ReceiptRouteTest(BoardTest):
    def test_pressing_mark_read_on_the_page_writes_the_receipts(self) -> None:
        self.deck("ORD", decided("D30", "2026-10-19T11:00:00Z"), decided("D31", "2026-10-19T11:01:00Z"))
        code, said = self.post("/read", {"fairway": "ORD",
                                         "decisions": ["2026-10-19T11:00:00Z", "2026-10-19T11:01:00Z"]})
        self.assertEqual(code, 200, said)
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "read"]), 2)

    def test_a_body_with_no_list_is_a_refusal_and_not_a_traceback(self) -> None:
        code, _ = self.post("/read", {"fairway": "ORD", "decisions": "D30"})
        self.assertEqual(code, 400)
