"""`./init`, run in a project that has just been made — in a terminal, and in the background for the board.

No real `./init` runs here and none ever should: the real one installs Spec Kit over the network, and a
suite that reached for it would be a suite nobody can run on a train. What is under test is the part this
keel owns — the command it builds, the lines it says, and the tail the board reads while a child is running
— so the child here is a four-line shell script that says what it was told to say.
"""
from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.init_run import DECLINED, Fitting, command, ended, start


def project(says: list[str], code: int = 0) -> Path:
    """A directory with an `init` in it that says those lines and exits with that status."""
    root = Path(tempfile.mkdtemp())
    script = root / "init"
    said = "\n".join(f"echo '{line}'" for line in says)
    script.write_text(f"#!/bin/sh\n{said}\nexit {code}\n", encoding="utf-8")
    script.chmod(0o755)
    return root


def finished(fitting: Fitting, seconds: float = 20.0) -> dict:
    """What it said, once it has stopped. Polled, because the board polls — and bounded, because a test that
    hangs on a child that never ends is a test nobody can read the failure of."""
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        said = fitting.said()
        if said["done"]:
            return said
        time.sleep(0.05)
    raise AssertionError(f"`./init` was still running after {seconds}s: {fitting.said()['lines']}")


class CommandTest(unittest.TestCase):
    def test_the_agent_is_named_where_somebody_named_one(self) -> None:
        self.assertEqual(command("claude"), ["./init", "--integration", "claude"])

    def test_unnamed_it_keeps_spec_kit_s_own_question(self) -> None:
        """Which is right in a terminal, where there is somebody to answer it."""
        self.assertEqual(command(), ["./init"])

    def test_a_failure_says_the_project_is_written_either_way(self) -> None:
        said = ended(2, "claude")
        self.assertIn("exited 2", said)
        self.assertIn("written and committed either way", said)


class BackgroundTest(unittest.TestCase):
    """The board's face: a child that outlives the request, read by polling."""

    def test_every_line_the_child_said_is_tailed_in_order(self) -> None:
        fitting = start(project(["first", "second", "third"]), "claude")
        lines = finished(fitting)["lines"]
        self.assertEqual([line for line in lines if line in ("first", "second", "third")],
                         ["first", "second", "third"])

    def test_a_poll_is_answered_with_what_was_said_after_the_lines_it_has(self) -> None:
        """The whole of the tail's contract: the page never shows a line twice and never misses one."""
        fitting = start(project(["one", "two"]), "claude")
        said = finished(fitting)
        self.assertEqual(said["at"], len(said["lines"]))
        self.assertEqual(fitting.said(said["at"])["lines"], [])
        self.assertEqual(fitting.said(said["at"] - 1)["lines"], said["lines"][-1:])

    def test_what_it_exited_with_is_what_the_board_is_told(self) -> None:
        fitting = start(project(["trying"], code=3), "claude")
        said = finished(fitting)
        self.assertEqual(said["code"], 3)
        self.assertIn("exited 3", said["lines"][-1])

    def test_an_init_that_cannot_be_run_is_a_line_and_not_a_silence(self) -> None:
        """A board that showed nothing where the child never started would be a board hiding the answer."""
        said = finished(start(Path(tempfile.mkdtemp()), "claude"))
        self.assertTrue(said["done"])
        self.assertNotEqual(said["code"], 0)
        self.assertIn("could not be run here", said["lines"][-1])

    def test_declining_is_a_finished_run_that_says_what_the_next_step_is(self) -> None:
        """The board still lands in the project; what it does not do is start anything in it."""
        said = finished(start(project(["never run"]), None), seconds=2.0)
        self.assertEqual(said["code"], 0)
        self.assertEqual(said["lines"][-1], DECLINED)

    def test_what_generate_said_is_the_head_of_the_same_receipt(self) -> None:
        """One card, not two: where the project went and what is happening in it are one person's question."""
        said = finished(start(project(["ready"]), "claude", ["created: /somewhere/demo"]))
        self.assertEqual(said["lines"][0], "created: /somewhere/demo")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
