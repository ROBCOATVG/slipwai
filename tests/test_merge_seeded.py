"""A slice with a story merges once the story ran green, or once it says what keeps it dark.

The captain's `seeded` gate runs after the turn, and a turn that merged has landed by then: recap merged five
slices with a story and no `seeded` line, and two of those stories could never have seeded. So the merge is
where the rule holds.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from harbourmaster_fixture import MergeFixture

from slipwai import logs

STORY = "specs/ordering/slices/ORD-01/try-it.json"


class SeededTest(MergeFixture):
    def a_slice_with_a_story(self) -> None:
        (self.root / STORY).parent.mkdir(parents=True, exist_ok=True)
        self.slice_branch("ORD-01", STORY, '{"steps": []}\n')

    def test_a_story_nobody_seeded_is_refused_and_the_berth_can_fix_it(self) -> None:
        self.a_slice_with_a_story()
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertIn("no `seeded` line", str(answer.fields["why"]))
        self.assertIs(answer.fields["resolve"], True)
        self.assertEqual(self.head("main"), self.trunk_was)

    def test_a_seeded_story_merges(self) -> None:
        self.a_slice_with_a_story()
        self.deck("ordering", "ORD", logs.entry("seeded", fairway="ORD", slice="ORD-01", records=3,
                                                commit=self.head("slice/ORD-01")))
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted")

    def test_a_story_dark_until_a_shared_need_lands_merges_with_the_need_handed_back(self) -> None:
        self.a_slice_with_a_story()
        self.deck("ordering", "ORD", logs.entry("told", fairway="ORD", slice="ORD-01", by="session",
                                                message="dark until the JWT library lands", story=STORY,
                                                needs=[{"what": "add the JWT library", "by": "person"}]))
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted")

    def test_a_hand_back_about_something_else_does_not_let_a_dark_story_through(self) -> None:
        """recap's LB13 merged on a hand-back about its design page, with a story that could never seed."""
        self.a_slice_with_a_story()
        self.deck("ordering", "ORD", logs.entry("told", fairway="ORD", slice="ORD-01", by="session",
                                                message="the design page is the host's",
                                                needs=[{"what": "land the patterns", "by": "person"}]))
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertIn("--dark", str(answer.fields["why"]))

    def test_a_slice_with_no_story_is_not_asked_for_one(self) -> None:
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted")


if __name__ == "__main__":
    unittest.main()
