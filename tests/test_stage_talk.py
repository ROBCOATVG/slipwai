"""A storyboard a person can talk about, a board that does not move on past a person's word, and a stage seen
running where its result will appear — through the running board, with a stand-in agent.

The first real run of this build drew a storyboard in eight minutes nobody could see, reviewed it into 84
findings and a list of questions, and offered two moves: approve all 49 states, or redraw all of them. A
person typed a question under it; the reply's turn ended well; the board, set to advance, read that end as
the step's and approved everything, then started the model; and the conversation went with the stage. Each
test here is one of those, the other way round.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import board_settings, stage_session, stage_talk, step_record
from slipwai.bridge import serve
from slipwai.drawn import record_verdict
from slipwai.init_run import Fitting, Step
from slipwai.project.cruise import cruise_config
from slipwai.stage_session import TALKING, StageSession
from slipwai.upstream import APPROVED_BY, unjudged
from slipwai.wheel import CONFIG, MORE

AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
STAND_IN = board_settings.Launch("stand-in", "Stand-in", (sys.executable, str(AGENT)), "a script")
FEATURE = "001-boats"


def until(check, seconds: float = 20) -> None:
    for _ in range(int(seconds / 0.05)):
        if check():
            return
        time.sleep(0.05)
    raise AssertionError("it never happened")


class Talking(BoardTest):
    """A board with a drawn feature, a stand-in agent to draw it, and the reads a test of talking needs."""

    def setUp(self) -> None:
        super().setUp()
        patched = mock.patch.object(board_settings, "SETTINGS", self.root / "board.json")
        patched.start()
        self.addCleanup(patched.stop)
        (self.root / "specs" / FEATURE / "mockups").mkdir(parents=True)
        (self.root / "specs" / FEATURE / "spec.md").write_text("# Boats\n", encoding="utf-8")
        (self.root / ".specify").mkdir()
        (self.root / CONFIG).write_text(cruise_config(), encoding="utf-8")

    @property
    def mockups(self) -> Path:
        return self.root / "specs" / FEATURE / "mockups"

    def advance_on(self) -> None:
        held = json.loads((self.root / CONFIG).read_text(encoding="utf-8"))
        (self.root / CONFIG).write_text(json.dumps({**held, "upstream": "advance"}), encoding="utf-8")

    def pages(self, blockers: int = 0, questions: int = 0, prose: str = "") -> None:
        """A drawing, with the two lines its research note declares about what is left to discuss."""
        (self.mockups / "basket.html").write_text('<title>Basket</title><article class="state"><h2>Empty</h2>'
                                                  "</article>", encoding="utf-8")
        (self.mockups / "storyboard.html").write_text("<title>Storyboard</title>", encoding="utf-8")
        (self.mockups / "research.md").write_text(f"# Research\n\nBlockers open: {blockers}\nQuestions open: "
                                                  f"{questions}\n\n{prose}", encoding="utf-8")
        step_record.ended(self.root, "surfaces", FEATURE, 0)  # and its end, as the board would have written it

    def board_fitting(self) -> Fitting:
        return self.server.RequestHandlerClass.bench.outfit(self.root.resolve()).fitting  # type: ignore[attr-defined]

    def drawing(self, argument: str = FEATURE) -> Fitting:
        """The storyboard drawn by the stand-in over the protocol, as the board's own run: what Draw starts."""
        stage = StageSession(self.root, "mockups", argument, launch=STAND_IN, pid="surfaces.pid", stage="")
        fitting = Fitting(self.root, [Step([], "Drawing.", lambda code: f"ended {code}", "surfaces",
                                           session=stage.run)])
        self.server.RequestHandlerClass.bench.outfit(self.root.resolve(), True).fitting = fitting  # type: ignore
        fitting.thread.start()
        return fitting

    def ended(self, fitting: Fitting) -> dict:
        try:
            until(lambda: fitting.said()["done"] and not fitting.thread.is_alive())
        except AssertionError:
            raise AssertionError(fitting.said()) from None
        return fitting.said()

    def talk(self, since: int = 0) -> dict:
        return json.loads(self.get(f"/stage/talk.json?command=mockups&since={since}")[1])


