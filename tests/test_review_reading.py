"""What the drawing stage found: the two lines it declares, which decide, and its findings, which are only shown.

The fixtures under `tests/fixtures/drawings/` are cut from drawings real projects wrote, names neutralised:
findings a heading each under `## Blockers` in a `gaps.md`, a `review-<surface>.md` a page with a summary
line and bold numbered items, and a `review.md` with a counts table and findings under a heading per surface.
None of those shapes decides anything any more; the stage's own `Blockers open:` and `Questions open:` lines do.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.review_reading import gate, reading, surfaces_check

DRAWINGS = Path(__file__).resolve().parent / "fixtures" / "drawings"


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.home = self.root / "specs/001-boats/mockups"
        self.home.mkdir(parents=True)

    def write(self, name: str, text: str) -> None:
        (self.home / name).parent.mkdir(parents=True, exist_ok=True)
        (self.home / name).write_text(text, encoding="utf-8")

    def copy(self, shape: str) -> None:
        for one in (DRAWINGS / shape).iterdir():
            shutil.copy(one, self.home / one.name)


class GateTest(Fixture):
    def test_the_gate_reads_the_stage_s_own_two_lines_and_nothing_else(self) -> None:
        self.copy("heading-findings")  # three Blockers in prose
        self.write("research.md", "# Research\n\nBlockers open: 0\nQuestions open: 0\n\n## Questions\n- Who pays?\n")
        self.assertEqual(gate(self.root, "001-boats"), "", "the stage says nothing is open; the prose decides nothing")
        self.write("research.md", "Blockers open: 2\nQuestions open: 1\n")
        self.assertEqual(gate(self.root, "001-boats"), "the drawing says 2 Blockers are open; 1 question only you "
                                                       "can answer is open")

    def test_a_drawing_without_the_lines_is_stopped_and_told_which_line_is_missing(self) -> None:
        self.copy("per-surface")
        self.assertIn("does not say `Blockers open: N` and `Questions open: N`", gate(self.root, "001-boats"))
        self.write("research.md", "Questions open: 0\n**Blockers open:** 0\n")
        self.assertIn("does not say `Blockers open: N` on a line", gate(self.root, "001-boats"),
                      "the fixed form only: a bolded line is not the declaration")
        self.write("research.md", "Blockers open: 0\nBlockers open: 4\nQuestions open: 0\n")
        self.assertIn("`Blockers open: N`", gate(self.root, "001-boats"), "said twice is not said")
        self.assertIn("does not declare", surfaces_check(self.root, "001-boats"))
        self.write("research.md", "Blockers open: 0\nQuestions open: 0\n")
        self.assertEqual(surfaces_check(self.root, "001-boats"), "")


class PanelTest(Fixture):
    def test_findings_a_heading_each_under_a_severity_are_counted_once_each(self) -> None:
        self.copy("heading-findings")
        found = reading(self.root, "001-boats")
        self.assertEqual([one.text[:30] for one in found.blockers],
                         ['G1 — "Interview held" has no s', "G2 — Consent refused has no st",
                          "G3 — The access list defaults "])
        self.assertEqual(sorted({one.severity for one in found.findings}), ["blocker", "nice", "should"])
        self.assertEqual(len(found.findings), 5, "a settled one is not listed, nor any finding's detail bullets")

    def test_a_page_per_surface_and_a_counts_table_are_both_read(self) -> None:
        self.copy("per-surface")
        found = reading(self.root, "001-boats")
        self.assertEqual(found.files, ["review-night.md", "review-tables.md"])
        self.assertEqual([one.text[:20] for one in found.blockers], ["TB-1. Two tables can"])
        self.assertEqual(sum(one.severity == "should" for one in found.findings), 2, "and `- None.` is none")
        shutil.rmtree(self.home)
        self.home.mkdir()
        self.copy("counts-table")
        found = reading(self.root, "001-boats")
        self.assertEqual([(one.where[:7], one.text[:24]) for one in found.blockers],
                         [("Booking", "Nothing says what happen"), ("Booking", "No error state for a boa"),
                          ("Calenda", "Two bookings can overlap")])
        self.assertEqual((found.blockers_open, found.questions_open), (3, 2))
        self.assertEqual([one[:16] for one in found.questions], ["Who can cancel? ", "More than one bo"])

    def test_questions_are_found_however_their_heading_is_written_and_none_is_none(self) -> None:
        self.write("research.md", "## Unresolved questions\n\n### Q1 — Who cancels?\nprose\n\n### Q2 — Paid? — "
                                  "answered (D2)\n\n**Questions**\n- Is it free?\n\n## Questions\n_None._\n")
        self.assertEqual(reading(self.root, "001-boats").questions, ["Q1 — Who cancels?", "Is it free?"])
        self.write("research.md", "## Questions\n- None\n- Whether it is resolved is up to you?\n")
        self.assertEqual(reading(self.root, "001-boats").questions, ["Whether it is resolved is up to you?"],
                         "a question with the word in it is still open")


class OddFilesTest(Fixture):
    def test_a_pipe_a_link_out_or_an_endless_line_is_not_what_holds_a_request(self) -> None:
        outside = Path(tempfile.mkdtemp()) / "o.md"
        outside.write_text("- [Blocker] from outside the project\n", encoding="utf-8")
        os.symlink(outside, self.home / "review.md")
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.home / "gaps.md")
        self.write("research.md", "Blockers open: 0\nQuestions open: 0\n" + "9" * 60000 + " Blockers\n")
        began = time.monotonic()
        found = reading(self.root, "001-boats")
        self.assertEqual(gate(self.root, "001-boats"), "")
        self.assertLess(time.monotonic() - began, 2.0)
        self.assertEqual(found.findings, [], "nothing read through the link or the pipe")


if __name__ == "__main__":
    unittest.main()
