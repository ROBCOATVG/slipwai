"""The machine's own folder chooser, which the board opens because a browser may not.

A web page is never told where anything is on the disk — `<input type="file">` hands over contents,
`webkitdirectory` hands over names relative to what was picked, the File System Access API hands over a
handle. The board is on the machine the folder is on, so it asks the operating system instead. What is
held here is the command each platform is asked with, and that every way of saying *no folder* — a
cancel, a machine with no chooser, a path that is not a directory — comes back the same way.
"""
from __future__ import annotations

import contextlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai.folder_choice import PROMPT, asking, chosen


class ran(contextlib.ExitStack):  # noqa: N801 — it reads as the verb it is at every call site
    """`subprocess.run` answering with that, so these hold what the board does with an answer rather than
    re-testing somebody else's dialog.

    The login environment is stubbed with it, and not for tidiness: `import subprocess` is one module
    object, so patching `folder_choice.subprocess.run` patches it for `shell_environment` too — which
    runs a real shell and reads bytes back, and met a string meant for the dialog.
    """

    def __init__(self, stdout: str = "", code: int = 0) -> None:
        super().__init__()
        self.said = subprocess.CompletedProcess([], code, stdout, "")
        #: What the chooser was actually asked, which is the half worth holding.
        self.asked: list[str] = []

    def __enter__(self) -> ran:
        super().__enter__()
        self.enter_context(mock.patch("slipwai.folder_choice.login_environment", lambda: {}))
        self.enter_context(mock.patch("slipwai.folder_choice.subprocess.run", self.answer))
        return self

    def answer(self, command: list[str], **_kw: object) -> subprocess.CompletedProcess:
        self.asked = command
        return self.said


class CommandTest(unittest.TestCase):
    def test_each_platform_is_asked_with_the_chooser_it_already_has(self) -> None:
        here = Path(tempfile.mkdtemp())
        with mock.patch.object(sys, "platform", "darwin"):
            said = asking(here)
            self.assertEqual(said[0], "osascript")
            self.assertIn("choose folder", said[-1])
            self.assertIn(str(here), said[-1])
        with mock.patch.object(sys, "platform", "linux"), \
                mock.patch("slipwai.folder_choice.which", lambda one: one if one == "zenity" else None):
            self.assertEqual(asking(here)[:3], ["zenity", "--file-selection", "--directory"])
        with mock.patch.object(sys, "platform", "linux"), \
                mock.patch("slipwai.folder_choice.which", lambda one: one if one == "kdialog" else None):
            self.assertEqual(asking(here)[0], "kdialog")

    def test_a_desktop_with_no_chooser_on_it_asks_with_nothing(self) -> None:
        """Which is not a fault: the field is a path somebody can type, and always was."""
        with mock.patch.object(sys, "platform", "linux"), \
                mock.patch("slipwai.folder_choice.which", lambda _one: None):
            self.assertEqual(asking(Path(tempfile.mkdtemp())), [])
            self.assertEqual(chosen(Path(tempfile.mkdtemp())), "")

    def test_the_dialog_opens_where_the_field_already_pointed(self) -> None:
        here = Path(tempfile.mkdtemp())
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertIn(str(here), asking(here)[-1])
            self.assertIn(PROMPT, asking(here)[-1])
        gone = here / "not-here"
        with mock.patch.object(sys, "platform", "darwin"), ran(str(here)) as asked:
            chosen(gone)
            self.assertNotIn(str(gone), asked.asked[-1], "a path that is not there is not where it opens")
            self.assertIn(str(Path.home()), asked.asked[-1], "it opens at home instead")


class AnswerTest(unittest.TestCase):
    def test_the_folder_picked_is_the_answer(self) -> None:
        here = Path(tempfile.mkdtemp())
        with ran(f"{here}\n"):
            self.assertEqual(chosen(Path(tempfile.mkdtemp())), str(here))

    def test_every_way_of_saying_no_folder_says_it_the_same_way(self) -> None:
        """A cancel, a chooser that could not start, a path that is not a directory. Each means *no
        folder*, and the field keeps whatever it already held."""
        for stdout, code, why in (("", 1, "cancelled"), ("", 0, "nothing said"),
                                  ("/not/a/real/place\n", 0, "not a directory")):
            with self.subTest(why=why), ran(stdout, code):
                self.assertEqual(chosen(Path(tempfile.mkdtemp())), "")

    def test_a_chooser_that_will_not_run_is_not_a_traceback(self) -> None:
        for fault in (OSError("no such thing"), subprocess.TimeoutExpired([], 1)):
            with self.subTest(fault=type(fault).__name__), \
                    mock.patch("slipwai.folder_choice.login_environment", lambda: {}), \
                    mock.patch("slipwai.folder_choice.subprocess.run", side_effect=fault):
                self.assertEqual(chosen(Path(tempfile.mkdtemp())), "")


class RouteTest(BoardTest):
    def test_the_board_asks_the_machine_and_hands_back_where_it_landed(self) -> None:
        here = Path(tempfile.mkdtemp())
        with ran(f"{here}\n"):
            self.assertEqual(self.post("/choose", {"start": str(self.root)}), (200, str(here)))

    def test_a_cancel_is_an_answer_rather_than_a_refusal(self) -> None:
        """200 and empty: the field keeps what it had. A 400 would be the page saying something went
        wrong when a person simply changed their mind."""
        with ran("", 1):
            self.assertEqual(self.post("/choose", {"start": str(self.root)}), (200, ""))

    def test_the_form_carries_the_button_that_asks(self) -> None:
        self.assertIn('data-choose="brief"', self.get("/generate")[1])


if __name__ == "__main__":
    unittest.main()
