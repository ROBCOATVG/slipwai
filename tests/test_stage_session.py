"""A stage over the Agent Client Protocol, run by a step in place of a child, over the stand-in agent.

What is proved: the stage's prompt makes any agent read the command's file and carries the asking rule; the
agent's words and work are lines on the receipt; a question from the agent is a card the board answers
through its route; a stop ends the stage with a status; and a project with nothing to launch is told so.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import board_settings, stage_session
from slipwai.board_settings import Launch
from slipwai.init_run import Fitting, Step, draft_step
from slipwai.stage_session import ASKING, StageSession, prompt_for

AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
STAND_IN = Launch("stand-in", "Stand-in", (sys.executable, str(AGENT)), "a script")


def finished(fitting: Fitting, seconds: float = 20) -> dict:
    for _ in range(int(seconds / 0.05)):
        said = fitting.said()
        if said["done"]:
            return said
        time.sleep(0.05)
    raise AssertionError("the stage never ended")


class StageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        patched = mock.patch.object(board_settings, "SETTINGS", self.root / "board.json")
        patched.start()
        self.addCleanup(patched.stop)

    def test_the_prompt_makes_any_agent_read_the_command_and_carries_the_asking_rule(self) -> None:
        said = prompt_for("draft", "docs/prd.md")
        self.assertTrue(said.startswith("Run the /draft command: read commands/draft.md and follow it exactly as "
                                        "written, with `docs/prd.md` as its argument."))
        self.assertIn(ASKING, said)
        self.assertIn("it is given no argument", prompt_for("launch"))

    def test_a_stage_is_a_step_whose_lines_are_the_agents_words_and_work(self) -> None:
        stage = StageSession(self.root, "draft", "docs/prd.md", launch=STAND_IN)
        fitting = Fitting(self.root, [Step([], "Drafting.", lambda code: f"ended {code}", "draft", session=stage.run)])
        fitting.thread.start()
        said = finished(fitting)
        self.assertEqual(said["code"], 0)
        self.assertEqual(said["step"], "draft")
        lines = said["lines"]
        self.assertEqual(lines[0], "Drafting.")
        self.assertIn("On Stand-in, over the Agent Client Protocol.", lines)
        self.assertTrue(any(line.startswith("Drawn: Run the /draft command") for line in lines), lines)
        self.assertTrue(any(line.startswith("· Write ") and line.endswith("prototype/index.html") for line in lines),
                        "a tool call is a line, with its path short")
        self.assertEqual(lines[-1], "ended 0")
        self.assertTrue((self.root / "prototype" / "index.html").is_file(), "a write inside the project was allowed")
        self.assertTrue((self.root / ".slipwai" / "stages" / "draft" / "session").is_file(), "kept under the board's")
        self.assertTrue(stage.said()["done"])

    def test_a_question_is_a_card_the_board_answers_and_a_stop_ends_the_stage(self) -> None:
        stage = StageSession(self.root, "draft", "ask", launch=STAND_IN)
        fitting = Fitting(self.root, [Step([], "Drafting.", lambda code: f"ended {code}", "draft", session=stage.run)])
        fitting.thread.start()
        asked = None
        for _ in range(400):
            asked = next((t for t in stage.said()["turns"] if t["kind"] == "question"), None)
            if asked:
                break
            time.sleep(0.05)
        assert asked is not None
        self.assertIn("? Which colour? — waiting on your answer, on the board", fitting.said()["lines"])
        self.assertTrue(stage.answer(asked["ask"]["id"], "blue"))
        said = finished(fitting)
        self.assertIn("You said: blue", said["lines"])
        self.assertEqual(said["code"], 0)
        slow = StageSession(self.root, "draft", "slow", launch=STAND_IN)
        fitting = Fitting(self.root, [Step([], "Drafting.", lambda code: f"ended {code}", "draft", session=slow.run)])
        fitting.thread.start()
        for _ in range(400):
            if any(t["kind"] == "permission" for t in slow.said()["turns"]):
                break
            time.sleep(0.05)
        self.assertEqual(slow.cancel(), "stopped")
        self.assertEqual(finished(fitting)["code"], 1, "a stopped stage ends as a failed step")

    def test_with_nothing_to_launch_the_draft_is_the_headless_child(self) -> None:
        with mock.patch.object(stage_session, "launchable", return_value=None):
            step = draft_step(self.root)
        self.assertEqual((step.argv, step.session), (["make", "draft"], None))
        with mock.patch.object(stage_session, "launchable", return_value=STAND_IN):
            step = draft_step(self.root)
        self.assertEqual(step.argv, [])
        self.assertIsNotNone(step.session)
        self.assertIn("over the Agent Client Protocol", step.announced)


class StageRoutesTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        patched = mock.patch.object(board_settings, "SETTINGS", self.root / "board.json")
        patched.start()
        self.addCleanup(patched.stop)

    def test_the_cards_are_answered_and_the_stage_stopped_from_the_board(self) -> None:
        self.assertEqual(json.loads(self.get("/stage.json")[1]), {"turns": [], "at": 0, "done": True, "command": ""})
        self.assertEqual(self.post("/stage/cancel", {})[0], 400)
        stage = StageSession(self.root, "draft", "ask", launch=STAND_IN)
        fitting = Fitting(self.root, [Step([], "Drafting.", lambda code: f"ended {code}", "draft", session=stage.run)])
        bench = self.server.RequestHandlerClass.bench  # type: ignore[attr-defined]
        bench.outfit(self.root.resolve(), True).fitting = fitting  # the board's running child, as it holds it
        fitting.thread.start()
        asked = None
        for _ in range(400):
            turns = json.loads(self.get("/stage.json?since=0")[1])["turns"]
            asked = next((t for t in turns if t["kind"] == "question"), None)
            if asked:
                break
            time.sleep(0.05)
        assert asked is not None
        self.assertEqual(self.post("/stage/answer", {"id": "q9", "answer": "x"})[0], 400)
        self.assertEqual(self.post("/stage/answer", {"id": asked["ask"]["id"], "answer": "blue"}), (200, "answered"))
        self.assertIn("You said: blue", finished(fitting)["lines"])
        page = self.get("/voyage")[1]
        self.assertIn('id="stage-asks"', page)
        self.assertIn('id="stage-stop"', page)


if __name__ == "__main__":
    unittest.main()
