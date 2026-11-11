"""What the app starts opens no console window of its own, on Windows.

What is proved: a process with no console starts its children with `CREATE_NO_WINDOW`; a child asked for
with flags of its own — a window somebody wants — keeps them; a process that has a console, and every
process on macOS and Linux, is left exactly as it was.
"""
from __future__ import annotations

import subprocess
import unittest
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import app

HIDDEN = 0x08000000


class WindowlessTest(unittest.TestCase):
    def started(self, console: int, **asked: int) -> tuple[bool, dict]:
        """`windowless` under a Windows that has `console`, then a child started; whether it was set, and
        what the child was started with."""
        seen: dict = {}

        def start(self: object, *args: object, **kwargs: object) -> None:
            seen.update(kwargs)

        with mock.patch.object(subprocess.Popen, "__init__", start):
            done = app.windowless("win32", lambda: console)
            begin: Any = subprocess.Popen.__init__
            begin(object(), ["git", "status"], **asked)
        return done, seen

    def test_a_child_of_an_app_with_no_console_opens_no_window(self) -> None:
        """Every agent session opened a terminal that stayed blank, its output going down a pipe to the
        board: it looked stuck, and closing it ended the session."""
        done, seen = self.started(console=0)
        self.assertEqual((done, seen["creationflags"]), (True, HIDDEN))

    def test_a_window_somebody_asked_for_is_still_opened(self) -> None:
        new_console = 0x00000010  # the sign-in, and Open a terminal here
        self.assertEqual(self.started(console=0, creationflags=new_console)[1]["creationflags"], new_console)

    def test_a_process_in_a_terminal_and_every_other_system_are_left_alone(self) -> None:
        done, seen = self.started(console=1)
        self.assertEqual((done, seen), (False, {}), "its children belong in the terminal it was started from")
        start = subprocess.Popen.__init__
        self.assertFalse(app.windowless("darwin"))
        self.assertFalse(app.windowless("linux"))
        self.assertIs(subprocess.Popen.__init__, start)


if __name__ == "__main__":
    unittest.main()
