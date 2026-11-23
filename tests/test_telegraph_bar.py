"""The severity bar, which is not on the telegraph (slipwai#154).

Ringing `full-ahead` for throughput used to raise the bar to HIGH, and a real run stowed forty-six MEDIUM
findings — integrity, privacy and money among them — with nothing on the telegraph saying a ring had done
that. What may merge unfixed is a quality decision and the positions are a throughput decision, so the bar
is its own setting: MEDIUM until a person sets it with `--set bar=…`, kept through every ring, and shown
beside the position.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import telegraph
from slipwai.cli_telegraph import ring, set_one, shown
from slipwai.fleet import pressure
from slipwai.project.harbour import START, harbour_config
from slipwai.settings_card import speed, tune


class BarTest(unittest.TestCase):
    """slipwai#154. Ringing `full-ahead` for throughput raised the bar to HIGH, and a real run stowed forty-six
    MEDIUM findings — integrity, privacy and money among them. What may merge unfixed is a quality decision,
    so the bar is its own setting and no position moves it."""

    def test_no_position_sets_the_bar(self) -> None:
        for position in telegraph.POSITIONS:
            with self.subTest(position=position):
                self.assertNotIn("bar", telegraph.settings(position))

    def test_the_bar_defaults_to_medium(self) -> None:
        self.assertEqual(telegraph.BAR, "MEDIUM")
        self.assertEqual(telegraph.bar_of({}), "MEDIUM")
        self.assertEqual(json.loads(harbour_config())["bar"], "MEDIUM")

    def test_an_unreadable_bar_reads_as_the_default_and_never_as_no_bar(self) -> None:
        self.assertEqual(telegraph.bar_of({"bar": "whatever"}), "MEDIUM")
        self.assertEqual(telegraph.bar_of({"bar": "high"}), "HIGH")

    def test_ringing_keeps_the_bar_a_person_set(self) -> None:
        for position in telegraph.POSITIONS:
            with self.subTest(position=position):
                self.assertEqual(telegraph.applied(position, {"bar": "LOW"})["bar"], "LOW")

    def test_a_set_bar_does_not_read_as_adjusted(self) -> None:
        """It is not a position's number, so a person setting it has not moved off the position."""
        held = {**json.loads(harbour_config()), "bar": "HIGH"}
        self.assertFalse(telegraph.adjusted(START, held))

    def test_the_board_shows_the_bar_beside_the_position_and_in_fine_tune(self) -> None:
        held = {**telegraph.settings("full-ahead"), "position": "full-ahead", "bar": "HIGH"}
        found = pressure(held, [])
        self.assertEqual(found["bar"], "HIGH")
        panel = speed(found, controls=False)
        self.assertIn("Stop a merge at or above: <b>HIGH</b>", panel)
        self.assertIn("no position moves", panel)
        self.assertIn("Stop a merge at or above", tune(held, controls=True))
        self.assertIn('data-number="bar" value="HIGH"', tune(held, controls=True))
        self.assertEqual(pressure({}, [])["bar"], "MEDIUM")

    def test_an_old_file_with_a_position_s_bar_does_not_read_as_adjusted(self) -> None:
        """A harbour.json written when full-ahead set HIGH still reads as full-ahead after the upgrade."""
        held = {**telegraph.settings("full-ahead"), "position": "full-ahead", "bar": "HIGH"}
        self.assertEqual(telegraph.described("full-ahead", held), "full-ahead")


class FileBarTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")

    def held(self) -> dict:
        return json.loads((self.root / "harbour.json").read_text(encoding="utf-8"))

    def test_ringing_full_ahead_leaves_the_bar_at_medium(self) -> None:
        ring(self.root, "full-ahead")
        self.assertEqual(self.held()["bar"], "MEDIUM")
        ring(self.root, "stop")
        self.assertEqual(self.held()["bar"], "MEDIUM")

    def test_set_bar_changes_the_bar_and_a_ring_keeps_it(self) -> None:
        said = set_one(self.root, ["bar=high"])
        self.assertEqual(self.held()["bar"], "HIGH")
        self.assertIn("bar = HIGH", "\n".join(said))
        self.assertEqual(said[0], f"telegraph: {START}")
        ring(self.root, "dead-slow")
        self.assertEqual(self.held()["bar"], "HIGH")

    def test_the_bar_is_shown_beside_the_position(self) -> None:
        lines = shown(self.held())
        self.assertEqual(lines[1].split()[:2], ["bar", "MEDIUM"])
        self.assertIn("no position moves", lines[1])

    def test_a_file_with_no_bar_is_shown_at_the_default(self) -> None:
        held = self.held()
        del held["bar"]
        self.assertEqual(shown(held)[1].split()[:2], ["bar", "MEDIUM"])
