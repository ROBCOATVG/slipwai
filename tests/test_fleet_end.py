"""The board at the two ends of a run: a stream with nothing left in it, and a log nobody can fold.

Split from `test_fleet.py` at its budget. recap's run showed both: every slice merged under a headline that
said a stream had stalled, and a library row that said nothing waited while its park was the unreadable line.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from test_fleet import Fixture, when

from slipwai import logs
from slipwai.bridge_page import live_cards
from slipwai.bridge_page import live_sub as fleet_sub
from slipwai.fleet_page import headline


class EndTest(Fixture):
    def test_a_fairway_with_everything_merged_is_finished_whatever_was_written_after(self) -> None:
        """recap's catch-up took a person's read receipts after its last merge, and its row said stalled."""
        self.deck("ORD",
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(700)),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc123", t=when(600)),
                  logs.entry("read", fairway="ORD", told="2026-10-01T00:00:00Z", t=when(500)))
        found = self.board()
        self.assertEqual(found["berths"][0]["state"], "finished")
        self.assertTrue(headline(found)[1].startswith("Built: every stream has merged what it claimed"))
        self.assertTrue(fleet_sub(found).startswith("built"))

    def test_merged_is_not_built_while_a_whole_capability_is_owed_its_gates(self) -> None:
        """recap's board said Built over eight capabilities none of which had been through its gates."""
        self.deck("ORD",
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(700)),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc123", t=when(600)))
        found = {**self.board(), "gates_owed": ["take-orders"]}
        colour, sentence, under = headline(found)
        self.assertEqual(colour, "brass")
        self.assertEqual(sentence, "Merged, not yet gated: 1 capability owed its gates — take-orders.")
        self.assertIn("/sail", under)
        found["gates_owed"] = ["take-orders", "bill-orders"]
        self.assertEqual(headline(found)[1],
                         "Merged, not yet gated: 2 capabilities owed their gates — take-orders, bill-orders.")

    def test_a_merge_with_a_sibling_still_claimed_is_not_finished(self) -> None:
        self.deck("ORD",
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(700)),
                  logs.entry("claimed", fairway="ORD", slice="ORD-02", t=when(690)),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc123", t=when(600)))
        self.assertEqual(self.board()["berths"][0]["state"], "stalled")

    def test_a_log_that_cannot_be_read_is_waiting_on_you_with_its_line(self) -> None:
        """recap's library row said nothing waited while the park it waited on was the unreadable line."""
        path = logs.deck_path(self.root, "ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(logs.entry("heartbeat", fairway="ORD").line() + "not json\n", encoding="utf-8")
        found = self.board()
        rows = [row for row in found["inbox"] if row["kind"] == "unreadable"]
        self.assertEqual([row["fairway"] for row in rows], ["ORD"])
        self.assertIn("line 2", rows[0]["what"])
        self.assertIn("1 waiting on you", fleet_sub(found))
        page = live_cards(found, {})
        self.assertIn("Repair a log", page)
        self.assertNotIn('placeholder="Answer ORD', page)



if __name__ == "__main__":
    unittest.main()
