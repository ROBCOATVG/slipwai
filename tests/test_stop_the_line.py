"""A red trunk stops the line: every captain holds and starts nothing new until it is green (phase 25,
`docs/stop-the-line-plan.md`, minimumCD's rule). The harbourmaster's half, sending the trunk mender, is
`test_mender`'s."""
from __future__ import annotations

import re
import unittest

import checkout_packages  # noqa: F401
from captain_fixture import WORKS, Fixture

from slipwai import logs


class StopTheLineTest(Fixture):
    """A red trunk stops the line: nothing new starts until it is green (phase 25, minimumCD's rule)."""

    def test_a_red_trunk_holds_the_fairway_and_starts_nothing(self) -> None:
        self.harbour(logs.entry("trunk-red", harbour=True, commit="a1b2c3d4", job="event model",
                                why="trunk is red at a1b2c3d4"))
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertIn("holds — trunk is red at a1b2c3d4 (event model)", done.stdout)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "claimed"], [], done.stdout)

    def test_the_line_moves_again_once_trunk_is_green(self) -> None:
        self.harbour(logs.entry("trunk-red", harbour=True, commit="a1b2c3d4", job="audit", why="red"),
                     logs.entry("trunk-green", harbour=True, commit="fixed001"))
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertNotIn("holds", done.stdout)
        self.assertEqual([e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"], ["ORD-01"])

    def test_holding_is_not_a_stop(self) -> None:
        """The loop turns again at its interval; a word in `STOPS` would end the captain on a red trunk."""
        self.harbour(logs.entry("trunk-red", harbour=True, commit="a1b2c3d4", job="audit", why="red"))
        done = self.captain("ORD", self.sail(WORKS))
        line = [one for one in done.stdout.splitlines() if "holds" in one][-1]
        text = self.script.read_text(encoding="utf-8")
        stops = re.search(r"^STOPS = \((.*?)\)$", text, re.MULTILINE)
        assert stops is not None
        for word in re.findall(r'"([^"]+)"', stops.group(1)):
            self.assertNotIn(word, line)


if __name__ == "__main__":
    unittest.main()
