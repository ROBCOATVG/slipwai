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

from slipwai import board_settings, brief_check, design_docs, handover
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
                        mock.patch.object(handover, "agent_chosen", return_value=stand_in),
                        # The catalogue's own default frontend, as a checkout with a language shipped answers it.
                        mock.patch.object(handover, "frontend_menu",
                                          return_value=(["none", "react-vite"], "react-vite", {}))):
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
        with mock.patch("slipwai.handover.extensions_offered", return_value=[("codegraph", "CodeGraph", "an index"),
                                                                           ("uipro", "UI/UX Pro Max", "")]):
            self.assertEqual(handover.answers(self.folder)["extensions"], "codegraph,uipro",
                             "every extension this machine has, ticked")
        lines = handover.said(held)
        self.assertIn("A browser app, drawn from the brief's 3 surfaces.", lines)
        self.assertTrue(any(line.startswith("For staff, an annoyance when it is down") for line in lines), lines)
        self.assertIn("Signed in by the people who work here, and nobody else.", lines)
        self.assertTrue(any("One service, bookings, in python with a real store in one file" in line for line in lines))
        self.assertTrue(any(line.startswith("Built with stand-in") for line in lines), lines)

    def where(self, said: str) -> None:
        """The brief's *Who runs it*, with a third line saying where."""
        prd = self.folder / "prd.md"
        text = prd.read_text(encoding="utf-8")
        marker = "- When it is down:"
        at = text.index("\n", text.index(marker)) + 1
        prd.write_text(text[:at] + f"- Where it runs: {said}\n" + text[at:], encoding="utf-8")

    def test_a_brief_that_says_aws_starts_there_where_this_machine_can_reach_it(self) -> None:
        """Every brief was generated for the laptop: the target was always `none`, so the shape was dropped (#47)."""
        self.where("in our AWS account")
        with mock.patch.object(handover, "short_of", return_value=[]):
            held = handover.answers(self.folder)
            lines = handover.said(held)
        self.assertEqual(held["target"], "aws")
        self.assertEqual(held["who"], "staff", "who signs in is still the brief's")
        self.assertTrue(any(line.endswith("in your AWS account.") for line in lines), lines)
        self.assertFalse(any("This machine cannot start there" in line for line in lines), lines)

    def test_a_place_this_machine_cannot_reach_starts_on_the_laptop_and_says_what_it_needs(self) -> None:
        self.where("in our AWS account")
        with mock.patch.object(handover, "short_of", return_value=["the AWS CLI", "OpenTofu 1.12"]):
            held = handover.answers(self.folder)
            lines = handover.said(held)
        self.assertEqual(held["target"], "none")
        self.assertIn("You said AWS. This machine cannot start there yet: it needs the AWS CLI and OpenTofu 1.12. "
                      "Starting on this machine for now.", lines)

    def test_a_cloud_whose_package_is_not_installed_is_still_the_place_said_and_says_so(self) -> None:
        """Read off the installed targets alone, a brief naming a cloud this machine had no package for read
        as not said, and started on the laptop without a word about why."""
        self.where("in our AWS account")
        targets = {key: entry for key, entry in brief_check.CATALOG["targets"].items() if key != "aws"}
        loaded = {key: one for key, one in handover.loaded().items() if key != "aws"}
        with mock.patch.dict(brief_check.CATALOG, {"targets": targets}), \
                mock.patch.object(handover, "loaded", return_value=loaded):
            held = handover.answers(self.folder)
            lines = handover.said(held)
        self.assertEqual(held["target"], "none")
        self.assertTrue(any(line.startswith("You said AWS. This machine cannot start there yet: it needs")
                            and "the aws target" in line for line in lines), lines)

    def test_another_team_s_platform_is_the_internal_tool_for_a_staff_screen(self) -> None:
        self.where("on a platform another team runs")
        with mock.patch.object(handover, "short_of", return_value=[]):
            self.assertEqual(handover.destination(
                {"runs_on": "platform", "used_by": "staff"}, True)[0], "internal-tool")
            self.assertEqual(handover.destination(
                {"runs_on": "platform", "used_by": "customers"}, True)[0], "existing-platform-service")
            self.assertEqual(handover.answers(self.folder)["target"], "existing")
        self.assertEqual(handover.destination({"runs_on": "nowhere"}, True), ("laptop-trial", ""))
        self.assertEqual(handover.destination({}, True), ("laptop-trial", ""), "not said is today's start")

    def test_the_laptop_says_what_it_will_be_when_it_goes_live_not_that_it_is_deployed(self) -> None:
        """The page said "the full stack, with a staging environment" and then "deployed nowhere"."""
        lines = handover.said(handover.answers(self.folder))
        self.assertIn("For staff, an annoyance when it is down: when it goes live it will be one environment.", lines)

    def test_the_prototype_beside_the_brief_is_carried_in_and_said(self) -> None:
        """The page a person played was left behind at hand-over; the builder saw state inventories in words."""
        played = self.folder.parent / "prototype" / "index.html"
        played.parent.mkdir()
        played.write_text("<title>Play</title><button>Book</button>", encoding="utf-8")
        self.assertTrue(any(line.endswith("and the prototype you played, which the surfaces follow.")
                            for line in handover.said(handover.answers(self.folder))))
        landed = design_docs.carried(self.folder)
        self.assertEqual(landed, self.folder / "prototype" / "index.html")
        assert landed is not None
        self.assertEqual(landed.read_text(encoding="utf-8"), played.read_text(encoding="utf-8"))
        self.assertEqual(design_docs.carried(self.folder), landed, "carried twice is still the one copy")
        self.assertIn(landed, design_docs.briefed(self.folder)[1], "it travels with the rest of the brief")

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
        with mock.patch("slipwai.interview_form.SKETCHES", self.folder.parent.parent):
            self.assertIn('href="/brief/read?sketch=club-boat-bookings">Read the brief</a>',
                          page({"brief": str(self.folder)}, root=self.folder.parent))
        self.assertNotIn("Read the brief", shown, "a brief that is not a sketch's is not read from here")
        self.assertIn('<input type="hidden" name="frontend" value="react-vite">', shown)
        self.assertIn('<input type="hidden" name="who" value="staff">', shown)
        self.assertNotIn("Delivery foundation", shown, "no question is asked on the hand-over's page")
        self.assertNotIn("Dev tooling", shown, "a machine with no extension installed is asked nothing")
        offered = [("codegraph", "CodeGraph", "an index"), ("uipro", "UI/UX Pro Max", "")]
        with mock.patch("slipwai.handover.extensions_offered", return_value=offered), \
                mock.patch("slipwai.interview_page.extensions_offered", return_value=offered):
            ticked = page({"brief": str(self.folder)}, root=self.folder.parent)
        self.assertIn("Dev tooling", ticked, "the one choice the brief cannot settle stays on the page")
        self.assertIn('name="extensions" value="codegraph" checked', ticked)
        self.assertIn('name="extensions" value="uipro" checked', ticked)
        self.assertNotIn('<input type="hidden" name="extensions"', ticked, "the boxes are the answer, once")
        full = page({"brief": str(self.folder), "edit": "1"}, root=self.folder.parent)
        self.assertIn("Delivery foundation", full)
        self.assertIn('value="club-boat-bookings"', full)
        self.assertIn('value="bookings"', full)
        self.assertNotIn("Make it</button>", full)


if __name__ == "__main__":
    unittest.main()
