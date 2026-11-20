"""A further feature's slice at its merge: its story and its capability's gates are under its own feature.

The merge held a story to its `seeded` line by looking under the feature the stream's log is in, and a
capability to its gates under the chart's. A later feature's slice has neither there, so its unseeded story
went through and its cleared gates were never found.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from harbourmaster_fixture import MergeFixture

from slipwai import logs

#: One chart, under `ordering`; ORD-01 is a later feature's and BIL-01 a third's, each the whole of a capability.
CHART = """slices:
  ORD-01: {fairway: ORD, feature: later, capability: place-an-order, sets: [], steers_by: []}
  BIL-01: {fairway: ORD, feature: third, capability: bill-an-order, sets: [], steers_by: []}
  ORD-02: {fairway: ORD, capability: pay, sets: [], steers_by: []}
"""
STORY = "specs/later/slices/ORD-01/try-it.json"


class FurtherFeatureMergeTest(MergeFixture):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        self.commit("the chart")

    def branch(self, slice_id: str, files: dict[str, str]) -> None:
        for path in files:
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        first, *rest = files
        self.git("checkout", "--quiet", "-b", f"slice/{slice_id}", "main")
        for path in rest:
            (self.root / path).write_text(files[path], encoding="utf-8")
        (self.root / first).write_text(files[first], encoding="utf-8")
        self.commit(slice_id)
        self.git("checkout", "--quiet", "-b", f"parked-{slice_id}", f"slice/{slice_id}")

    def gates(self, feature: str, capability: str) -> str:
        return f"specs/{feature}/capabilities/{capability}/gates.md"

    def test_a_story_under_the_slice_s_own_feature_is_held_to_its_seed(self) -> None:
        self.branch("ORD-01", {STORY: '{"steps": []}\n',
                               self.gates("later", "place-an-order"): "Cleared: 2026-11-20 · c0ffee\n"})
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertIn(f"has a story ({STORY})", str(answer.fields["why"]))

    def test_seeded_and_its_gates_cleared_under_its_own_feature_it_merges(self) -> None:
        self.branch("ORD-01", {STORY: '{"steps": []}\n',
                               self.gates("later", "place-an-order"): "Cleared: 2026-11-20 · c0ffee\n"})
        self.deck("ordering", "ORD", logs.entry("seeded", fairway="ORD", slice="ORD-01", records=1,
                                                commit=self.head("slice/ORD-01")))
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted", self.answer().fields)

    def test_a_third_feature_s_capability_is_held_to_the_gates_under_the_third(self) -> None:
        self.branch("BIL-01", {"service.txt": "one\ntwo\n"})
        self.ask("BIL-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertIn(self.gates("third", "bill-an-order"), str(answer.fields["why"]))

    def test_a_slice_naming_no_feature_is_held_under_the_chart_s_as_it_was(self) -> None:
        self.branch("ORD-02", {self.gates("ordering", "pay"): "Cleared: 2026-11-20 · c0ffee\n"})
        self.ask("ORD-02")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted", self.answer().fields)


if __name__ == "__main__":
    unittest.main()
