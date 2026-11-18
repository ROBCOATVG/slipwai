"""The board advancing by itself presses past only what it saw end well, never the same press twice for
nothing, and never leaves a person without the two things they can do about a word not yet said.

Round four of the storyboard conversation, through the running board with the stand-in agent: a message to the
draft stranded by a Stop is shown with Say it now and Discard on the stage card and under Waiting on you; a
board restarted in the middle of a drawing does not approve what it finds; a drawing that draws nothing ends
short and is not drawn again on every poll; and the counts are read only where a line says them.
"""
from __future__ import annotations

import json
import time
from unittest import mock

import checkout_packages  # noqa: F401
from test_stage_talk import FEATURE, STAND_IN, Talking, until

from slipwai import stage_session, step_record
from slipwai.init_run import Fitting, Step
from slipwai.logs import run_dir
from slipwai.review_reading import DECLARE, declared
from slipwai.stage_session import StageSession


class StrandedTest(Talking):
    def drafting(self) -> Fitting:
        stage = StageSession(self.root, "draft", "linger", launch=STAND_IN)
        fitting = Fitting(self.root, [Step([], "Drafting.", lambda code: f"ended {code}", "draft",
                                           session=stage.run)])
        self.server.RequestHandlerClass.bench.outfit(self.root.resolve(), True).fitting = fitting  # type: ignore
        fitting.thread.start()
        until(lambda: (self.root / ".lingering").exists())
        return fitting

    def test_a_message_to_the_draft_stranded_by_a_stop_has_say_it_now_and_discard_where_it_is_shown(self) -> None:
        self.advance_on()
        fitting = self.drafting()
        self.assertEqual(self.post("/stage/say", {"message": "the members own the boats"}), (200, "queued"))
        status, said = self.post("/stage/carry-on", {})
        self.assertEqual(status, 409)
        self.assertIn("it will be said when this turn ends", said, "queued behind a turn under way, it says so")
        self.post("/stage/cancel", {})
        self.ended(fitting)
        live = json.loads(self.get("/live.json")[1])
        [item] = [one for one in live["waiting"]["holding"] if "not said to it yet" in one["text"]]
        self.assertEqual(item["say"]["command"], "draft", "Waiting on you carries Say it now and Discard for it")
        card = json.loads(self.get("/stage/talk.json?command=")[1])["waiting_all"]
        self.assertEqual([(one["command"], one["text"], one["live"]) for one in card],
                         [("draft", "the members own the boats", False)], "and so does the stage card")
        self.assertIn("say it now, or discard it", self.post("/stage/carry-on", {})[1])
        self.assertEqual(self.post("/stage/say", {"command": "draft", "message": item["say"]["text"],
                                                  "resend": item["say"]["id"]}), (200, "said"))
        self.assertIn("Drawn: the members own the boats", self.ended(self.board_fitting())["lines"])
        self.assertEqual(json.loads(self.get("/stage/talk.json?command=")[1])["waiting_all"], [])


class RecordsTest(Talking):
    def half_drawn(self) -> None:
        """What a board restarted in the middle of a drawing finds: pages so far, a research note begun."""
        (self.mockups / "basket.html").write_text('<title>Basket</title><article class="state"><h2>Empty</h2>'
                                                  "</article>", encoding="utf-8")
        (self.mockups / "research.md").write_text("Blockers open: 0\nQuestions open: 0\n", encoding="utf-8")

    def test_a_drawing_interrupted_by_a_restart_is_not_approved_and_the_board_says_what_to_do(self) -> None:
        self.advance_on()
        self.half_drawn()
        marker = run_dir(self.root) / "surfaces.pid"
        marker.write_text(f"999999\n{time.time():.0f}\n", encoding="utf-8")  # a drawing whose process is gone
        live = json.loads(self.get("/live.json")[1])
        self.assertFalse((self.mockups / "mock-states.md").exists(), "a half-drawn storyboard is not approved")
        [why] = [one["text"] for one in live["waiting"]["holding"] if "interrupted" in one["text"]]
        self.assertIn("draw it again, or look at it and approve or disapprove it yourself", why)

    def test_a_drawing_the_board_has_no_record_of_ending_waits_for_the_person_once(self) -> None:
        self.advance_on()
        self.half_drawn()
        self.get("/live.json")
        self.assertFalse((self.mockups / "mock-states.md").exists())
        self.assertIn("has no record of the drawing", self.talk()["held"])
        step_record.ended(self.root, "surfaces", FEATURE, 0)
        self.get("/live.json")
        self.assertTrue((self.mockups / "mock-states.md").is_file(), "with the record, it goes on as before")

    def test_a_drawing_s_own_end_is_written_down_with_its_feature_and_outcome(self) -> None:
        self.pages()
        (run_dir(self.root) / step_record.ENDED).unlink()  # what `pages` stands in for: here the run writes it
        self.ended(self.drawing())
        seen = step_record.record(self.root, "surfaces")
        assert seen is not None
        self.assertEqual((seen["feature"], seen["code"]), (FEATURE, 0))

    def test_the_drawing_is_told_to_write_pending_until_the_review_is_finished(self) -> None:
        self.assertIn("Blockers open: pending\nQuestions open: pending", DECLARE)
        self.assertNotIn("Blockers open: 0\nQuestions open: 0", DECLARE)
        self.assertEqual(declared("Blockers open: pending\nQuestions open: pending\n"), (None, None))


class NothingDrawnTest(Talking):
    def test_a_drawing_that_draws_nothing_ends_short_and_is_not_drawn_again_on_every_poll(self) -> None:
        self.advance_on()
        with mock.patch.object(stage_session, "launchable", return_value=STAND_IN):
            self.get("/live.json")  # the board draws by itself
            fitting = self.board_fitting()
            said = self.ended(fitting)
            for _ in range(3):
                self.get("/live.json")
                time.sleep(0.2)
        self.assertEqual(said["code"], 1)
        self.assertTrue(any("no surface page under specs/001-boats/mockups/" in line for line in said["lines"]))
        self.assertIs(self.board_fitting(), fitting, "and not drawn again")
        self.assertEqual(sum(line.startswith("Drawing the surfaces") for line in fitting.said()["lines"]), 1)

    def test_the_board_never_presses_the_same_step_for_the_same_feature_twice_with_nothing_changed(self) -> None:
        step_record.pressed(self.root, "draw", FEATURE)
        self.assertTrue(step_record.repeated(self.root, "draw", FEATURE))
        (self.mockups / "basket.html").write_text("<title>Basket</title>", encoding="utf-8")
        self.assertFalse(step_record.repeated(self.root, "draw", FEATURE), "something changed: a person, or a step")


class ReaderTest(Talking):
    def test_a_count_is_a_whole_number_on_a_line_that_begins_with_the_words(self) -> None:
        self.assertEqual(declared("Blockers open: 0.5\nQuestions open: 0\n"), (None, 0))
        self.assertEqual(declared("We keep the blockers open 0 paths in mind.\nBlockers open: 1\nQuestions open: 2\n"),
                         (1, 2))
        self.assertEqual(declared("Notes on the blockers open: 0 of them were hard.\nBlockers open: 1\n"
                                  "Questions open: 2\n"), (1, 2), "the words mid-sentence are prose, not a count")
        self.assertEqual(declared("- **Blockers open:** 3.\n> Questions open: 0 (none)\n"), (3, 0))


if __name__ == "__main__":
    import unittest
    unittest.main()
