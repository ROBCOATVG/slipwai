"""What the fleet counts as waiting on a person. Split from `test_fleet.py` at its budget."""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from test_fleet import Fixture, when

from slipwai import inbox_rows, logs
from slipwai.cli_fleet import lines


class WaitsTest(Fixture):
    def test_a_merge_waiting_on_a_red_trunk_is_paused_and_not_waiting_on_anybody(self) -> None:
        """lean-coffee-club said *waiting on you* for MT2 and MT5 while trunk's CI ran; nobody had anything
        to do, and the harbourmaster asked for both merges again when it went green."""
        self.deck("ORD", logs.entry("parked", fairway="ORD", slice="L01", cause="trunk", waiting="green-trunk",
                                    why="L01: the merge was refused: trunk is red", t=when(3)))
        row = self.board()["inbox"][0]
        self.assertEqual((row["paused"], row["waiting_on"]), ("yes", "the harness"))
        said = "\n".join(lines(self.root))
        self.assertIn("waiting on you: nothing", said)
        self.assertIn("paused, nothing for you to do: 1", said)

    def test_a_question_and_a_park_on_a_person_are_still_waits(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="a note", t=when(9)),
                  logs.entry("parked", fairway="ORD", why="open questions", t=when(5)))
        on_you, resting, notes = inbox_rows.inbox_split(self.board()["inbox"])
        self.assertEqual(([row["kind"] for row in on_you], resting, [row["kind"] for row in notes]),
                         (["parked"], [], ["told"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
