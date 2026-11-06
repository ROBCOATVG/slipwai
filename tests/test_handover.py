"""Hand-over from a brief: the start page settles what the brief settled and says so before asking anything.

What is proved: the project's name comes from the sketch, a browser app from the brief's surfaces, who signs
in from *Who runs it*, the service's purpose from the brief's first paragraph, the builder's choices from
the smallest start; the page from a brief is a few lines with Make it and Change something; and Change
something is the whole form, prefilled.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import board_settings, handover
from slipwai.board_settings import Launch
from slipwai.interview_form import from_query, page

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "brief"


class HandoverTest(unittest.TestCase):
    def setUp(self) -> None:
        area = Path(tempfile.mkdtemp())
        self.folder = area / "sketches" / "club-boat-bookings" / "brief"
        shutil.copytree(FIXTURE, self.folder)
        stand_in = Launch("stand-in", "Stand-in", ("python3",), "a script")
        for patched in (mock.patch.object(board_settings, "SETTINGS", area / "board.json"),
                        mock.patch.object(handover, "agent_chosen", return_value=stand_in)):
            patched.start()
            self.addCleanup(patched.stop)

    def test_what_the_brief_settles_is_answered_and_the_rest_is_the_smallest_start(self) -> None:
        held = handover.answers(self.folder)
        self.assertEqual(held["name"], "club-boat-bookings")
        self.assertEqual(held["service-name"], "bookings")
        self.assertEqual(held["frontend"], "react-vite", "the brief drew surfaces")
        self.assertEqual(held["who"], "staff", "from Who runs it")
        self.assertTrue(held["purpose"].startswith("A member books one of the club's boats"))
        self.assertEqual((held["language"], held["persistence"], held["write-model"], held["target"]),
                         ("python", "sqlite", "events", "none"))
        self.assertEqual(held["init"], "stand-in")
        self.assertEqual(held["brief"], str(self.folder))
        lines = handover.said(held)
        self.assertIn("A browser app, drawn from the brief's 3 surfaces.", lines)
        self.assertTrue(any(line.startswith("For staff, an annoyance when it is down") for line in lines), lines)
        self.assertIn("Signed in by the people who work here, and nobody else.", lines)
        self.assertTrue(any("One service, bookings, in python with a real store in one file" in line for line in lines))
        self.assertTrue(any(line.startswith("Built with stand-in") for line in lines), lines)

    def test_a_brief_with_no_surfaces_and_no_lines_takes_the_plain_defaults(self) -> None:
        bare = Path(tempfile.mkdtemp()) / "notes"
        bare.mkdir()
        (bare / "prd.md").write_text("# Thing\n\nIt does a thing.\n", encoding="utf-8")
        held = handover.answers(bare)
        self.assertEqual((held["name"], held["service-name"], held["frontend"], held["who"]),
                         ("notes", "notes", "none", "everyone"))
        self.assertIn("No browser app: the brief draws no surfaces.", handover.said(held))
        self.assertTrue(any(line.startswith("Who runs it is not said yet") for line in handover.said(held)))

    def test_the_page_from_a_brief_is_a_confirmation_and_change_something_is_the_form_prefilled(self) -> None:
        self.assertEqual(from_query(f"brief={self.folder}"), {"brief": str(self.folder)})
        self.assertEqual(from_query(f"brief={self.folder}&edit=1"), {"brief": str(self.folder), "edit": "1"})
        shown = page({"brief": str(self.folder)}, root=self.folder.parent)
        self.assertIn("<h2>Make club-boat-bookings</h2>", shown)
        self.assertIn('id="generate">Make it</button>', shown)
        self.assertIn("Change something", shown)
        self.assertIn('<input type="hidden" name="frontend" value="react-vite">', shown)
        self.assertIn('<input type="hidden" name="who" value="staff">', shown)
        self.assertNotIn("Delivery foundation", shown, "no question is asked on the hand-over's page")
        full = page({"brief": str(self.folder), "edit": "1"}, root=self.folder.parent)
        self.assertIn("Delivery foundation", full)
        self.assertIn('value="club-boat-bookings"', full)
        self.assertIn('value="bookings"', full)
        self.assertNotIn("Make it</button>", full)


if __name__ == "__main__":
    unittest.main()
