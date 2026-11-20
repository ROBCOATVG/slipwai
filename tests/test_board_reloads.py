"""An open board window reloads when a storyboard is rewritten in place, and once, when the writing has ended.

The window read the storyboard's pages by name. A conversation that rebuilt `storyboard.html`, redrew a page
or closed the review's Blockers left every name as it was, so the window went on showing the first drawing
while the stage said the storyboard was ready, and the person could not see it.
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import checkout_packages  # noqa: F401

from slipwai import voyage_page
from slipwai.logs import run_dir
from slipwai.voyage import shape
from slipwai.voyage_live import writing

NAMES = ("storyboard.html", "basket.html", "research.md", "review.md")


class RewrittenInPlaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.mockups = self.root / "specs/001-ordering/mockups"
        self.mockups.mkdir(parents=True)
        for name in NAMES:
            (self.mockups / name).write_text("<title>Mock: Basket</title>", encoding="utf-8")
            os.utime(self.mockups / name, (1_000_000, 1_000_000))

    def said(self) -> str:
        return shape(self.root, [], {}, "001-ordering", False)

    def test_each_file_of_the_stage_written_again_changes_what_the_page_is_made_of(self) -> None:
        seen = self.said()
        for later, name in enumerate(NAMES, 1):
            os.utime(self.mockups / name, (1_000_000 + later, 1_000_000 + later))
            self.assertNotEqual(self.said(), seen, f"{name} was written again")
            seen = self.said()

    def test_nothing_written_leaves_it_alone(self) -> None:
        self.assertEqual(self.said(), self.said())

    def test_a_file_that_is_not_the_stage_s_does_not_reload_the_window(self) -> None:
        seen = self.said()
        (self.mockups / "notes.txt").write_text("a note", encoding="utf-8")
        self.assertEqual(self.said(), seen)


class WritingTest(unittest.TestCase):
    """The reload waits for the turn that is writing to end, in this window or in another."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def board(self, said: dict | None = None) -> SimpleNamespace:
        fitting = SimpleNamespace(said=lambda since=0: said) if said is not None else None
        return SimpleNamespace(root=self.root, fitting=fitting)

    def test_nothing_running_is_nothing_writing(self) -> None:
        self.assertFalse(writing(self.board()))
        self.assertFalse(writing(self.board({"done": True, "talking": True})))

    def test_a_turn_of_conversation_under_way_is_writing_and_a_stage_s_own_run_is_not(self) -> None:
        self.assertTrue(writing(self.board({"done": False, "talking": True})))
        self.assertFalse(writing(self.board({"done": False, "talking": False})),
                         "a stage's own run has a card of its own, which reloads at its start and its end")

    def test_a_drawing_another_window_carries_on_is_writing_the_pages_this_one_shows(self) -> None:
        run_dir(self.root).mkdir(parents=True, exist_ok=True)
        (run_dir(self.root) / "surfaces.pid").write_text(f"{os.getpid()}\n{time.time():.0f}\n", encoding="utf-8")
        self.assertTrue(writing(self.board()))

    def test_the_page_holds_its_reload_while_the_poll_says_so(self) -> None:
        self.assertIn("const held = typing || found.passage.writing;", voyage_page.SCRIPT)
        self.assertIn('"writing": true', voyage_page.payload([], False, False, writing=True))


if __name__ == "__main__":
    unittest.main()
