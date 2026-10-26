"""The lines a strategy ADR records beside its name, and what each strategy cannot start without."""
from __future__ import annotations

import datetime
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.layout import Layout
from slipwai.strategy import decision_of
from slipwai.strategy_record import lines_of, missing, review_in_date

ADR = "# 0002. Change strategy\n\n## Status\n\nAccepted\n\n## Decision\n\nStrategy: {strategy}\n{lines}\n"


class LinesTest(unittest.TestCase):
    def test_a_line_is_read_however_it_is_emphasised_and_a_template_value_is_not_an_answer(self) -> None:
        lines = lines_of("**New home:** beside services/next\n- `End`: all — deleted by 2027-06-30\nTarget: <shape>\n")
        self.assertEqual(lines["New home"], "beside services/next")
        self.assertEqual(lines["End"], "all — deleted by 2027-06-30")
        self.assertNotIn("Target", lines, "a value still in angle brackets is the template's")

    def test_each_strategy_names_what_it_cannot_start_without(self) -> None:
        self.assertEqual(missing("in-place", {}), ["Target"])
        self.assertEqual(missing("leave-it", {"Variant": "retain"}), ["Risk-owner", "Review"])
        self.assertIn("Why single cut-over", missing("rewrite", {}))

    def test_a_strangler_that_moves_everything_owes_what_a_rewrite_owes(self) -> None:
        partial = {"Freeze": "agreed — the owner, 2026-10-01", "New home": "beside", "End": "partial",
                   "Target": "as-is"}
        self.assertEqual(missing("strangler-fig", partial), [])
        self.assertEqual(missing("strangler-fig", {**partial, "End": "all — by 2027-06-30"}), ["Parity", "Checkpoint"])

    def test_a_freeze_is_answered_only_by_agreed_or_absent(self) -> None:
        said = {"New home": "beside", "End": "partial", "Target": "as-is"}
        self.assertIn("Freeze", missing("strangler-fig", {**said, "Freeze": "we'll see"}))
        self.assertNotIn("Freeze", missing("strangler-fig", {**said, "Freeze": "absent — re-pin every release"}))

    def test_a_review_is_in_date_only_when_it_is_ahead(self) -> None:
        today = datetime.date(2026, 10, 26)
        self.assertTrue(review_in_date({"Review": "2027-04-30"}, today))
        self.assertFalse(review_in_date({"Review": "2026-01-01"}, today))
        self.assertFalse(review_in_date({}, today), "no date is a review nobody set")


class OldNameTest(unittest.TestCase):
    def test_a_modular_monolith_decided_before_reads_as_a_strangler_whose_home_is_inside(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "delivery/docs/adr").mkdir(parents=True)
            (root / "delivery/docs/adr/0002-strategy.md").write_text(
                ADR.format(strategy="modular-monolith", lines=""), encoding="utf-8")
            decided = decision_of(root, Layout("delivery"))
        self.assertEqual(decided["decided"], "strangler-fig")
        self.assertEqual((decided["lines"]["New home"], decided["lines"]["Target"]),
                         ("inside", "modules in one deployable"))
        self.assertEqual(decided["missing"], ["Freeze", "End"], "what the old name implied is not asked again")


if __name__ == "__main__":
    unittest.main()
