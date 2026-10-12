"""One page whatever started it: the board, generation and adoption as tabs of one server on one port.

Before this slice there were three documents on one server and three ways to arrive at one of them, which is
the shape the plan calls three commands that each open something. The two things it is held to are here: the
tab bar is on every tab and marks the one you are on, and a verb run while a board is already serving joins
that board rather than binding a second — the failure that shape has is two servers on two ports, each sure
it is the board.

It stands up servers, so it is in the Makefile's `SLOW` list.
"""
from __future__ import annotations

import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.bridge import serve
from slipwai.bridge_page import read_only
from slipwai.cli_fleet import config
from slipwai.cli_start import open_board, running
from slipwai.fleet import board
from slipwai.page_shell import TABS, tabs
from slipwai.project.harbour import harbour_config


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")
        self.opened: list[str] = []
        self.server = serve(self.root, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)

    def get(self, path: str) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10) as answer:
            return answer.read().decode("utf-8")


class OnePageTest(Fixture):
    """Three places, one page: whichever you arrive at, the other two are a click away."""

    def test_every_tab_carries_every_other(self) -> None:
        for where, _ in TABS:
            said = self.get(where)
            for other, name in TABS:
                with self.subTest(on=where, link=other):
                    self.assertIn(f'href="{other}"', said)
                    self.assertIn(name, said)

    def test_the_tab_you_are_on_says_so(self) -> None:
        for where, name in TABS:
            with self.subTest(tab=where):
                self.assertIn('aria-current="page"', self.get(where))
                self.assertIn(f'aria-current="page">{name}', self.get(where))

    def test_the_published_copy_has_no_tabs_because_it_is_one_file(self) -> None:
        """A link that worked served and 404'd published would be the two copies disagreeing."""
        said = read_only(board(self.root, config(self.root)), config(self.root))
        self.assertNotIn('class="tabs"', said)

    def test_a_tab_that_is_not_one_still_says_what_there_is(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as refused:
            self.get("/nowhere")
        with refused.exception as answer:
            self.assertEqual(answer.code, 404)


class OneServerTest(Fixture):
    """A verb run while a board is serving joins it. Two boards on two ports is the failure."""

    def test_a_board_already_serving_is_found(self) -> None:
        self.assertTrue(running("127.0.0.1", self.port))

    def test_a_port_with_nothing_on_it_is_not_a_board(self) -> None:
        spare = serve(self.root, "127.0.0.1", 0)
        port = spare.server_address[1]
        spare.server_close()
        self.assertFalse(running("127.0.0.1", port))

    def test_opening_the_board_again_starts_no_second_one(self) -> None:
        second = open_board(self.root, "127.0.0.1", self.port, open_page=self.opened.append)
        self.assertIsNone(second, "a second server was bound while one was already serving")
        self.assertEqual(self.opened, [f"http://127.0.0.1:{self.port}/"])

    def test_the_browser_is_still_pointed_at_the_tab_that_was_asked_for(self) -> None:
        open_board(self.root, "127.0.0.1", self.port, open_page=self.opened.append, at="/adopt")
        self.assertEqual(self.opened, [f"http://127.0.0.1:{self.port}/adopt"])


class TabBarTest(unittest.TestCase):
    def test_the_bar_is_built_from_the_tabs_and_not_written_out(self) -> None:
        said = tabs("/generate")
        self.assertEqual(said.count("<a "), len(TABS))

    def test_a_page_that_is_no_tab_marks_none_of_them(self) -> None:
        self.assertNotIn("aria-current", tabs("/nowhere"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
