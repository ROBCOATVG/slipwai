"""The captain with a slice's driver held open, and what is said to a slice reaching it.

Over the stand-in agent (`SLIPWAI_ACP`): a turn cancelled for a person's message costs no attempt; a stop
ends the session now, writes `stopped` naming who and why and leaves the berth as it was; a pause lets the
turn finish and gives the slot back, and a resume carries the slice on in its saved session. In print mode
(`SLIPWAI_SAIL`): a message waits for the slice's next dispatch and goes into its prompt, and one to a slice
parked on a question is the person's answer to the park.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import checkout_packages  # noqa: F401
from captain_fixture import WORKS, Fixture
from test_drive import STAND_IN

from slipwai import logs, talk


def until(what: Callable[[], object], timeout: float = 60.0) -> None:
    ends = time.monotonic() + timeout
    while not what():
        if time.monotonic() > ends:
            raise AssertionError("waited and it did not happen")
        time.sleep(0.1)


class HeldCaptainTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.home = talk.place(self.root / ".slipwai", "ORD", "ORD-01")

    def over(self) -> subprocess.Popen:
        env = {key: value for key, value in os.environ.items() if key != "SLIPWAI_SAIL"}
        captain = subprocess.Popen([sys.executable, str(self.script), "ORD", "--once"], cwd=self.root, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env={**env, "SLIPWAI_ACP": STAND_IN})
        self.addCleanup(captain.kill)
        return captain

    def finished(self, captain: subprocess.Popen) -> str:
        said, _ = captain.communicate(timeout=120)
        self.assertEqual(captain.returncode, 0, said)
        return said

    def kinds(self) -> list[str]:
        return [e.kind for e in self.read("ORD")]

    def test_a_cancelled_turn_is_not_counted_as_a_failed_attempt(self) -> None:
        self.budget(minutes=5, attempts=0)  # one run and no retry: a counted cancel would park
        self.grant("ORD-01")
        (self.root / ".linger").write_text("", encoding="utf-8")
        captain = self.over()
        until(lambda: (self.root / ".lingering").exists())
        sent = talk.send(self.home, "say", "use the blue header", mode="interrupt")
        said = self.finished(captain)
        self.assertIn("ORD-01 is through its gate and merged", said)
        self.assertNotIn("parked", self.kinds(), said)
        self.assertIn("no attempt spent", said)
        receipt = next(one for one in talk.receipts(self.home) if one["id"] == sent["id"])
        self.assertEqual((receipt["state"], receipt["reply"]), ("answered", "Reply: use the blue header"))
        opened = [one for one in talk.thread(self.home) if one["kind"] == "session"]
        self.assertEqual(len(opened), 1, "the retry was the next prompt into the same session")

    def test_stop_writes_stopped_and_leaves_the_berth(self) -> None:
        self.grant("ORD-01")
        (self.root / ".linger").write_text("", encoding="utf-8")
        captain = self.over()
        until(lambda: (self.root / ".lingering").exists())
        (self.root / "half-done.txt").write_text("uncommitted", encoding="utf-8")
        talk.send(self.home, "stop", "wrong approach")
        said = self.finished(captain)
        stops = [e for e in self.read("ORD") if e.kind == "stopped"]
        self.assertEqual([(e.fields["slice"], e.fields.get("by"), e.fields.get("why")) for e in stops],
                         [("ORD-01", "person", "wrong approach")], said)
        self.assertNotIn("parked", self.kinds())
        self.assertNotIn("merged", self.kinds())
        self.assertEqual(self.kinds().count("claimed"), 1, "not started again by the turn that stopped it")
        self.assertEqual((self.root / "half-done.txt").read_text(encoding="utf-8"), "uncommitted")
        self.assertIn("stopped", [one["kind"] for one in talk.thread(self.home)])
        self.assertEqual(talk.saved_session(self.home)["id"], "s-1")

    def test_a_paused_slice_gives_its_slot_back_and_resumes_on_its_saved_session(self) -> None:
        self.grant("ORD-01")
        (self.root / ".dawdle").write_text("", encoding="utf-8")
        captain = self.over()
        until(lambda: (self.root / ".dawdling").exists())
        talk.send(self.home, "pause", "lunch")
        until(lambda: "seen" in [one["kind"] for one in talk.thread(self.home)])
        (self.root / ".go").write_text("", encoding="utf-8")
        said = self.finished(captain)
        self.assertEqual([e.fields.get("paused") for e in self.read("ORD") if e.kind == "stopped"], [True], said)
        # What `abreast.live` reads a slice's session slot off: its newest claim, merge, stop or park.
        ends = [e.kind for e in self.read("ORD") if e.kind in ("claimed", "merged", "stopped", "parked")]
        self.assertEqual(ends[-1], "stopped", "a paused slice holds no session")
        self.assertNotIn("merged", self.kinds())
        self.assertTrue(talk.paused(self.home))
        talk.send(self.home, "resume")
        said = self.finished(self.over())
        self.assertIn("ORD-01 is through its gate and merged", said)
        opened = [one["loaded"] for one in talk.thread(self.home) if one["kind"] == "session"]
        self.assertEqual(opened, [False, True], "carried on in the session it closed with")


class PrintModeTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.run_dir = self.root / ".slipwai"
        told = ('import os, pathlib\npathlib.Path("told.txt").write_text(os.environ.get("SLIPWAI_MESSAGES", ""), '
                'encoding="utf-8")\n')
        self.fake = self.sail(told + WORKS)

    def receipt(self, slice_id: str, ident: str) -> dict:
        home = talk.place(self.run_dir, "ORD", slice_id)
        return next(one for one in talk.receipts(home) if one["id"] == ident)

    def test_print_mode_delivers_at_the_next_dispatch(self) -> None:
        sent = talk.send(talk.place(self.run_dir, "ORD", "ORD-01"), "say", "mind the rounding", mode="interrupt")
        self.grant("ORD-01")
        done = self.captain("ORD", self.fake)
        self.assertIn("ORD-01 is through its gate and merged", done.stdout, done.stderr)
        self.assertIn("from person: mind the rounding", (self.root / "told.txt").read_text(encoding="utf-8"))
        self.assertEqual(self.receipt("ORD-01", sent["id"])["state"], "delivered")

    def test_a_message_to_a_closed_driver_stays_queued_and_a_say_to_a_parked_slice_answers_the_park(self) -> None:
        parked_at = "2026-11-16T09:02:00Z"
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t="2026-11-16T09:00:00Z"),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="Which currency?",
                             t="2026-11-16T09:01:00Z"),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="ORD-01: awaiting Q1", t=parked_at))
        later = talk.send(talk.place(self.run_dir, "ORD", "ORD-02"), "say", "for when you start")
        answer = talk.send(talk.place(self.run_dir, "ORD", "ORD-01"), "say", "euros")
        done = self.captain("ORD", self.fake)
        told = [e for e in self.read("ORD") if e.kind == "told"]
        self.assertEqual([(e.fields["message"], e.fields.get("by"), e.fields.get("slice"), e.fields.get("inbox"))
                          for e in told], [("euros", "person", "ORD-01", answer["id"])], done.stdout)
        self.assertNotIn("merged", [e.kind for e in self.read("ORD")], "nothing ran while ORD-01 was parked")
        self.assertEqual(self.receipt("ORD-02", later["id"])["state"], "queued", "a closed driver's stays queued")
        self.assertEqual(self.receipt("ORD-01", answer["id"])["state"], "queued")
        # The harbourmaster's part, as it does it on a person's `told` after a park: the receipt carrying it.
        self.harbour(logs.entry("cleared", harbour=True, fairway="ORD", parked=parked_at, what="euros"))
        self.grant("ORD-01")
        done = self.captain("ORD", self.fake)
        self.assertIn("ORD-01 is through its gate and merged", done.stdout, done.stderr)
        decided = [e for e in self.read("ORD") if e.kind == "decision"]
        self.assertEqual([(e.fields["id"], e.fields["what"], e.fields.get("decided_by")) for e in decided],
                         [("Q1", "euros", "human")])
        self.assertEqual(self.receipt("ORD-01", answer["id"])["state"], "delivered", "delivered as its answer")
        self.assertIn("from person: euros", Path(self.root / "told.txt").read_text(encoding="utf-8"))
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "told"]), 1, "told once")


if __name__ == "__main__":
    import unittest
    unittest.main()
