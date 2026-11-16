"""The board's kept read under load and under a person's hand, and what waits on a person when the fold has
nothing to say about it.

`test_live_board` holds the bands; this holds the read they are drawn from — threads at once, an action
in the middle of a read, every route that changes something, a read that fails, two projects — and the
list of what waits on a person read from the fleet's own logs rather than from the fold's rows.
"""
from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import board_read, logs

EMPTY = board_read.Read([], "", {}, {}, {}, [], {})


class LoadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.made: list[Path] = []
        board_read.forget()
        self.addCleanup(board_read.forget)

    def slow(self, root: Path) -> board_read.Read:
        self.made.append(root)
        time.sleep(0.2)
        return EMPTY

    def test_polls_arriving_together_make_one_read(self) -> None:
        with mock.patch.object(board_read, "fold", self.slow):
            threads = [threading.Thread(target=board_read.read, args=(self.root,)) for _ in range(12)]
            for one in threads:
                one.start()
            for one in threads:
                one.join()
        self.assertEqual(len(self.made), 1)

    def test_an_action_during_a_read_in_flight_is_not_answered_by_that_read_afterwards(self) -> None:
        begun, release = threading.Event(), threading.Event()

        def held(root: Path) -> board_read.Read:
            self.made.append(root)
            begun.set()
            release.wait(5)
            return EMPTY
        with mock.patch.object(board_read, "fold", held):
            first = threading.Thread(target=board_read.read, args=(self.root,))
            first.start()
            begun.wait(5)
            board_read.forget(self.root)  # a person's POST, while the read is being made
            release.set()
            first.join()
            board_read.read(self.root)
        self.assertEqual(len(self.made), 2, "the read begun before the action was not kept")

    def test_a_read_that_fails_is_not_kept(self) -> None:
        calls = []

        def broken(root: Path) -> board_read.Read:
            calls.append(root)
            raise OSError("a log went away mid-read")
        with mock.patch.object(board_read, "fold", broken):
            for _ in range(2):
                with self.assertRaises(OSError):
                    board_read.read(self.root)
        self.assertEqual(len(calls), 2)

    def test_two_projects_never_share_a_read(self) -> None:
        other = Path(tempfile.mkdtemp())
        with mock.patch.object(board_read, "fold", lambda root: board_read.Read([{"slice": root.name}], "", {}, {},
                                                                                 {}, [], {})):
            self.assertEqual(board_read.read(self.root).rows[0]["slice"], self.root.name)
            self.assertEqual(board_read.read(other).rows[0]["slice"], other.name)


#: Every route that changes something, each with a body. Most are refused for want of what they act on;
#: refused or done, a person pressed something, and the next poll reads afresh.
ROUTES = ("/tell", "/talk/say", "/talk/steer", "/talk/interrupt", "/talk/again", "/talk/all", "/dismiss", "/read",
          "/decisions/read", "/decisions/confirm", "/need", "/ring", "/set", "/attach", "/cast-off", "/stop",
          "/draw", "/draft", "/model", "/launch", "/intake", "/storyboard", "/feedback", "/try", "/wheel", "/dial",
          "/remote", "/ci-off", "/console/reset")


class DropTest(BoardTest):
    def test_every_route_that_changes_something_drops_the_kept_read(self) -> None:
        key = str(self.root)
        with mock.patch.object(board_read, "KEEP", 60.0):
            for route in ROUTES:
                with self.subTest(route=route):
                    self.get("/live.json")
                    self.assertIn(key, board_read.KEPT)
                    self.post(route, {})
                    self.assertNotIn(key, board_read.KEPT, f"{route} left the read it acted on kept")


class FromTheFleetTest(BoardTest):
    """A park counts whether or not the fold has a row for its slice."""

    def waiting(self) -> dict:
        return json.loads(self.get("/live.json")[1])["waiting"]

    def test_a_park_with_no_chart_behind_it_is_still_waiting_on_you(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", slice="ORD-01", why="Which owner? It matters."))
        found = self.waiting()
        self.assertEqual(found["count"], 1)
        self.assertTrue(found["holding"][0]["text"].startswith("ORD-01: Which owner?"))

    def test_a_hand_back_with_needs_is_waiting_on_you(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", slice="ORD-01", by="session", message="landed?",
                                    needs=[{"what": "the token in the env file", "by": "person"}]))
        found = self.waiting()
        self.assertEqual(found["count"], 1)
        self.assertIn("the token in the env file", found["holding"][0]["text"])

    def test_a_clearance_script_that_faults_never_reads_as_nothing_waiting(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", slice="ORD-01", why="Which owner?"))
        with mock.patch.object(board_read, "folded", lambda root: ([], "clearance could not be read")):
            found = self.waiting()
        self.assertEqual(found["count"], 1)
        self.assertNotIn('data-waiting-count hidden', self.get("/voyage")[1])

    def test_a_paused_park_and_a_note_are_not(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="fyi"),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="limit", cause="limit",
                             until="2099-01-01T00:00:00Z"))
        self.assertEqual(self.waiting()["count"], 0)

    def test_the_paused_slices_can_still_be_tried_and_a_stream_still_told(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", slice="ORD-01", why="limit", cause="limit",
                                    until="2099-01-01T00:00:00Z"))
        streams = json.loads(self.get("/live.json")[1])["bands"]["streams"]["html"]
        self.assertIn("Try the 1 paused slices now anyway", streams)
        self.assertIn('href="/captain-window?fairway=ORD"', streams, "a stream is told in its captain's window")


class NoReloadTest(BoardTest):
    def test_a_note_landing_moves_a_band_and_never_reloads_the_window(self) -> None:
        """A reload closed every card a person had open, and threw away what they were typing."""
        before = json.loads(self.get("/live.json")[1])["passage"]["shape"]
        self.deck("ORD", logs.entry("told", fairway="ORD", message="a note"),
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="Which owner?"))
        self.assertEqual(json.loads(self.get("/live.json")[1])["passage"]["shape"], before)


class LoginKeptTest(unittest.TestCase):
    def test_the_login_shell_is_asked_again_after_a_few_minutes_and_after_a_read_that_faults(self) -> None:
        from slipwai import shell_environment as shell

        asked = []
        token = shell.KEEP_LOGIN.set(True)
        self.addCleanup(shell.KEEP_LOGIN.reset, token)
        def login(command: str) -> dict[str, str]:
            asked.append(command)
            return {"PATH": "/p"}
        with mock.patch.object(shell, "login_of", login), \
                mock.patch.dict(shell.ANSWERED, clear=True):
            shell.login_environment()
            shell.login_environment()
            self.assertEqual(len(asked), 1)
            for command in shell.ANSWERED:
                shell.ANSWERED[command] = (time.monotonic() - shell.LOGIN_KEPT - 1, {"PATH": "/p"})
            shell.login_environment()
            self.assertEqual(len(asked), 2, "kept a few minutes, not for the board's life")
            with mock.patch.object(board_read, "folded", lambda root: ([], "clearance could not be read")):
                board_read.fold(Path(tempfile.mkdtemp()))
            self.assertEqual(shell.ANSWERED, {}, "a read that faults asks the shell again next time")


if __name__ == "__main__":
    unittest.main()
