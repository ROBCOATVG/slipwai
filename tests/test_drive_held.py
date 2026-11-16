"""A slice's driver held open over the stand-in agent, and the conversation files it is the one writer of.

What is proved: one session takes many prompts; a message waits for the turn under way or interrupts it,
and is answered, or flagged where the agent said nothing; a pause closes the driver with its session saved
and the next one loads it; a withdrawal takes back a message never delivered; an agent that dies leaves
what was queued not delivered; and what the agent does reaches the slice's activity log in the kinds the
board reads.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
from test_drive import AGENT, loaded

from slipwai import activity, talk


def until(what: Callable[[], object], timeout: float = 20.0) -> None:
    ends = time.monotonic() + timeout
    while not what():
        if time.monotonic() > ends:
            raise AssertionError("waited and it did not happen")
        time.sleep(0.05)


class TalkFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = talk.place(Path(tempfile.mkdtemp()), "ORD", "ORD-01")

    def test_a_message_is_written_whole_and_refused_when_it_is_not_one(self) -> None:
        sent = talk.send(self.home, "say", "hello", mode="interrupt")
        self.assertEqual([one["id"] for one in talk.inbox(self.home)], [sent["id"]])
        self.assertEqual(sorted(path.name for path in (self.home / "inbox").iterdir()), [f"{sent['id']}.json"])
        for kind, text, mode in (("shout", "x", "wait"), ("say", " ", "wait"), ("say", "x", "later")):
            with self.assertRaises(ValueError):
                talk.send(self.home, kind, text, mode=mode)
        with self.assertRaises(ValueError):
            talk.place(self.home, "..", "x")

    def test_receipts_are_folded_from_the_inbox_and_the_thread(self) -> None:
        ids = [talk.send(self.home, "say", f"m{n}")["id"] for n in range(5)]
        talk.note(self.home, "delivered", id=ids[1], mode="wait")
        talk.note(self.home, "delivered", id=ids[2], mode="wait")
        talk.note(self.home, "reply", to=ids[2], text="done")
        talk.note(self.home, "failed", id=ids[3], why="the agent ended")
        talk.send(self.home, "withdraw", of=ids[4])
        states = {one["id"]: (one["state"], one["reply"], one["why"]) for one in talk.receipts(self.home)
                  if one["kind"] == "say"}
        self.assertEqual(states, {ids[0]: ("queued", "", ""), ids[1]: ("delivered", "", ""),
                                  ids[2]: ("answered", "done", ""), ids[3]: ("not delivered", "", "the agent ended"),
                                  ids[4]: ("withdrawn", "", "")})
        self.assertEqual([one["id"] for one in talk.queued(self.home)], [ids[0]])


class HeldTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.drive = loaded(self.root)
        self.home = talk.place(self.root / ".slipwai", "ORD", "ORD-01")
        self.activity = self.root / ".slipwai" / "activity" / "ORD" / "ORD-01.jsonl"
        self.drives: list[Any] = []
        self.addCleanup(lambda: [one.end() for one in self.drives])

    def started(self, prompt: str, fresh: bool = False) -> Any:
        env = {**os.environ, "SLIPWAI_FAIRWAY": "ORD", "SLIPWAI_SLICE": "ORD-01", "SLIPWAI_STAGE": "drive"}
        held = self.drive.Drive([sys.executable, str(AGENT)], self.root, env, prompt,
                                kept=self.root / ".slipwai" / "acp" / "ORD-01", conversation=self.home,
                                activity=self.activity, fresh=fresh)
        self.drives.append(held)
        return held

    def kinds(self) -> list[str]:
        return [one["kind"] for one in talk.thread(self.home)]

    def state(self, ident: str) -> dict:
        return next(one for one in talk.receipts(self.home) if one["id"] == ident)

    def said(self) -> list[str]:
        return [one["what"] for one in activity.lines_of(self.root, "ORD", "ORD-01") if one["kind"] == "said"]

    def test_a_second_prompt_reaches_the_same_session(self) -> None:
        held = self.started("count")
        self.assertEqual(held.wait(20), 0)
        first, agent = held.session.session_id, held.pid
        self.assertTrue(held.alive, "a turn's end is not the driver's")
        held.prompt("count")
        self.assertEqual(held.wait(20), 0)
        self.assertEqual((held.session.session_id, held.pid), (first, agent))
        self.assertIn("Drawn: count prompt 2 in s-1", self.said())
        self.assertEqual(self.kinds().count("session"), 1)
        held.end()
        self.assertEqual(talk.saved_session(self.home)["id"], "s-1", "closing saves the session")

    def test_a_wait_mode_message_is_delivered_after_the_turn_and_answered(self) -> None:
        held = self.started("dawdle")
        until(lambda: (self.root / ".dawdling").exists())
        sent = talk.send(self.home, "say", "is the total in euros?")
        until(lambda: "seen" in self.kinds())
        self.assertEqual(self.state(sent["id"])["state"], "queued", "it waits for the turn under way")
        (self.root / ".go").write_text("", encoding="utf-8")
        self.assertEqual(held.wait(20), 0)
        receipt = self.state(sent["id"])
        self.assertEqual((receipt["state"], receipt["reply"]), ("answered", "Reply: is the total in euros?"))
        lines = talk.thread(self.home)
        ended = next(n for n, one in enumerate(lines) if one["kind"] == "turn" and one.get("state") == "ended")
        self.assertLess(ended, self.kinds().index("delivered"), "delivered once the turn had ended")
        self.assertTrue(receipt["delivered"])

    def test_an_interrupt_cancels_the_turn_and_delivers(self) -> None:
        held = self.started("linger")
        until(lambda: (self.root / ".lingering").exists())
        sent = talk.send(self.home, "say", "stop and look at the header", mode="interrupt")
        self.assertEqual(held.wait(20), 0, "a turn cancelled for a message is not a failed run")
        self.assertTrue(held.interrupted)
        self.assertIn({"state": "cancelled", "stop": "cancelled"},
                      [{k: one.get(k) for k in ("state", "stop")} for one in talk.thread(self.home)
                       if one["kind"] == "turn"])
        self.assertEqual(self.state(sent["id"])["state"], "answered")

    def test_a_turn_that_says_nothing_after_a_delivery_is_unaddressed(self) -> None:
        sent = talk.send(self.home, "say", "quiet now")
        held = self.started("hello")
        self.assertEqual(held.wait(20), 0)
        self.assertEqual(self.state(sent["id"])["state"], "unaddressed")

    def test_pause_then_resume_loads_the_saved_session(self) -> None:
        held = self.started("hello")
        held.wait(20)
        talk.send(self.home, "pause", "lunch", by="person")
        until(lambda: held.closed)
        self.assertEqual(held.halted, ("paused", "person", "lunch"))
        self.assertTrue(talk.paused(self.home))
        self.assertEqual(talk.saved_session(self.home)["id"], "s-1")
        talk.send(self.home, "resume")
        again = self.started("hello")
        self.assertEqual(again.wait(20), 0)
        opened = [one for one in talk.thread(self.home) if one["kind"] == "session"]
        self.assertEqual([one["loaded"] for one in opened], [False, True])
        until(lambda: not talk.paused(self.home))

    def test_a_stage_that_reviews_opens_a_fresh_session(self) -> None:
        record = self.root / "benchmark.json"
        record.write_text(json.dumps({"stages": [{"stage": "implement-shipwright"}, {"stage": "review-mate"}]}),
                          encoding="utf-8")
        self.assertTrue(self.drive.reviewing(record))
        talk.save_session(self.home, "s-1")
        held = self.started("hello", fresh=True)
        held.wait(20)
        opened = next(one for one in talk.thread(self.home) if one["kind"] == "session")
        self.assertEqual((opened["loaded"], opened["why"]), (False, "a stage that reviews starts fresh"))

    def test_withdraw_before_delivery(self) -> None:
        sent = talk.send(self.home, "say", "never mind this")
        talk.send(self.home, "withdraw", of=sent["id"])
        held = self.started("hello")
        self.assertEqual(held.wait(20), 0)
        until(lambda: "withdrawn" in self.kinds())
        self.assertNotIn("delivered", self.kinds())
        self.assertEqual(self.state(sent["id"])["state"], "withdrawn")

    def test_the_agent_dying_mid_turn_marks_queued_messages_not_delivered(self) -> None:
        held = self.started("dawdle die")
        until(lambda: (self.root / ".dawdling").exists())
        sent = talk.send(self.home, "say", "are you there?")
        until(lambda: "seen" in self.kinds())
        (self.root / ".go").write_text("", encoding="utf-8")
        self.assertEqual(held.wait(20), 1)
        receipt = self.state(sent["id"])
        self.assertEqual(receipt["state"], "not delivered")
        self.assertIn("the agent", receipt["why"])

    def test_what_the_agent_does_is_written_to_the_activity_log_and_what_it_asks_to_the_thread(self) -> None:
        held = self.started("outside ask plan")
        self.assertEqual(held.wait(20), 0)
        written = activity.lines_of(self.root, "ORD", "ORD-01")
        edits = [one for one in written if one["kind"] == "edit"]
        self.assertTrue(edits and edits[0]["what"].endswith("prototype/index.html"), written)
        self.assertEqual(edits[0]["status"], "completed")
        self.assertIn("failed", [one["kind"] for one in written], "the call refused outside the berth failed")
        self.assertIn("1 of 2 done: Check it", [one["what"] for one in written if one["kind"] == "plan"])
        asks = [one for one in talk.thread(self.home) if one["kind"] in ("ask", "answer")]
        self.assertEqual([(one["kind"], one.get("what")) for one in asks],
                         [("ask", "permission"), ("answer", None), ("ask", "question"), ("answer", None)])
        self.assertTrue(asks[1]["text"].startswith("refused"))


if __name__ == "__main__":
    unittest.main()
