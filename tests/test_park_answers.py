"""What answers a park, and what never does.

A park is a person's to clear. hr-test-2's fairway parked at the decision ceiling on nineteen decisions
nobody had read, and eleven minutes later a slice's *for the host* note cleared it: every `told` counted as
an answer, whoever wrote it, so parks cleared each other and the guardrail held nothing. Now only a
person's `told` answers a park, none does while the decisions stand unread past the ceiling, and the park
the captain writes at the ceiling is cleared by the reading alone.
"""
from __future__ import annotations

import unittest

import captain_fixture
import checkout_packages  # noqa: F401
import harbourmaster_fixture

from slipwai import logs


class HarbourmasterTest(harbourmaster_fixture.Fixture):
    def cleared(self) -> list[str]:
        return sorted(str(entry.fields["parked"]) for entry in self.harbour() if entry.kind == "cleared")

    def test_a_session_s_note_to_the_host_answers_no_park(self) -> None:
        """hr-test-2: a slice's *for the host* note cleared the fairway's decision-ceiling park."""
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="decide", t="2026-10-12T09:00:00Z"),
                  logs.entry("told", fairway="ORD", message="For the host: L03 is green but for two gates",
                             t="2026-10-12T10:00:00Z"),
                  logs.entry("told", fairway="ORD", message="from a session", t="2026-10-12T10:01:00Z",
                             by="session"))
        self.run_once()
        self.assertEqual(self.cleared(), [])

    def test_an_answer_aimed_at_one_slice_clears_its_park_and_no_sibling_s(self) -> None:
        """Three slices parked on three questions are three answers: the box on L07's card is not L09's."""
        self.deck("ordering", "ORD",
                  logs.entry("parked", fairway="ORD", slice="L07", why="Q1?", t="2026-10-12T09:00:00Z"),
                  logs.entry("parked", fairway="ORD", slice="L09", why="Q2?", t="2026-10-12T09:01:00Z"),
                  logs.entry("told", fairway="ORD", slice="L07", message="b", t="2026-10-12T10:00:00Z",
                             by="person"))
        self.run_once()
        self.assertEqual(self.cleared(), ["2026-10-12T09:00:00Z"])

    def over_the_ceiling(self) -> None:
        (self.root / "harbour.json").write_text('{"decision_ceiling": 1}', encoding="utf-8")
        self.deck("ordering", "ORD", logs.entry("decision", fairway="ORD", id="D1", what="a", t="2026-10-12T08:00:00Z"),
                  logs.entry("decision", fairway="ORD", id="D2", what="b", t="2026-10-12T08:01:00Z"))

    def test_past_the_decision_ceiling_a_person_s_go_clears_nothing_until_the_decisions_are_read(self) -> None:
        self.over_the_ceiling()
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="merge", t="2026-10-12T09:00:00Z"),
                  logs.entry("told", fairway="ORD", message="go", t="2026-10-12T10:00:00Z", by="person"))
        self.run_once()
        self.assertEqual(self.cleared(), [], "a message is not a reading")
        self.deck("ordering", "ORD", logs.entry("read", fairway="ORD", told="2026-10-12T08:00:00Z"))
        self.run_once()
        self.assertEqual(self.cleared(), ["2026-10-12T09:00:00Z"], "the answer waited and then counted")

    def test_a_park_at_the_ceiling_is_cleared_by_reading_and_never_by_a_message(self) -> None:
        self.over_the_ceiling()
        at = "2026-10-12T09:00:00Z"
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="2 decisions stand unread", t=at,
                                                waiting="decision-review"))
        self.run_once()
        self.assertEqual(self.cleared(), [])
        (self.root / "harbour.json").write_text('{"decision_ceiling": 5}', encoding="utf-8")
        self.deck("ordering", "ORD", logs.entry("told", fairway="ORD", message="go", t="2026-10-12T10:00:00Z",
                                                by="person"))
        self.run_once()
        receipts = [entry for entry in self.harbour() if entry.kind == "cleared"]
        self.assertEqual([entry.fields["parked"] for entry in receipts], [at])
        self.assertIn("read", str(receipts[0].fields["what"]), "cleared by the ceiling, not by the message")


class CaptainTest(captain_fixture.Fixture):
    def test_a_park_at_the_decision_ceiling_says_it_waits_on_a_reading(self) -> None:
        """So the harbourmaster clears it when the decisions are read, and never on somebody's message."""
        self.budget(minutes=5, decision_ceiling=1)
        self.deck("ORD", logs.entry("decision", fairway="ORD", id="D1", what="a"),
                  logs.entry("decision", fairway="ORD", id="D2", what="b"))
        self.captain("ORD", self.sail(captain_fixture.WORKS))
        parked = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual([e.fields.get("waiting") for e in parked], ["decision-review"], parked)
        self.assertIn("decision_ceiling", str(parked[0].fields["why"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
