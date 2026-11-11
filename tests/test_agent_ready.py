"""Making an agent ready from the settings page, over the stand-in agent.

What is proved: the handshake's answer is kept — the agent's name and version, the time, whether it loads
a session, the ways to sign in — and shown on the page; a sign-in by a method of the agent's kind is the
agent's `authenticate`; a method of the terminal kind is run in a window and waited on, by the command the
agent named, and is the line to run where the board has no window; a sign-in given up on records nobody;
a conversation refused for want of a sign-in says where to sign in; an agent that cannot start is a
recorded fault, not a crash; and nothing starts for an agent this machine cannot launch.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import agent_ready, board_settings, settings_page
from slipwai.board_agent import SIGN_IN_FIRST, BoardAgent
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
        self.assertIn("It offers 2 models to pick from on this page.", state["lines"])
        self.assertEqual(read(self.file).offered["stand-in"][0]["values"][1]["value"], "b")
        self.assertTrue((self.root / "ready" / "stand-in" / ".acp" / "agent.log").is_file())
        with mock.patch.object(agent_ready, "launch_for", return_value=STAND_IN):
            signed = agent_ready.begin("stand-in", method="login")
        assert isinstance(signed, agent_ready.Readying)
        self.assertIn("Signed in, by login.", settled(signed)["lines"])
        self.assertIn("login", read(self.file).ready["stand-in"]["signed_in"])
        self.assertEqual(agent_ready.sign_in_line(STAND_IN, found["auth"][1]), f"{sys.executable} --setup")

    def made_ready(self) -> None:
        with mock.patch.object(agent_ready, "launch_for", return_value=STAND_IN):
            begun = agent_ready.begin("stand-in")
        assert isinstance(begun, agent_ready.Readying)
        settled(begun)

    def signing_in(self, status: int | Exception) -> tuple[dict, mock.Mock]:
        window = mock.Mock(side_effect=[status])
        with mock.patch.object(agent_ready, "launch_for", return_value=STAND_IN), \
                mock.patch.object(agent_ready, "in_a_window", window):
            begun = agent_ready.begin("stand-in", method="setup")
            assert isinstance(begun, agent_ready.Readying)
            return settled(begun), window

    def test_a_sign_in_that_is_a_terminal_s_is_run_in_a_window_and_waited_on(self) -> None:
        """A fresh machine had the agent and nobody signed in to it: the only sign-in the agent has is a
        command, the board never said it could run one, and so the agent offered none."""
        self.made_ready()
        state, window = self.signing_in(0)
        self.assertEqual(window.call_args.args[0], [sys.executable, "--setup"])
        self.assertEqual((state["lines"][-1], state["failed"]), ("Signed in, by Set up.", False))
        self.assertIn("setup", read(self.file).ready["stand-in"]["signed_in"])
        self.assertEqual(read(self.file).ready["stand-in"]["agent"], "stand-in", "what was found is kept")

    def test_a_sign_in_given_up_on_is_said_and_nobody_is_recorded_as_signed_in(self) -> None:
        self.made_ready()
        state, _ = self.signing_in(1)
        self.assertTrue(state["failed"])
        self.assertIn("ended with status 1: nobody is signed in", state["lines"][-1])
        state, _ = self.signing_in(OSError("no such file"))
        self.assertEqual(state["lines"][-1], "! The sign-in could not be run: no such file")
        self.assertNotIn("signed_in", read(self.file).ready["stand-in"])

    def test_the_command_is_the_one_the_agent_named_where_it_named_one(self) -> None:
        """An agent fetched by `npx` is a script in npm's cache: `npx --cli auth login` is not its sign-in."""
        fetched = Launch("claude", "Claude Code", ("npx", "@agentclientprotocol/claude-agent-acp"), "npx")
        method = {"id": "claude-ai-login", "type": "terminal", "args": ["--cli", "auth", "login"],
                  "_meta": {"terminal-auth": {"command": "/n/node", "args": ["/c/agent.js", "--cli", "auth", "login"]}}}
        self.assertEqual(agent_ready.sign_in_argv(fetched, method),
                         ["/n/node", "/c/agent.js", "--cli", "auth", "login"])
        self.assertIn("_meta", agent_ready.METHOD_FIELDS, "kept with the method, or the command is lost on a reload")

    @unittest.skipUnless(sys.platform == "darwin", "the script Terminal opens is a Mac's")
    def test_on_a_mac_the_window_is_a_script_that_leaves_its_status(self) -> None:
        run = subprocess.run

        def opened(argv: list[str], check: bool) -> None:
            run(["/bin/sh", argv[1]], check=check)  # what Terminal does with it

        with mock.patch.object(agent_ready.subprocess, "run", opened):
            status = agent_ready.in_a_window(["/bin/sh", "-c", 'test "$SAID" = "a b" && exit 7'],
                                             {"SAID": "a b", "PATH": "/usr/bin:/bin"}, self.root, limit=20)
        self.assertEqual(status, 7)

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
        self.assertEqual(agent_ready.state("zed"), {"key": "zed", "lines": [], "done": True, "failed": False})


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
        self.assertIn("not signed in from here; if a conversation says so, sign in by: Sign in, Set up.", page)
        self.assertIn('data-method="login">Sign in: Sign in</button>', page)
        self.assertIn(">Make ready again</button>", page)
        for windowed, said in ((True, 'data-method="setup">Sign in: Set up</button>'), (False, "Set up: run <code>")):
            with mock.patch("slipwai.settings_page.launches", return_value=[STAND_IN]), \
                    mock.patch.object(agent_ready, "WINDOWED", windowed):
                self.assertIn(said, self.get("/settings")[1])
        self.assertIn("else if (!state.failed) location.reload();", settings_page.SCRIPT,
                      "a sign-in that failed stays on the page: a reload took its reason with it")

    def test_a_conversation_refused_for_want_of_a_sign_in_says_where_to_sign_in(self) -> None:
        said: list[tuple[str, str]] = []

        def say(who: str, kind: str, text: str, more: dict | None) -> None:
            said.append((kind, text))

        agent = BoardAgent(STAND_IN, self.root / "talk", "agent", say)
        (self.root / "talk").mkdir()
        self.addCleanup(agent.close)
        self.assertEqual(agent.turn("signed out", 20), "fault")
        self.assertEqual(said[-1], ("error", SIGN_IN_FIRST))
        self.assertIn("Open Settings and press Sign in", SIGN_IN_FIRST)


if __name__ == "__main__":
    unittest.main()
