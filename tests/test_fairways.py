"""Fairways: one bounded context's slices, held by one at a time, and read off the chart.

Issue #30's work, renamed as it lands. Version 1 called this a workstream and read it from a column
somebody typed into the split, which is a second place for a fact the chart already holds — and the one
that is wrong is always the one somebody typed. So the split's table is read from `chart.yaml`, and what is
held here is that the prose says so, that a session can take one fairway or every free one, and that merge
order is within a fairway rather than across.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.project import commands

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "assets/toolkit/skills/story-splitting/SKILL.md"


def flat(text: str) -> str:
    return " ".join(text.split())


def page(event: bool) -> str:
    """`commands/sail.md` as a session reads it: the rules moved into the asset in slice 16.5, so what
    they say is asked of the page rather than of the function that used to hold the words."""
    return flat(commands.sail_command(event=event, apps=[], target="none"))


class FairwaySectionTest(unittest.TestCase):
    def section(self) -> str:
        return page(event=True)

    def test_a_fairway_is_one_context_held_by_one_at_a_time(self) -> None:
        self.assertIn("one bounded context's slices, in split order, held by one at a time", self.section())

    def test_two_fairways_share_nothing_but_marks(self) -> None:
        """Which is what lets one merge and demo without waiting on the other."""
        self.assertIn("share nothing but **marks**", self.section())

    def test_the_table_is_read_from_the_chart_and_never_typed_beside_it(self) -> None:
        """A second place to say which fairway a slice is in is a second place for it to be wrong."""
        section = self.section()
        self.assertIn("read from the chart**, never typed", section)
        self.assertIn("the one that is wrong is always the one somebody typed", section)

    def test_a_single_context_project_sees_no_change(self) -> None:
        self.assertIn("one context has one fairway, and nothing in this section changes for it",
                      self.section())

    def test_held_by_routes_and_the_branch_still_locks(self) -> None:
        """Two sessions on one fairway are two claims, and the mutex is where it always was."""
        section = self.section()
        self.assertIn("routing, not a lock", section)
        self.assertIn("two claims", section)

    def test_merges_are_ordered_within_a_fairway_and_not_across(self) -> None:
        section = self.section()
        self.assertIn("ordered within a fairway and not across", section)
        self.assertIn("whichever finished first", section)

    def test_a_conflict_in_a_mark_stops_both_rather_than_being_resolved_in_a_branch(self) -> None:
        self.assertIn("stop both fairways for the host, never resolve it in a branch", self.section())

    def test_the_boundary_is_held_by_the_scope_gate_rather_than_remembered(self) -> None:
        self.assertIn("check-slice-scope` refuses a branch that touches a path another fairway owns",
                      self.section())


class ReadySetTest(unittest.TestCase):
    def test_a_fairway_narrows_the_ready_set_and_names_what_it_left(self) -> None:
        for event in (True, False):
            with self.subTest(event=event):
                rules = page(event)
                self.assertIn("A fairway narrows all of the above", rules)
                self.assertIn("named as *another fairway's* and left", rules)

    def test_with_no_fairway_given_a_session_takes_every_free_one(self) -> None:
        rules = page(event=True)
        self.assertIn("the ready slices of every fairway nobody holds", rules)
        self.assertIn("naming its slices as *held*", rules)


class DriveArgumentTest(unittest.TestCase):
    def test_drive_takes_a_fairway(self) -> None:
        written = commands.sail_command(event=True, apps=[], target="aws")
        self.assertIn("argument-hint: [slice-id-or-feature] [fairway=<name>]", written)

    def test_the_fairways_section_reaches_the_page_a_session_reads(self) -> None:
        written = commands.sail_command(event=False, apps=[], target="none")
        self.assertIn("### Fairways", written)


class SplitTableTest(unittest.TestCase):
    def test_the_split_names_the_table_and_where_it_comes_from(self) -> None:
        split = flat(SPLIT.read_text(encoding="utf-8"))
        self.assertIn("## Fairways", split)
        self.assertIn("Read from `specs/<feature>/chart.yaml`'s `fairways` block, never typed beside it",
                      split)

    def test_a_slice_is_never_in_two_fairways(self) -> None:
        split = flat(SPLIT.read_text(encoding="utf-8"))
        self.assertIn("never one slice in two fairways", split)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
