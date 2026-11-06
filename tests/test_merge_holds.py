"""A merge is held where the gate skipped part of itself, where a capability would be made whole ungated, and where
trunk's CI cannot be read.

recap merged 34 slices over all three: every slice with a screen over `render gate(s) SKIPPED, not passed`, the
last slice of each of its eight capabilities with no gate run on any of them, and every merge `ci=unverified`
behind a repository with no remote, whose CI would have failed from its first commit.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401
from harbourmaster_fixture import MergeFixture

from slipwai import logs

CHART = {"slices": {"ORD-01": {"capability": "take-orders", "fairway": "ORD"},
                    "ORD-02": {"capability": "take-orders", "fairway": "ORD"}}}
GATES = "specs/ordering/capabilities/take-orders/gates.md"


class SkippedTest(MergeFixture):
    GATE = ("verify:\n\t@echo 'check-ux-gates: apps/web/screens/ — 12 render gate(s) SKIPPED, not passed'\n"
            "\t@echo 'verify: all gates passed'\n")

    def test_a_gate_that_skipped_part_of_itself_is_refused_and_the_berth_can_fix_it(self) -> None:
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertIn("A skipped gate has not passed", str(answer.fields["why"]))
        self.assertIn("12 render gate(s) SKIPPED", str(answer.fields["why"]))
        self.assertIs(answer.fields["resolve"], True)
        self.assertEqual(self.head("main"), self.trunk_was)


class FurnishedTest(MergeFixture):
    """The merge is gated in a worktree, which has the tracked tree and nothing an extension installed."""

    GATE = ("verify:\n\t@test -f tools/kit/installed && echo 'verify: all gates passed' "
            "|| echo 'the kit is not installed in this checkout — SKIPPED, not passed'\n")

    def test_what_an_extension_installed_under_tools_is_there_for_the_gate(self) -> None:
        (self.root / ".gitignore").write_text(".slipwai/\ntools/kit/\n", encoding="utf-8")
        self.commit("the kit is ignored")
        (self.root / "tools/kit").mkdir(parents=True)
        (self.root / "tools/kit/installed").write_text("yes\n", encoding="utf-8")
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted", self.answer().fields)


class CapabilityTest(MergeFixture):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text(json.dumps(CHART), encoding="utf-8")
        self.commit("the chart")

    def test_the_last_slice_of_an_ungated_capability_is_refused_naming_its_record(self) -> None:
        self.deck("ordering", "ORD", logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc"))
        self.slice_branch("ORD-02", "service.txt", "one\ntwo\n")
        self.ask("ORD-02")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertIn("last slice of take-orders", str(answer.fields["why"]))
        self.assertIn(GATES, str(answer.fields["why"]))
        self.assertIs(answer.fields["resolve"], True)

    def test_the_last_slice_merges_once_its_branch_has_cleared_the_gates(self) -> None:
        self.deck("ordering", "ORD", logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc"))
        (self.root / GATES).parent.mkdir(parents=True)
        self.slice_branch("ORD-02", GATES, "# take-orders — gates\n\nCleared: 2026-11-06, nothing above the bar\n")
        self.ask("ORD-02")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted", self.answer().fields)

    def test_a_slice_that_leaves_its_capability_unfinished_is_not_held(self) -> None:
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted", self.answer().fields)


class UnaskedTest(MergeFixture):
    def test_a_forge_nobody_can_ask_parks_the_merge_with_why(self) -> None:
        """recap: no remote for fifteen days, and all 34 merges granted `ci=unverified`."""
        (self.root / "harbour.json").write_text(json.dumps({"trunk": "main", "ci": ["false"]}), encoding="utf-8")
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertIn("trunk's CI cannot be read here", str(answer.fields["why"]))
        self.assertIn("the forge could not be asked", str(answer.fields["why"]))
        self.assertIs(answer.fields["resolve"], False)
        self.assertEqual(answer.fields["waiting"], "green-trunk")
        self.assertEqual(self.head("main"), self.trunk_was)

    def test_ci_off_merges_unverified_as_before(self) -> None:
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "granted", answer.fields)
        self.assertEqual(answer.fields["ci"], "unverified")


if __name__ == "__main__":
    unittest.main()
