"""The console: a read-only conversation with the harbourmaster, driven by a stand-in for the agent.

The agent is a command the console is handed, so what runs here is the real conversation — the turns, the
poll, the refusal while an answer is being written — over a script that prints the stream the agent prints.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import console

# What the agent prints for one question: it opens a file, then says something. The question is the last
# argument, which is how the console passes it.
STAND_IN = """
import json, sys, time
question = sys.argv[-1]
time.sleep(float(__import__('os').environ.get('STAND_IN_WAIT', '0')))
print('not json, a banner')
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "tool_use", "name": "Read", "input": {"file_path": ".slipwai/logs/harbour.jsonl"}}]}}))
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "You asked: " + question}]}}))
print(json.dumps({"type": "result", "is_error": False, "result": "done"}))
"""


class ConsoleTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        script = Path(tempfile.mkdtemp()) / "agent.py"
        script.write_text(STAND_IN, encoding="utf-8")
        self.talking = console.Console(self.root, [sys.executable, str(script)])
        console.CONSOLES[self.root.resolve()] = self.talking
        self.addCleanup(console.CONSOLES.clear)

    def settle(self) -> dict:
        for _ in range(100):
            _, body = self.get("/console.json?since=0")
            said = json.loads(body)
            if not said["busy"]:
                return said
            time.sleep(0.05)
        self.fail("the console never finished answering")

    def test_a_question_comes_back_as_the_file_read_and_the_words_said(self) -> None:
        code, said = self.post("/console/ask", {"message": "why is ORD-01 waiting?"})
        self.assertEqual((code, said), (200, "asked"))
        turns = self.settle()["turns"]
        self.assertEqual([(t["role"], t["kind"]) for t in turns],
                         [("person", "text"), ("harbourmaster", "read"), ("harbourmaster", "text")])
        self.assertEqual(turns[1]["text"], "Read .slipwai/logs/harbour.jsonl")
        self.assertEqual(turns[2]["text"], "You asked: why is ORD-01 waiting?")

    def test_a_poll_carries_only_what_the_asker_does_not_have(self) -> None:
        self.post("/console/ask", {"message": "one"})
        first = self.settle()
        _, body = self.get(f"/console.json?since={first['at']}")
        self.assertEqual(json.loads(body)["turns"], [])

    def test_an_empty_question_and_a_second_while_one_is_under_way_are_refused(self) -> None:
        code, said = self.post("/console/ask", {"message": "   "})
        self.assertEqual(code, 400)
        self.assertIn("ask the harbourmaster something", said)
        os.environ["STAND_IN_WAIT"] = "1"
        self.addCleanup(os.environ.pop, "STAND_IN_WAIT", None)
        self.assertEqual(self.post("/console/ask", {"message": "slow"})[0], 200)
        code, said = self.post("/console/ask", {"message": "again"})
        self.assertEqual(code, 400)
        self.assertIn("still answering", said)
        self.settle()

    def test_a_new_conversation_forgets_the_old_one(self) -> None:
        self.post("/console/ask", {"message": "one"})
        self.settle()
        self.assertEqual(self.post("/console/reset", {})[1], "cleared")
        self.assertEqual(self.settle()["turns"], [])

    def test_the_dock_is_on_the_voyage_window_and_not_on_the_published_copy(self) -> None:
        self.assertIn('id="console"', self.get("/voyage")[1])
        self.assertNotIn('id="console"', self.rendered(controls=False))


class AgentCommandTest(unittest.TestCase):
    """What the real session is started with, off a stub `claude` on the path."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.bin = Path(tempfile.mkdtemp())
        held = os.environ["PATH"]
        os.environ["PATH"] = str(self.bin)
        self.addCleanup(os.environ.__setitem__, "PATH", held)

    def stub(self) -> None:
        """A `claude` the path lookup finds: a script on POSIX, and on Windows a `.cmd` beside it, since
        `shutil.which` there finds only names with an extension `PATHEXT` lists. Nothing runs it."""
        path = self.bin / "claude"
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        if os.name == "nt":
            (self.bin / "claude.cmd").write_text("@echo off\r\n", encoding="utf-8")

    def test_the_session_can_read_and_search_and_nothing_else(self) -> None:
        self.stub()
        held = console.Console(self.root)
        held.session = "abc"
        argv = held.argv("hello") or []
        self.assertEqual(argv[argv.index("--tools") + 1], "Read,Grep,Glob")
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "Read,Grep,Glob")
        for power in ("Bash", "Edit", "Write", "WebFetch", "--dangerously-skip-permissions"):
            self.assertNotIn(power, " ".join(argv))

    def test_the_first_question_starts_a_session_and_the_next_resumes_it(self) -> None:
        self.stub()
        held = console.Console(self.root)
        held.session = "abc"
        self.assertIn("--session-id", held.argv("one") or [])
        held.begun = True
        self.assertIn("--resume", held.argv("two") or [])

    def test_the_brief_is_the_project_s_own_with_its_front_matter_taken_off(self) -> None:
        (self.root / "agents").mkdir()
        (self.root / "agents/harbour-harbourmaster.md").write_text(
            "---\ndescription: x\n---\nYou are the harbourmaster.\n", encoding="utf-8")
        self.assertEqual(console.brief(self.root), "You are the harbourmaster.")

    def test_a_machine_with_no_agent_says_so_rather_than_hanging(self) -> None:
        held = console.Console(self.root)
        held.ask("anyone there?")
        said = held.said()
        self.assertFalse(said["busy"])
        self.assertEqual(said["turns"][-1]["kind"], "error")
        self.assertIn("claude", said["turns"][-1]["text"])


if __name__ == "__main__":
    unittest.main()
