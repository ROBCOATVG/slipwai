"""The captain with a slice's driver held open, and what is said to a slice reaching it.

Over the stand-in agent (`SLIPWAI_ACP`): a turn cancelled for a person's message costs no attempt; a
person's stop holds the slice across the captain's turns until a person resumes it, which starts a fresh
session; a pause lets the turn finish and gives the slot back, and a resume carries the slice on in its
saved session; a message turn that hangs is held to the stage bound and parks the slice as silence does.
In print mode (`SLIPWAI_SAIL`): a message waits for the slice's next dispatch and goes into its prompt, and
stays queued where no session started; one sent to a slice after its park is the person's answer to it,
and one sent before is not.
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

    def over(self, *argv: str) -> subprocess.Popen:
        env = {key: value for key, value in os.environ.items() if key != "SLIPWAI_SAIL"}
        captain = subprocess.Popen([sys.executable, str(self.script), "ORD", *(argv or ("--once",))], cwd=self.root,
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env={**env, "SLIPWAI_ACP": STAND_IN})
        self.addCleanup(captain.kill)
        return captain

    def finished(self, captain: subprocess.Popen, timeout: float = 150, why: str = "") -> str:
        try:
            said, _ = captain.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            captain.kill()
            said, _ = captain.communicate()
            self.fail(f"the captain did not end within {timeout:.0f}s{': ' + why if why else ''}\n{said[-3000:]}")
        self.assertEqual(captain.returncode, 0, said)
        return said

    def kinds(self) -> list[str]:
        return [e.kind for e in self.read("ORD")]

    def lines(self) -> list[str]:
        return [one["kind"] for one in talk.thread(self.home)]

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
        self.assertEqual(self.lines().count("session"), 1, "the retry was the next prompt into the same session")

    def test_a_person_s_stop_holds_the_slice_across_turns_until_they_resume_it(self) -> None:
        self.grant("ORD-01")
        (self.root / ".linger").write_text("", encoding="utf-8")
        captain = self.over("--interval", "1")  # the loop, which used to claim a stopped slice back at once
        until(lambda: (self.root / ".lingering").exists())
        (self.root / "half-done.txt").write_text("uncommitted", encoding="utf-8")
        talk.send(self.home, "stop", "wrong approach")
        # A captain that claims a person's stopped slice back goes round for ever: said at once, as that.
        ends = time.monotonic() + 120
        while captain.poll() is None and time.monotonic() < ends:
            self.assertLessEqual(self.kinds().count("claimed"), 1, "the slice was claimed back after a person's stop")
            time.sleep(0.2)
        said = self.finished(captain, 5, "it kept the slice going after a person's stop")
        stops = [e for e in self.read("ORD") if e.kind == "stopped"]
        self.assertEqual([(e.fields["slice"], e.fields.get("by"), e.fields.get("why")) for e in stops],
                         [("ORD-01", "person", "wrong approach")], said)
        self.assertEqual(self.kinds().count("claimed"), 1, said)
        self.assertNotIn("merged", self.kinds())
        self.assertIn("ORD-01 is stopped by a person until they resume it", said)
        self.assertEqual((self.root / "half-done.txt").read_text(encoding="utf-8"), "uncommitted")
        self.assertEqual(talk.saved_session(self.home), {}, "a stop ends the session")
        said = self.finished(self.over())  # a captain started again holds it too
        self.assertEqual(self.kinds().count("claimed"), 1, said)
        talk.send(self.home, "resume")
        said = self.finished(self.over())
        self.assertIn("ORD-01 is through its gate and merged", said)
        self.assertEqual([one["loaded"] for one in talk.thread(self.home) if one["kind"] == "session"],
                         [False, False], "a resume after a stop starts a fresh session")

    def test_a_paused_slice_gives_its_slot_back_and_resumes_on_its_saved_session(self) -> None:
        self.grant("ORD-01")
        self.grant("ORD-02")  # set ready by the mark ORD-01 sets before it pauses, and merged meanwhile
        (self.root / ".dawdle").write_text("", encoding="utf-8")
        captain = self.over("--interval", "1")
        until(lambda: (self.root / ".dawdling").exists())
        talk.send(self.home, "pause", "lunch")
        until(lambda: "seen" in self.lines())
        (self.root / ".go").write_text("", encoding="utf-8")
        said = self.finished(captain)
        self.assertEqual([e.fields.get("paused") for e in self.read("ORD") if e.kind == "stopped"], [True], said)
        # What `abreast.live` reads a slice's session slot off: its newest claim, merge, stop or park.
        ends = [e.kind for e in self.read("ORD") if e.kind in ("claimed", "merged", "stopped", "parked")
                and e.fields.get("slice") == "ORD-01"]
        self.assertEqual(ends, ["claimed", "stopped"], "a paused slice holds no session, and is not claimed back")
        self.assertTrue(talk.paused(self.home))
        talk.send(self.home, "resume")
        said = self.finished(self.over())
        self.assertIn("ORD-01 is through its gate and merged", said)
        opened = [one["loaded"] for one in talk.thread(self.home) if one["kind"] == "session"]
        self.assertEqual(opened, [False, True], "carried on in the session it closed with")

    def test_a_message_turn_that_hangs_is_held_to_the_stage_bound(self) -> None:
        self.budget(minutes=0.1, attempts=0)  # six seconds of silence ends a stage
        self.grant("ORD-01")
        (self.root / ".dawdle").write_text("", encoding="utf-8")
        captain = self.over()
        started = time.monotonic()
        until(lambda: (self.root / ".dawdling").exists())
        sent = talk.send(self.home, "say", "dawdle on this")  # the stand-in hangs answering it
        until(lambda: "seen" in self.lines())
        (self.root / ".go").write_text("", encoding="utf-8")
        said = self.finished(captain, 60, "a message turn that hangs was not ended at the stage bound")
        self.assertLess(time.monotonic() - started, 90, said)
        receipt = next(one for one in talk.receipts(self.home) if one["id"] == sent["id"])
        self.assertEqual(receipt["state"], "not delivered", said)
        self.assertIn("nothing was written to the deck log", receipt["why"])
        parks = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual([e.fields.get("cause") for e in parks], ["silence"], said)


#: A print-mode session the harness refuses the first time, as a session limit, and runs after; it takes the
#: `--output-format stream-json` its refusal is read by, and hands the fake below it the slice and stream.
REFUSING = """import pathlib, sys
if not pathlib.Path("refused-once").exists():
    pathlib.Path("refused-once").write_text("x", encoding="utf-8")
    print('{"type":"result","subtype":"success","is_error":true,"result":"You have hit your session limit, '
          'resets 9:40pm (Europe/London)"}', flush=True)
    sys.exit(1)
