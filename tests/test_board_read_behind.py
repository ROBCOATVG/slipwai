"""A kept read past its two seconds answers at once and is made again behind the request (`board_read.read`)."""
from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import board_read


class BehindTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(f"/nowhere/behind-{id(self)}")
        self.made: list[int] = []
        self.gate = threading.Event()

        def fold(_root: Path) -> object:
            self.made.append(1)
            if len(self.made) > 1:
                self.gate.wait(5)
            return len(self.made)

        for patched in (mock.patch.object(board_read, "fold", fold), mock.patch.object(board_read, "KEEP", 0.05)):
            patched.start()
            self.addCleanup(patched.stop)
        self.addCleanup(board_read.forget, self.root)

    def test_a_stale_read_answers_at_once_and_is_made_again_behind(self) -> None:
        self.assertEqual(board_read.read(self.root), 1)
        time.sleep(0.1)
        started = time.monotonic()
        self.assertEqual(board_read.read(self.root), 1, "the kept read, not a wait on a new one")
        self.assertLess(time.monotonic() - started, 0.5)
        self.gate.set()
        for _ in range(50):
            if self.root.as_posix() not in board_read.REMAKING:
                break
            time.sleep(0.02)
        self.assertEqual(board_read.read(self.root), 2, "the read made behind is the next one answered")

    def test_a_person_s_action_is_never_answered_from_before_it(self) -> None:
        self.gate.set()
        self.assertEqual(board_read.read(self.root), 1)
        board_read.forget(self.root)
        self.assertEqual(board_read.read(self.root), 2, "made now, waited on")


if __name__ == "__main__":
    unittest.main()
