"""`harbour.json`: the numbers a run is held to, and what a stage does when it reaches one.

The experiment spent 104 hours and, at its worst, hundreds of millions of input tokens on a single slice,
with nothing anywhere saying what too much was. A stage that has no budget cannot be over one, so the only
signals were a person noticing and the bill arriving. Both are late.

What is held here is that the numbers exist, that they are in the project rather than in a prompt, and that
reaching one means stowing rather than stopping — with the two exceptions where stowing would be dishonest.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.project import harbour
from slipwai.project.careen import DEFAULT_BAR, SEVERITIES
from slipwai.project.stage_models import STAGES


def flat(text: str) -> str:
    return " ".join(text.split())


class ConfigTest(unittest.TestCase):
    def document(self) -> dict:
        return json.loads(harbour.harbour_config())

    def test_it_is_json_a_person_can_edit_and_says_what_each_number_is(self) -> None:
        document = self.document()
        self.assertEqual(document["v"], 1)
        self.assertIn("stowed into the fairway's careen", document["_comment"])

    def test_every_stage_budget_names_both_a_clock_and_a_spend(self) -> None:
        """Either alone lets the other run away: a cheap stage can still take all afternoon."""
        for stage, budget in self.document()["stages"].items():
            with self.subTest(stage=stage):
                self.assertIn("minutes", budget)
                self.assertIn("tokens", budget)

    def test_there_is_a_default_for_a_stage_nobody_named(self) -> None:
        """A stage added later is budgeted from the day it exists rather than from the day somebody notices."""
        self.assertIn("default", self.document()["stages"])

    def test_every_named_budget_is_a_stage_the_table_has(self) -> None:
        """A budget keyed on nothing is a number that never applies and never says so."""
        keys = {stage.key for stage in STAGES}
        for named in self.document()["stages"]:
            if named == "default":
                continue
            with self.subTest(stage=named):
                self.assertIn(named, keys)

    def test_the_implement_stage_gets_the_largest_budget(self) -> None:
        """It is the one that writes the code; a budget that treats it like a gaps pass would be wrong."""
        stages = self.document()["stages"]
        self.assertEqual(max(stages, key=lambda name: stages[name]["tokens"]), "implement-shipwright")

    def test_the_bar_is_the_careen_s_and_not_a_second_copy(self) -> None:
        self.assertEqual(self.document()["bar"], DEFAULT_BAR)
        self.assertIn(self.document()["bar"], SEVERITIES)

    def test_a_decision_ceiling_exists_because_the_experiment_had_none(self) -> None:
        """125 decisions with 105 never reviewed is not a record of judgement, it is a backlog of it."""
        self.assertGreater(self.document()["decision_ceiling"], 0)

    def test_every_wait_has_a_bound(self) -> None:
        """A wait with no bound is indistinguishable from a run that has stopped."""
        self.assertGreater(self.document()["wait_bound"], 0)


class BudgetSectionTest(unittest.TestCase):
    def section(self) -> str:
        return flat(harbour.budget_section())

    def test_reaching_a_budget_means_stowing_rather_than_stopping(self) -> None:
        section = self.section()
        self.assertIn("It stows", section)
        self.assertIn("the slice continues to its next rung and may merge", section.lower())

    def test_work_above_the_bar_parks_rather_than_being_stowed(self) -> None:
        """The point of a bar is that what is above it does not get deferred by a clock."""
        self.assertIn("parks for a person", self.section())
        self.assertIn("does not get deferred by a clock", self.section())

    def test_nothing_critical_is_ever_stowed_whatever_the_budget_said(self) -> None:
        self.assertIn("Nothing CRITICAL is ever stowed", self.section())

    def test_the_number_is_recorded_and_not_only_that_it_was_reached(self) -> None:
        """A budget that is hit every time is a budget that is wrong, and the word `stowed` does not say so."""
        section = self.section()
        self.assertIn("Say the number, not just that it was reached", section)
        self.assertIn("a budget that is hit every time is a budget that is wrong", section)

    def test_it_names_where_the_leftovers_go_and_what_records_it(self) -> None:
        """Into the capability's record, which a slice may write — never the careen itself, which every slice
        of a stream shares and the harbourmaster alone writes (issue 154)."""
        section = self.section()
        self.assertIn("Write what is left into the capability's record** — "
                      "`specs/<feature>/capabilities/<capability>/stowed.md`", section)
        self.assertIn("the harbourmaster carries the record's rows into `fairways/<name>/careen.md` when the "
                      "slice merges", section)
        self.assertNotIn("Write what is left into the fairway's careen", section)
        self.assertIn("`stowed` line", section)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