sys.argv[1:] = sys.argv[-2:]
"""


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

    def test_a_message_handed_to_a_session_the_harness_refused_is_returned_and_delivered_next_time(self) -> None:
        path = self.root / "refusing.py"
        path.write_text(REFUSING + (self.root / "fake-sail.py").read_text(encoding="utf-8"), encoding="utf-8")
        sail = f"{sys.executable} {path} --output-format stream-json"
        sent = talk.send(talk.place(self.run_dir, "ORD", "ORD-01"), "say", "mind the rounding")
        done = self.captain("ORD", sail)
        self.assertIn("paused at ORD-01 until", done.stdout, done.stderr)
        home = talk.place(self.run_dir, "ORD", "ORD-01")
        self.assertEqual([one["kind"] for one in talk.thread(home) if one.get("id") == sent["id"]][-1], "returned")
        self.assertEqual(self.receipt("ORD-01", sent["id"])["state"], "queued", "back in the queue")
        park = next(e for e in self.read("ORD") if e.kind == "parked")
        self.harbour(logs.entry("cleared", harbour=True, fairway="ORD", parked=park.t, what="the limit lifted"))
        self.grant("ORD-01")
        done = self.captain("ORD", sail)
        self.assertIn("ORD-01 is through its gate and merged", done.stdout, done.stderr)
        self.assertIn("from person: mind the rounding", (self.root / "told.txt").read_text(encoding="utf-8"))
        self.assertEqual(self.receipt("ORD-01", sent["id"])["state"], "delivered")

    def test_a_message_stays_queued_where_no_session_started(self) -> None:
        sent = talk.send(talk.place(self.run_dir, "ORD", "ORD-01"), "say", "are you there?")
        done = self.captain("ORD", str(self.root / "no-such-harness-here"))
        self.assertIn("parked", done.stdout, done.stderr)
        self.assertEqual(self.receipt("ORD-01", sent["id"])["state"], "queued", done.stdout)

    def test_a_message_sent_before_a_park_is_not_its_answer(self) -> None:
        later = "2099-01-01T09:00:00Z"  # a park written after the message was sent
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t="2026-11-16T09:00:00Z"),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="Which currency?", t=later),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="ORD-01: awaiting Q1", t=later))
        early = talk.send(talk.place(self.run_dir, "ORD", "ORD-01"), "say", "mind the rounding")
        done = self.captain("ORD", self.fake)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "told"], [], done.stdout)
        self.assertEqual(self.receipt("ORD-01", early["id"])["state"], "queued")

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
