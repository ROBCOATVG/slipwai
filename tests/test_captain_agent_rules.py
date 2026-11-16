"""The second review, through the whole captain: what only the program around the helm can hold.

What is proved: a captain that changes the project while it decides has its orders refused, the event closed
by the rule, and its agent turned off for the stream; attempts spent on a slice outlive a stop its captain
ordered, so stopping a slice does not buy it a new set; a message the captain routes to a parked slice never
answers the park; and a person's word to one slice does not answer a park the whole stream wrote about another.
"""
from __future__ import annotations

import json

import checkout_packages  # noqa: F401
from test_captain_agent import AgentBase

from slipwai import logs, talk


class RulesTest(AgentBase):
    def test_a_captain_that_changes_the_project_is_refused_and_turned_off(self) -> None:
        self.granted("ORD-01")
        said = self.turn("tamper")
        self.assertIn("WARNING", said)
        record = self.closed()[0]
        self.assertEqual((record["by"], record["cost"]["ended"]), ("rule", "changed"), said)
        self.assertIn("tampered.txt", record["why"])
        self.assertTrue(all(one["state"] == "refused" for one in self.results()))
        off = json.loads((logs.run_dir(self.root) / "events/ORD/agent-off.json").read_text(encoding="utf-8"))
        self.assertIn("changed the project", off["why"])
        (self.root / "tampered.txt").unlink()
        self.granted("ORD-02")
        said = self.turn("today")
        self.assertIn("turned off for this stream", said, "and it stays off, the stream on its rules")
        self.assertEqual(len(self.closed()), 1, "never woken again")

    def test_a_stop_its_captain_ordered_does_not_give_a_slice_its_attempts_back(self) -> None:
        self.budget(minutes=5, attempts=1)
        self.settings(bound=20)
        (self.root / "no-demo").write_text("", encoding="utf-8")
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t="2026-11-16T09:00:00Z"),
                  logs.entry("stopped", fairway="ORD", slice="ORD-01", by="captain:ORD", t="2026-11-16T09:01:00Z"),
                  logs.entry("stopped", fairway="ORD", slice="ORD-01", by="captain:ORD", t="2026-11-16T09:02:00Z"))
        said = self.turn("today")
        parks = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parks), 1, said)
        self.assertIn("last of 3 run(s)", str(parks[0].fields["why"]), "two spent before, one now: no retry")

    def test_a_message_its_captain_routed_never_answers_a_park(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t="2026-11-16T09:00:00Z"),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="Refund window?",
                             t="2026-11-16T09:01:00Z"),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="ORD-01: awaiting Q1",
                             t="2026-11-16T09:02:00Z"))
        talk.send(talk.place(logs.run_dir(self.root), "ORD", "ORD-01"), "say", "Decision: refunds 90 days",
                  by="captain:ORD", via="captain:ORD", of="x", quote="what do you think?")
        self.turn("today")
        self.assertEqual([e for e in self.read("ORD") if e.kind == "told"], [])

    def test_a_word_to_one_slice_does_not_answer_the_stream_s_park_about_another(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-02", t="2026-11-16T09:00:00Z"),
                  logs.entry("parked", fairway="ORD", why="ORD-02: a host change only a person may make",
                             t="2026-11-16T09:01:00Z"))
        talk.send(talk.place(logs.run_dir(self.root), "ORD", "ORD-01"), "say", "use the blue header")
        self.turn("today")
        self.assertEqual([e for e in self.read("ORD") if e.kind == "told"], [])
        talk.send(talk.place(logs.run_dir(self.root), "ORD", "ORD-02"), "say", "landed it, carry on")
        self.turn("today")
        self.assertEqual([(e.fields.get("slice"), e.fields["message"]) for e in self.read("ORD") if e.kind == "told"],
                         [("ORD-02", "landed it, carry on")])


if __name__ == "__main__":
    import unittest
    unittest.main()
