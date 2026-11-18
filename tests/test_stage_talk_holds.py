"""What a person says to a stage is kept, said, and holds the board — through a Stop, a restart, a verdict given
too early, and a later stage that failed. Through the running board, with the stand-in agent.

Each test is one way the first build of this let a person's word be lost or overruled: an Approve pressed while
a message waited, which the message's own turn then made stale and the board approved again over; a Stop that
started the waiting message at once; a restart that left a message shown as queued for good; a conversation
with the storyboard that erased the model's failure.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from unittest import mock

import checkout_packages  # noqa: F401
from test_stage_talk import FEATURE, STAND_IN, Talking, until

from slipwai import stage_session, stage_talk
from slipwai.bridge import serve
from slipwai.drawn import record_verdict
from slipwai.init_run import Fitting, Step
from slipwai.upstream import APPROVED_BY


class HoldsTest(Talking):
    def test_approve_is_refused_while_a_message_waits_and_a_changed_page_is_never_approved_over(self) -> None:
        self.advance_on()
        self.pages()
        fitting = self.drawing("dawdle")
        until(lambda: (self.root / ".dawdling").exists())
        self.assertEqual(self.post("/stage/say", {"command": "mockups", "message": "repaint it blue"}),
                         (200, "queued"))
        status, said = self.post("/storyboard", {"feature": FEATURE, "verdict": "approved"})
        self.assertEqual(status, 400)
        self.assertIn("has not been said to it yet", said)
        self.assertFalse((self.mockups / "mock-states.md").exists(), "no verdict on pages about to change")
        (self.root / ".go").write_text("", encoding="utf-8")
        until(lambda: "Drawn: repaint it blue" in fitting.said()["lines"])
        self.ended(fitting)
        record_verdict(self.root, FEATURE, "approved")  # the person's verdict, on what they now see
        stage_talk.release(self.root)
        self.post("/stage/say", {"command": "mockups", "message": "repaint it, larger"})
        self.ended(self.board_fitting())
        self.assertEqual(self.post("/stage/carry-on", {}), (200, "carrying on"))
        live = json.loads(self.get("/live.json")[1])
        verdicts = (self.mockups / "mock-states.md").read_text(encoding="utf-8")
        self.assertFalse(verdicts.startswith(APPROVED_BY), "the board wrote nothing over the withdrawn verdict")
        self.assertIn("<!-- withdrawn: Basket", verdicts)
        self.assertTrue(any("has changed since its verdict" in one["text"] for one in live["waiting"]["holding"]))

    def test_a_delivered_message_holds_the_board_again_whatever_was_said_to_carry_on_before(self) -> None:
        self.advance_on()
        self.pages()
        fitting = self.drawing("dawdle")
        until(lambda: (self.root / ".dawdling").exists())
        self.post("/stage/say", {"command": "mockups", "message": "what is on it?"})
        self.assertEqual(self.post("/stage/carry-on", {})[0], 409, "Carry on waits on it, as Approve does")
        stage_talk.release(self.root)  # however the hold was let go of before the message was said
        self.assertEqual(stage_talk.held(self.root), [])
        (self.root / ".go").write_text("", encoding="utf-8")
        until(lambda: "Drawn: what is on it?" in fitting.said()["lines"])
        self.ended(fitting)
        self.assertEqual(stage_talk.held(self.root), ["mockups"])
        self.get("/live.json")
        self.assertFalse((self.mockups / "mock-states.md").exists())

    def test_stop_starts_nothing_and_what_waited_is_said_only_when_the_person_says_so(self) -> None:
        self.pages()
        fitting = self.drawing("linger")
        until(lambda: (self.root / ".lingering").exists())
        self.post("/stage/say", {"command": "mockups", "message": "make it green"})
        self.assertEqual(self.post("/stage/cancel", {}), (200, "stopped"))
        self.ended(fitting)
        time.sleep(0.5)
        self.assertTrue(fitting.said()["done"], "nothing started by itself after the Stop")
        self.assertNotIn("Drawn: make it green", fitting.said()["lines"])
        talk = self.talk()
        self.assertEqual(talk["queued_ids"], [])
        [stuck] = talk["undelivered"]
        self.assertEqual(stuck["text"], "make it green", "shown as not delivered, with Say it now")
        self.assertEqual(self.post("/stage/say", {"command": "mockups", "message": stuck["text"],
                                                  "resend": stuck["id"]}), (200, "said"))
        self.assertIn("Drawn: make it green", self.ended(fitting)["lines"])
        self.assertEqual(self.talk()["undelivered"], [])

    def test_after_a_restart_a_queued_message_says_it_was_not_delivered_and_can_be_said(self) -> None:
        self.pages()
        self.ended(self.drawing())
        stage_talk.said(self.root, "mockups", "and the tables?", queued=True)  # queued when the app went away
        later = serve(self.root, "127.0.0.1", 0)
        self.addCleanup(later.server_close)
        import threading
        threading.Thread(target=later.serve_forever, daemon=True).start()
        self.addCleanup(later.shutdown)
        self.server, self.port = later, later.server_address[1]
        talk = self.talk()
        self.assertEqual((talk["queued_ids"], [one["text"] for one in talk["undelivered"]]),
                         ([], ["and the tables?"]), "never promised as queued with nothing to say it")
        with mock.patch.object(stage_session, "launchable", return_value=STAND_IN):
            stuck = talk["undelivered"][0]
            self.assertEqual(self.post("/stage/say", {"command": "mockups", "message": stuck["text"],
                                                      "resend": stuck["id"]}), (200, "said"))
            self.assertIn("Drawn: and the tables?", self.ended(self.board_fitting())["lines"])
        self.assertEqual(self.talk()["undelivered"], [])

    def test_talking_to_the_storyboard_after_a_later_stage_failed_keeps_that_failure(self) -> None:
        self.advance_on()
        self.pages()
        self.ended(self.drawing())
        record_verdict(self.root, FEATURE, "approved")
        stage_talk.release(self.root)
        failed = Fitting(self.root, [Step([sys.executable, "-c", "raise SystemExit(3)"], "Modelling.",
                                          lambda code: f"ended {code}", "model")])
        self.server.RequestHandlerClass.bench.outfit(self.root.resolve()).fitting = failed  # type: ignore
        failed.thread.start()
        self.ended(failed)
        with mock.patch.object(stage_session, "launchable", return_value=STAND_IN):
            self.post("/stage/say", {"command": "mockups", "message": "what does the total say?"})
            self.ended(self.board_fitting())
        self.post("/stage/carry-on", {})
        live = json.loads(self.get("/live.json")[1])
        self.assertEqual(self.board_fitting().said()["step"], "", "nothing was launched past the failure")
        self.assertTrue(any(one["text"].startswith("`model` ended short (exit 3) before this conversation")
                            for one in live["waiting"]["holding"]), live["waiting"]["holding"])

    def test_a_stop_during_a_reply_then_carry_on_says_why_nothing_moves(self) -> None:
        self.advance_on()
        self.pages()
        self.ended(self.drawing())
        self.post("/stage/say", {"command": "mockups", "message": "linger here"})
        until(lambda: (self.root / ".lingering").exists())
        self.post("/stage/cancel", {})
        self.ended(self.board_fitting())
        self.post("/stage/carry-on", {})
        self.assertIn("ended short", self.talk()["held"], "Carry on pressed, nothing moves, and the page says why")

    def test_a_name_off_the_address_is_never_a_path_and_an_unignored_run_folder_is_not_written(self) -> None:
        self.assertEqual(json.loads(self.get("/stage/talk.json?command=../../etc")[1])["turns"], [])
        status, said = self.post("/stage/say", {"command": "../x", "message": "hello"})
        self.assertEqual(status, 400)
        self.assertIn("is not a stage of this board", said)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        stage_talk._IGNORED.clear()
        (self.root / ".slipwai/stages/mockups").mkdir(parents=True)
        (self.root / ".slipwai/stages/mockups/session").write_text("s-1\n", encoding="utf-8")
        status, said = self.post("/stage/say", {"command": "mockups", "message": "my private thought"})
        self.assertEqual(status, 400)
        self.assertIn("run `slipwai migrate`", said)
        self.assertFalse((self.root / ".slipwai/stages/mockups/talk.jsonl").exists(), "nothing a commit would carry")
        stage_talk._IGNORED.clear()

    def test_a_torn_last_line_loses_itself_and_not_the_next_turn(self) -> None:
        path = self.root / ".slipwai/stages/mockups/talk.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text('{"role": "person", "kind": "text", "text": "first"}\n{"role": "pers', encoding="utf-8")
        stage_talk.add(self.root, "mockups", {"role": "agent", "kind": "text", "text": "after the tear"})
        self.assertEqual([one["text"] for one in stage_talk.turns(self.root, "mockups")], ["first", "after the tear"])
