"""Making an agent ready from the settings page, over the stand-in agent.

What is proved: the handshake's answer is kept — the agent's name and version, the time, whether it loads
a session, the ways to sign in — and shown on the page; a sign-in by a method of the agent's kind is the
agent's `authenticate`; a method of the terminal kind is the line to run; an agent that cannot start is a
recorded fault, not a crash; and nothing starts for an agent this machine cannot launch.
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

from slipwai import agent_ready, board_settings
from slipwai.board_settings import Launch, read

AGENT = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
STAND_IN = Launch("stand-in", "Stand-in", (sys.executable, str(AGENT)), "a script")
DIES = Launch("dies", "Dies", (sys.executable, "-c", "raise SystemExit(2)"), "a script")


def settled(readying: agent_ready.Readying, seconds: float = 20) -> dict:
    for _ in range(int(seconds / 0.05)):
        state = readying.state()
        if state["done"]:
            return state
        time.sleep(0.05)
    raise AssertionError("never done")


class ReadyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.file = self.root / "board.json"
        for patched in (mock.patch.object(board_settings, "SETTINGS", self.file),
                        mock.patch.object(agent_ready, "HOME", self.root / "ready"),
                        mock.patch.dict(agent_ready.RUNNING, clear=True)):
            patched.start()
            self.addCleanup(patched.stop)

    def test_the_handshake_s_answer_is_kept_and_a_sign_in_is_the_agent_s_authenticate(self) -> None:
        with mock.patch.object(agent_ready, "launch_for", return_value=STAND_IN):
            begun = agent_ready.begin("stand-in")
        assert isinstance(begun, agent_ready.Readying)
        state = settled(begun)
        self.assertIn("stand-in 0.1 answered the handshake in", state["lines"][1])
        found = read(self.file).ready["stand-in"]
        self.assertEqual((found["agent"], found["version"], found["load_session"], found["fault"]),
                         ("stand-in", "0.1", True, ""))
        self.assertEqual([m["id"] for m in found["auth"]], ["login", "setup"])
        self.assertTrue((self.root / "ready" / "stand-in" / ".acp" / "agent.log").is_file())
        with mock.patch.object(agent_ready, "launch_for", return_value=STAND_IN):
            signed = agent_ready.begin("stand-in", method="login")
        assert isinstance(signed, agent_ready.Readying)
        self.assertIn("Signed in, by login.", settled(signed)["lines"])
        self.assertIn("login", read(self.file).ready["stand-in"]["signed_in"])
        with mock.patch.object(agent_ready, "launch_for", return_value=STAND_IN):
            refused = agent_ready.begin("stand-in", method="setup")
        assert isinstance(refused, agent_ready.Readying)
        self.assertIn("! the agent refused authenticate: setup is not a way to sign in", settled(refused)["lines"])
        self.assertEqual(agent_ready.sign_in_line(STAND_IN, found["auth"][1]), f"{sys.executable} --setup")

    def test_an_agent_that_cannot_start_is_a_recorded_fault_and_an_unable_one_never_starts(self) -> None:
        with mock.patch.object(agent_ready, "launch_for", return_value=DIES):
            begun = agent_ready.begin("dies")
        assert isinstance(begun, agent_ready.Readying)
        self.assertTrue(settled(begun)["lines"][-1].startswith("! the agent exited 2"))
        self.assertIn("exited 2", read(self.file).ready["dies"]["fault"])
        unable = Launch("goose", "Goose", (), "not on PATH")
        with mock.patch.object(agent_ready, "launch_for", return_value=unable):
            self.assertEqual(agent_ready.begin("goose"), "Goose cannot be made ready here: not on PATH")
        self.assertEqual(agent_ready.begin("zed"), "zed is not a harness the registry can launch")
        self.assertEqual(agent_ready.state("zed"), {"key": "zed", "lines": [], "done": True})


class ReadyPageTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.file = self.root / "board.json"
        for patched in (mock.patch.object(board_settings, "SETTINGS", self.file),
                        mock.patch.object(agent_ready, "HOME", self.root / "ready"),
                        mock.patch.dict(agent_ready.RUNNING, clear=True)):
            patched.start()
            self.addCleanup(patched.stop)

    def test_the_page_makes_an_agent_ready_and_shows_what_it_said(self) -> None:
        self.assertEqual(self.post("/settings/ready", {"key": "zed"})[0], 400)
        with mock.patch.object(agent_ready, "launch_for", return_value=STAND_IN):
            self.assertEqual(self.post("/settings/ready", {"key": "stand-in"}), (200, "Making Stand-in ready…"))
        for _ in range(400):
            state = json.loads(self.get("/settings/ready.json?key=stand-in")[1])
            if state["done"]:
                break
            time.sleep(0.05)
        self.assertTrue(state["done"])
        with mock.patch("slipwai.settings_page.launches", return_value=[STAND_IN]):
            page = self.get("/settings")[1]
        self.assertIn("Ready: stand-in 0.1 answered in", page)
        self.assertIn("sign-in: Sign in, Set up.", page)
        self.assertIn('data-method="login">Sign in: Sign in</button>', page)
        self.assertIn("Set up: run <code>", page)
        self.assertIn(">Make ready again</button>", page)


if __name__ == "__main__":
    unittest.main()