class StageTalkTest(Talking):
    def test_a_question_about_the_drawn_storyboard_is_answered_and_approves_nothing(self) -> None:
        """The incident: drawn, a question asked, the reply's turn ended — with `advance` set."""
        self.advance_on()
        self.pages()
        self.ended(self.drawing())  # no poll in between: the board had not advanced when the person spoke
        self.assertEqual(self.post("/stage/say", {"command": "mockups", "message": "why is the cart empty?"}),
                         (200, "said"))
        said = self.ended(self.board_fitting())
        self.assertIn("Drawn: why is the cart empty?", said["lines"])
        live = json.loads(self.get("/live.json")[1])  # the poll is the board's clock: this is where it advanced
        self.assertFalse((self.mockups / "mock-states.md").exists(), "asking a question approved nothing")
        self.assertEqual(self.board_fitting().said()["step"], "surfaces", "and nothing after it was started")
        held = [one["text"] for one in live["waiting"]["holding"]]
        self.assertTrue(any(one.startswith("You said something to the drawing stage") for one in held), held)
        talk = self.talk()
        self.assertEqual([(one["role"], one["text"]) for one in talk["turns"] if one["kind"] == "text"],
                         [("person", "why is the cart empty?"), ("agent", "Drawn: why is the cart empty?")])
        self.assertTrue(talk["carry"])
        self.assertIn("press Carry on", talk["held"])
        self.assertIn('id="storyboard-talk"', self.get("/voyage")[1])
        self.assertEqual(self.post("/stage/carry-on", {}), (200, "carrying on"))
        self.get("/live.json")
        written = (self.mockups / "mock-states.md").read_text(encoding="utf-8")
        self.assertTrue(written.startswith(APPROVED_BY), "Carry on is the person's word, and then it advances")

    def test_a_review_with_a_blocker_stops_the_board_and_says_why_where_the_person_looks(self) -> None:
        self.advance_on()
        self.pages(1, 1, "## Questions\n- Can two members share a boat?\n")
        (self.mockups / "review.md").write_text("## Basket\n- [Blocker] The basket has no total\n"
                                                "- [Nice-to-have] Rounder corners\n", encoding="utf-8")
        live = json.loads(self.get("/live.json")[1])
        self.assertFalse((self.mockups / "mock-states.md").exists())
        reason = ("The storyboard for 001-boats waits for you rather than being approved by the board: the drawing "
                  "says 1 Blocker is open; 1 question only you can answer is open")
        self.assertIn({"n": 1, "text": reason, "href": "#mockups"}, live["waiting"]["holding"])
        self.assertEqual(self.talk()["held"], reason, "and the stage card says it, from the same poll")
        page = self.get("/voyage")[1]
        self.assertIn('<details class="findings" id="findings-001-boats"><summary>What the drawing found · '
                      "its own count: 1 Blocker and 1 question open · 1 Blocker · 1 Nice-to-have</summary>", page,
                      "collapsed, with the drawing's own count first")
        self.assertLess(page.index("<h3>Blockers</h3>"), page.index("<h3>Open questions"), "Blockers first")
        self.assertIn('data-talk-about="About the Blocker on Basket: “The basket has no total” — "', page)
        self.assertIn('data-talk-about="Answering “Can two members share a boat?”: "', page)
        self.pages(3, 1, "## Questions\n- Can two members share a boat?\n")
        page = self.get("/voyage")[1]
        self.assertIn("1 Blocker and 1 question listed here, as far as the files could be read; the count the "
                      "board goes by is the drawing&#x27;s own.", page)
        self.assertIn("the drawing says 3 Blockers are open", self.talk()["held"])

    def test_a_clean_review_with_nothing_said_is_approved_by_the_board_as_before(self) -> None:
        self.advance_on()
        self.pages()
        (self.mockups / "review.md").write_text("- [Should-address] A plainer label\n", encoding="utf-8")
        self.get("/live.json")
        self.assertTrue((self.mockups / "mock-states.md").read_text(encoding="utf-8").startswith(APPROVED_BY))

    def test_the_conversation_survives_the_next_stage_and_a_restart_and_carries_on_from_either(self) -> None:
        self.pages()
        self.ended(self.drawing())
        self.post("/stage/say", {"command": "mockups", "message": "the organiser books"})
        self.ended(self.board_fitting())
        model = Fitting(self.root, [Step([sys.executable, "-c", "print('modelled')"], "Modelling.",
                                         lambda code: "", "model")])
        self.server.RequestHandlerClass.bench.outfit(self.root.resolve()).fitting = model  # type: ignore
        model.thread.start()
        self.ended(model)
        texts = [one["text"] for one in self.talk()["turns"] if one["kind"] == "text"]
        self.assertEqual(texts, ["the organiser books", "Drawn: the organiser books"], "the next stage started")
        with mock.patch.object(stage_session, "launchable", return_value=STAND_IN):
            self.assertEqual(self.post("/stage/say", {"command": "mockups", "message": "and members?"}),
                             (200, "said"))
            self.ended(self.board_fitting())
        self.assertIn("modelled", self.board_fitting().said()["lines"], "the receipt so far is kept")
        later = serve(self.root, "127.0.0.1", 0)  # the app restarted: a new board, nothing in memory
        self.addCleanup(later.server_close)
        import threading
        threading.Thread(target=later.serve_forever, daemon=True).start()
        self.addCleanup(later.shutdown)
        where = f"http://127.0.0.1:{later.server_address[1]}"
        with urllib.request.urlopen(f"{where}/stage/talk.json?command=mockups&seat=w", timeout=5) as answer:
            turns = json.loads(answer.read().decode("utf-8"))["turns"]
        self.assertEqual([one["text"] for one in turns if one["kind"] == "text"][-2:],
                         ["and members?", "Drawn: and members?"])
        with urllib.request.urlopen(f"{where}/voyage?seat=w", timeout=5) as answer:
            self.assertIn('id="storyboard-talk"', answer.read().decode("utf-8"))

    def test_a_page_the_conversation_changes_loses_its_verdict_and_the_board_says_which(self) -> None:
        self.pages()
        (self.mockups / "total.html").write_text('<title>Total</title><article class="state"><h2>Shown</h2>'
                                                 "</article>", encoding="utf-8")
        self.ended(self.drawing())
        record_verdict(self.root, FEATURE, "approved")
        self.assertEqual(unjudged(self.root), "")
        self.post("/stage/say", {"command": "mockups", "message": "what does the total say?"})
        self.ended(self.board_fitting())
        self.assertIn("— approved", (self.mockups / "mock-states.md").read_text(encoding="utf-8"),
                      "a turn that changed no page leaves the verdict standing")
        self.post("/stage/say", {"command": "mockups", "message": "repaint it with a total"})
        said = self.ended(self.board_fitting())
        self.assertIn("! The verdict on what this changed no longer stands, so it waits on yours again: Basket — "
                      "Empty; Total — Shown.", said["lines"])
        verdicts = (self.mockups / "mock-states.md").read_text(encoding="utf-8")
        self.assertNotIn("— approved", verdicts)
        self.assertEqual(unjudged(self.root), FEATURE, "the storyboard waits on a verdict again")
        page = self.get("/voyage")[1]
        self.assertIn("Changed since your verdict, so not approved: Basket — Empty (in the conversation); Total — "
                      "Shown (in the conversation).", page)
        self.assertIn('data-verdict="approved">Approve storyboard', page, "and the buttons are back")
        record_verdict(self.root, FEATURE, "approved")
        self.assertEqual(unjudged(self.root), "", "and a verdict given again stands")

    def test_something_said_while_the_stage_draws_is_queued_and_said_when_its_turn_ends(self) -> None:
        self.advance_on()
        self.pages()
        fitting = self.drawing("dawdle")
        until(lambda: (self.root / ".dawdling").exists())
        page = self.get("/voyage")[1]
        self.assertIn('id="surfaces-running"', page, "a card in the storyboard's place while it draws")
        self.assertIn('data-stage-marker="mockups">drawing</span>', page, "and the Screens tab is marked")
        self.assertNotIn('id="mockups"', page)
        self.assertTrue(json.loads(self.get("/live.json")[1])["passage"]["shape"].startswith("surfaces|"))
        self.assertEqual(self.post("/stage/say", {"command": "mockups", "message": "make it blue"}), (200, "queued"))
        talk = self.talk()
        self.assertEqual([(one["text"], one.get("queued")) for one in talk["turns"]], [("make it blue", True)])
        self.assertTrue(talk["running"])
        self.assertIn("and it waits to be said", talk["held"])
        (self.root / ".go").write_text("", encoding="utf-8")
        until(lambda: "Drawn: make it blue" in fitting.said()["lines"])
        self.ended(fitting)
        talk = self.talk()
        self.assertEqual(talk["queued_ids"], [], "said, and shown as said")
        self.assertIn("Drawn: make it blue", [one["text"] for one in talk["turns"]])
        live = json.loads(self.get("/live.json")[1])
        self.assertFalse(live["passage"]["shape"].startswith("surfaces|"), "its end is a new shape: a reload")
        self.assertIn('id="mockups"', self.get("/voyage")[1])
        self.assertIn("The storyboard for 001-boats is ready to look at: approve it or send it back",
                      [one["text"] for one in live["waiting"]["holding"]])
        self.assertFalse((self.mockups / "mock-states.md").exists(), "a queued word holds the board too")

    def test_the_model_running_is_said_on_the_model_tab(self) -> None:
        waits = "import pathlib, time\nwhile not pathlib.Path('.go').exists(): time.sleep(0.05)"
        model = Fitting(self.root, [Step([sys.executable, "-c", waits], "Modelling.", lambda code: "", "model")])
        self.server.RequestHandlerClass.bench.outfit(self.root.resolve(), True).fitting = model  # type: ignore
        model.thread.start()
        page = self.get("/voyage")[1]
        self.assertIn('id="model-running"', page)
        self.assertIn('data-stage-marker="model">modelling</span>', page)
        (self.root / ".go").write_text("", encoding="utf-8")
        self.ended(model)
        self.assertNotIn('id="model-running"', self.get("/voyage")[1])

    def test_a_reply_is_judged_by_the_stage_s_own_after_check_as_it_was_at_park(self) -> None:
        """A draft that stopped short, finished by a reply, has ended well — as it always had at `park`; one the
        reply did not finish is still short. Whether the board moves on from it is the hold's business."""
        finished = self.root / "specs/002-more/spec.md"
        stage = StageSession(self.root, "draft", "docs/prd.md", launch=STAND_IN,
                             after=lambda: "" if finished.is_file() else "no specification yet")
        fitting = Fitting(self.root, [Step([], "Drafting.", lambda code: f"ended {code}", "draft",
                                           session=stage.run)])
        fitting.thread.start()
        self.assertEqual(self.ended(fitting)["code"], 1)
        self.assertTrue(fitting.reply("the organiser books"))
        self.assertEqual(self.ended(fitting)["code"], 1, "the reply did not write it: still short")
        finished.parent.mkdir(parents=True)
        finished.write_text("# More\n", encoding="utf-8")
        self.assertTrue(fitting.reply("write it, then"))
        said = self.ended(fitting)
        self.assertIn("Drawn: write it, then", said["lines"])
        self.assertEqual(said["code"], 0, "the after-check passes now, so the stage has ended well")

    def test_a_turn_of_conversation_is_asked_to_write_down_what_is_decided(self) -> None:
        asked: list[str] = []

        def session(one: StageSession, fitting: Fitting, launch: object, words: str, first: bool) -> int:
            asked.append(words)
            return 0
        stage = StageSession(self.root, "mockups", launch=STAND_IN)
        with mock.patch.object(StageSession, "session", session):
            stage.follow(Fitting(self.root, []), "members may cancel up to a day before")
        self.assertEqual(asked, [f"members may cancel up to a day before\n\n---\n{TALKING}"])
        self.assertIn("write it down in this turn where the command says such things are kept", TALKING)
        page = " ".join((Path(__file__).resolve().parents[1] / "assets/toolkit/commands/mockups.md")
                        .read_text(encoding="utf-8").split())
        self.assertIn("the next entry of `specs/<feature>/decisions.md`, in the shape `commands/cruise.md` shows, "
                      "with `Decided by: human`", page)
        self.assertIn("A verdict is still not yours", page)

    def test_a_verdict_lets_go_of_the_hold_a_word_put_on_the_board(self) -> None:
        self.advance_on()
        self.pages()
        stage_talk.said(self.root, "mockups", "who books?")
        self.assertEqual(stage_talk.held(self.root), ["mockups"])
        self.assertEqual(self.post("/storyboard", {"feature": FEATURE, "verdict": "parked", "reason": "plainer"})[0],
                         200)
        self.assertEqual(stage_talk.held(self.root), [], "Approve and Disapprove are the word to carry on")

    def test_the_setting_says_what_advancing_now_does(self) -> None:
        says = MORE["upstream"]  # the row's sentence, under its short choices
        self.assertIn("still waits for you on a storyboard whose drawing says a Blocker or a question is open", says)
        self.assertIn("until you press Carry on", says)
        self.assertIn("did not see end well", says)


if __name__ == "__main__":
    import unittest
    unittest.main()
