"""A drawing is never failed for what it declares, and a person's word is never lost, overruled or said unasked.

Round three of the storyboard conversation, through the running board with the stand-in agent: a drawing that
does not write the two counts ends well and goes on at `park` on either profile, and only a board advancing by
itself waits on them; Carry on, like Approve, waits on a message not yet said; a message not said can be said
now or discarded and is never said by itself; and `slipwai migrate` is the remedy for an unignored run folder
without restarting the board.
"""
from __future__ import annotations

import json
import subprocess
import time
from unittest import mock

import checkout_packages  # noqa: F401
from test_stage_talk import FEATURE, STAND_IN, Talking, until

from slipwai import stage_session, stage_talk, step_record
from slipwai.drawn import record_verdict
from slipwai.init_run import draw
from slipwai.review_reading import DECLARE


class DeclaredTest(Talking):
    def bare_pages(self) -> None:
        """A drawing as a project from before the two lines draws it: pages, and a research note without them."""
        (self.mockups / "basket.html").write_text('<title>Basket</title><article class="state"><h2>Empty</h2>'
                                                  "</article>", encoding="utf-8")
        (self.mockups / "storyboard.html").write_text("<title>Storyboard</title>", encoding="utf-8")
        (self.mockups / "research.md").write_text("# Research\n\n**Blockers:** two, I think\n", encoding="utf-8")

    def drawn_by_the_board(self) -> dict:
        with mock.patch.object(stage_session, "launchable", return_value=STAND_IN):
            fitting = draw(self.root)
            self.server.RequestHandlerClass.bench.outfit(self.root.resolve(), True).fitting = fitting  # type: ignore
            return self.ended(fitting)

    def test_at_park_a_drawing_without_the_lines_ends_well_and_the_build_goes_on_from_its_approval(self) -> None:
        for profile, next_step in (("standard", "approved; continuing the build"),
                                   ("event-modelling", "approved; modelling")):
            with self.subTest(profile):
                self.setUp()
                (self.root / "project.json").write_text(json.dumps({"profile": profile}), encoding="utf-8")
                self.bare_pages()
                said = self.drawn_by_the_board()
                self.assertEqual(said["code"], 0, "a drawing is not failed for what its note does not say")
                self.assertTrue(any(DECLARE.split("\n")[0] in line for line in said["lines"]),
                                "the board's own prompt told the drawing the two lines")
                self.assertEqual(self.post("/storyboard", {"feature": FEATURE, "verdict": "approved"}),
                                 (200, next_step))

    def test_advancing_with_no_lines_waits_for_the_person_and_says_which_line_and_where_it_comes_from(self) -> None:
        self.advance_on()
        self.bare_pages()
        step_record.ended(self.root, "surfaces", FEATURE, 0)  # it ended well, as the board saw it
        live = json.loads(self.get("/live.json")[1])
        self.assertFalse((self.mockups / "mock-states.md").exists())
        [why] = [one["text"] for one in live["waiting"]["holding"] if "does not say" in one["text"]]
        self.assertIn("`Blockers open: N` and `Questions open: N` with a number", why)
        self.assertIn("`slipwai migrate`", why)


class KeptTest(Talking):
    def stopped_with_a_message_waiting(self) -> dict:
        self.pages()
        fitting = self.drawing("linger")
        until(lambda: (self.root / ".lingering").exists())
        self.post("/stage/say", {"command": "mockups", "message": "make it green"})
        self.post("/stage/cancel", {})
        self.ended(fitting)
        [stuck] = self.talk()["undelivered"]
        return stuck

    def test_carry_on_waits_on_a_message_not_yet_said_as_approve_does(self) -> None:
        self.advance_on()
        self.stopped_with_a_message_waiting()
        status, said = self.post("/stage/carry-on", {})
        self.assertEqual(status, 409)
        self.assertIn("say it now, or discard it", said)
        self.get("/live.json")
        self.assertFalse((self.mockups / "mock-states.md").exists(), "and the board approved nothing past it")

    def test_a_message_not_said_is_never_said_unasked_and_can_be_discarded(self) -> None:
        stuck = self.stopped_with_a_message_waiting()
        self.assertEqual(self.post("/stage/say", {"command": "mockups", "message": "what does it show?"}),
                         (200, "said"))
        lines = self.ended(self.board_fitting())["lines"]
        time.sleep(0.3)
        self.assertNotIn("Drawn: make it green", self.board_fitting().said()["lines"], lines)
        self.assertEqual(self.post("/storyboard", {"feature": FEATURE, "verdict": "approved"})[0], 400)
        self.assertEqual(self.post("/stage/discard", {"command": "mockups", "id": stuck["id"]}), (200, "discarded"))
        talk = self.talk()
        self.assertEqual((talk["undelivered"], talk["discarded_ids"]), ([], [stuck["id"]]),
                         "kept in the conversation, marked discarded")
        self.assertEqual(self.post("/stage/carry-on", {}), (200, "carrying on"), "and it holds nothing")
        self.assertEqual(self.post("/storyboard", {"feature": FEATURE, "verdict": "parked", "reason": "plainer"})[0],
                         200)

    def test_migrate_is_the_remedy_without_restarting_the_board_and_the_card_says_so_first(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / ".slipwai/stages/mockups").mkdir(parents=True)
        (self.root / ".slipwai/stages/mockups/session").write_text("s-1\n", encoding="utf-8")
        self.assertIn("run `slipwai migrate`", self.talk()["unkept"], "said before anybody types")
        status, said = self.post("/stage/say", {"command": "mockups", "message": "my private thought"})
        self.assertEqual(status, 400)
        (self.root / ".gitignore").write_text(".slipwai/\n", encoding="utf-8")  # what migrate's ignore line does
        self.assertEqual(self.talk()["unkept"], "")
        with mock.patch.object(stage_session, "launchable", return_value=STAND_IN):
            self.assertEqual(self.post("/stage/say", {"command": "mockups", "message": "now, then"}), (200, "said"))
            self.ended(self.board_fitting())
        self.assertIn("now, then", [one["text"] for one in stage_talk.turns(self.root, "mockups")])

    def test_continue_the_build_and_model_again_give_one_answer_on_a_changed_storyboard(self) -> None:
        self.pages()
        record_verdict(self.root, FEATURE, "approved")
        self.page_changed()
        status, said = self.post("/launch", {})
        self.assertEqual(status, 400)
        self.assertIn("has changed since its verdict", said)
        self.assertFalse(json.loads(self.get("/live.json")[1])["passage"]["launchable"], "and it is not offered")

    def page_changed(self) -> None:
        (self.mockups / "basket.html").write_text('<title>Basket</title><article class="state"><h2>Full</h2>'
                                                  "</article>", encoding="utf-8")
