"""`slipwai` with nothing after it: the board, opened, rather than a usage message.

The verb that needs no argument should be the one that shows you where you are. A person who has installed
this and knows nothing else types `slipwai`, and what they get is either their fleet or the two things they
can start — not a list of twenty-two verbs they have no way to choose between.

The other half of the slice is the half that is easy to forget: a tool run from a script has nobody to show
a page to. So a command with no terminal on the other end, and one told `--no-browser`, fall back to exactly
the usage message they printed before, and every verb stays reachable as it is today.

It stands up a server, so it is in the Makefile's `SLOW` list and runs in `make verify`.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai.cli import VERBS, main
from slipwai.cli_start import open_board, start_main, will_open
from slipwai.project.harbour import harbour_config


class WhetherToOpenTest(unittest.TestCase):
    """Three ways of asking the same question, because the wrong answer is a script that hangs."""

    def test_a_person_at_a_terminal_gets_the_page(self) -> None:
        self.assertTrue(will_open([], interactive=True))

    def test_nobody_at_the_terminal_gets_the_usage_message_it_always_printed(self) -> None:
        """A tool run from a script has nobody to show a page to, and a server it cannot see is worse
        than the message it expected."""
        self.assertFalse(will_open([], interactive=False))

    def test_no_browser_is_taken_at_its_word_even_at_a_terminal(self) -> None:
        self.assertFalse(will_open(["--no-browser"], interactive=True))


class OpenedBoardTest(unittest.TestCase):
    """What is served, and where the browser is pointed."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.opened: list[str] = []

    def board(self, root: Path) -> str:
        server = open_board(root, "127.0.0.1", 0, open_page=self.opened.append)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/", timeout=5) as answer:
            return answer.read().decode("utf-8")

    def harbour(self) -> Path:
        (self.root / ".slipwai").mkdir()
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")
        return self.root

    def test_the_browser_is_pointed_at_the_port_it_bound(self) -> None:
        """Bound first and opened second: a browser sent to a port nothing is listening on is a blank tab."""
        self.board(self.harbour())
        self.assertEqual(len(self.opened), 1)
        self.assertTrue(self.opened[0].startswith("http://127.0.0.1:"))

    def test_a_harbour_opens_on_its_fleet(self) -> None:
        self.assertIn("Streams", self.board(self.harbour()))

    def test_a_directory_that_is_no_project_opens_the_board_anyway(self) -> None:
        """Empty, with what it *can* do from there. The alternative is a sentence telling somebody to go
        back to the terminal, which is the moment this was supposed to stop being a terminal."""
        said = self.board(self.root)
        self.assertIn("Start a new project", said)
        self.assertIn("Adopt a repository", said)

    def test_what_can_be_started_leads_where_there_is_no_fleet_to_lead_with(self) -> None:
        said = self.board(self.root)
        self.assertLess(said.index("Start a new project"), said.index("Waiting on you"))


class FallbackTest(unittest.TestCase):
    """What a script still gets, unchanged."""

    def run_bare(self, arguments: list[str]) -> str:
        """`slipwai` as a script runs it: `sys.stdin` a pipe, which is what decides this."""
        argv, err = sys.argv, io.StringIO()
        sys.argv = ["slipwai", *arguments]
        try:
            with (mock.patch.object(sys, "stdin", io.StringIO()),
                  self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(err)):
                main()
        finally:
            sys.argv = argv
        self.assertEqual(raised.exception.code, 2)
        return err.getvalue()

    def test_no_terminal_still_says_which_verbs_there_are(self) -> None:
        said = start_main([], interactive=False, open_page=lambda url: None)
        self.assertFalse(said, "it opened a page with nobody to show it to")
        self.assertIn("a verb is required: " + ", ".join(VERBS), self.run_bare([]))

    def test_every_verb_is_still_reachable_exactly_as_it_is_today(self) -> None:
        out = io.StringIO()
        argv = sys.argv
        sys.argv = ["slipwai", "--help"]
        try:
            with self.assertRaises(SystemExit), contextlib.redirect_stdout(out):
                main()
        finally:
            sys.argv = argv
        for verb in VERBS:
            with self.subTest(verb=verb):
                self.assertIn(verb, out.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
