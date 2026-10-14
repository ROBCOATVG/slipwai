"""What the chart says runs first, and what a person may move while a run is going — slices 18.1 and 18.2.

Two decisions, one file, because they are the same decision at two scales. The order of the chart's
`slices` block is the order every captain takes them in, and the order of its `fairways` block is which
captain is lit when there are fewer berths than fairways. Both were accidents before this: the slices'
order was whatever the split happened to write, and the fairways' was wherever a fairway's first slice
happened to fall. A decision the whole loop follows, taken by nobody, is what these hold against.

`test_clearance.py` beside this holds the rule that lets a slice start at all.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def clearance_module():
    """The toolkit script, loaded the way a generated project runs it: by path, with no slipwai around it."""
    path = ROOT / "assets/toolkit/scripts/agents/clearance.py"
    spec = importlib.util.spec_from_file_location("clearance_order_script", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


chart = clearance_module()

CHART: dict = {
    "v": 1,
    "feature": "ordering",
    "fairways": {"ordering": {}, "billing": {}},
    "marks": {"OrderPlaced": {}, "InvoiceRaised": {}, "PricingPort": {}},
    "slices": {
        "ORD-01": {"fairway": "ordering", "capability": "place-an-order",
                   "sets": ["OrderPlaced"], "steers_by": []},
        "ORD-02": {"fairway": "ordering", "capability": "place-an-order",
                   "sets": ["PricingPort"], "steers_by": []},
        "BIL-01": {"fairway": "billing", "capability": "bill-an-order",
                   "sets": ["InvoiceRaised"], "steers_by": ["OrderPlaced", "PricingPort"]},
    },
}


def fold(*lines: dict):
    """The logs folded as the script folds them, which here is always none: every case is about the chart."""
    return chart.folded(list(lines))


#: Two fairways, a slice each, both ready from the first turn — so what decides which one starts when
#: there is one berth is the fairway priority and nothing else (slice 18.2).
TWO_STREAMS: dict = {
    "v": 1,
    "feature": "ordering",
    "fairways": {"ordering": {}, "billing": {}},
    "marks": {"OrderPlaced": {}, "InvoiceRaised": {}},
    "slices": {
        "ORD-01": {"fairway": "ordering", "capability": "place-an-order", "sets": ["OrderPlaced"],
                   "steers_by": []},
        "ORD-02": {"fairway": "ordering", "capability": "place-an-order", "sets": [], "steers_by": []},
        "BIL-01": {"fairway": "billing", "capability": "bill-an-order", "sets": ["InvoiceRaised"],
                   "steers_by": []},
    },
}


class FairwayPriorityTest(unittest.TestCase):
    """Slice 18.2. With fewer berths than fairways, which stream gets one is a decision — the chart's
    `fairways` block, and the harbour's answer over it while a run is going."""

    def started(self, order: list[str] | None, slots: int) -> list[str]:
        planned = chart.schedule(chart.positions(TWO_STREAMS, fold(), fairways=order),
                                 slots=slots, claims=set())
        return [row["slice"] for row in planned["start"]]

    def test_the_one_slot_goes_to_the_fairway_named_first(self) -> None:
        self.assertEqual(self.started(["billing", "ordering"], 1), ["BIL-01"])
        self.assertEqual(self.started(["ordering", "billing"], 1), ["ORD-01"])

    def test_split_order_still_governs_inside_one_fairway(self) -> None:
        """Across fairways the priority decides; within one, the split's order is the whole rule and a
        priority must not reach into it."""
        self.assertEqual(self.started(["ordering", "billing"], 2), ["ORD-01", "ORD-02"])

    def test_a_queued_slice_says_it_was_the_slot_and_not_the_chart_that_stopped_it(self) -> None:
        planned = chart.schedule(chart.positions(TWO_STREAMS, fold(), fairways=["billing", "ordering"]),
                                 slots=1, claims=set())
        self.assertEqual([row["slice"] for row in planned["queued"]], ["ORD-01", "ORD-02"])
        self.assertIn("no slot", planned["queued"][0]["why"])

    def test_with_no_order_given_the_rows_come_as_the_chart_has_them(self) -> None:
        """Which is what every caller that does not care about fairways gets, unchanged."""
        self.assertEqual(self.started(None, 3), ["ORD-01", "ORD-02", "BIL-01"])

    def test_the_order_is_the_charts_block_with_the_harbours_names_moved_up(self) -> None:
        self.assertEqual(chart.fairway_order(TWO_STREAMS, []), ["ordering", "billing"])
        self.assertEqual(chart.fairway_order(TWO_STREAMS, ["billing"]), ["billing", "ordering"])
        self.assertEqual(chart.fairway_order(TWO_STREAMS, ["gone"]), ["ordering", "billing"],
                         "a stale name is not a reason to reorder or to drop a fairway")


class OrderProposalTest(unittest.TestCase):
    """Slice 18.1. The order of the chart's `slices` block is the order every captain takes them in, and
    until this it was written by the split as a side effect of writing the rows. `--order` is what the
    split reads out to propose it: every row with what it is read off, so the person is confirming an
    argued order rather than a list."""

    def rows(self) -> dict[str, str]:
        return dict(chart.order_reasons(CHART))

    def test_the_rows_come_in_the_charts_own_order_and_nothing_is_sorted(self) -> None:
        self.assertEqual([slice_id for slice_id, _ in chart.order_reasons(CHART)],
                         ["ORD-01", "ORD-02", "BIL-01"])

    def test_a_row_says_what_waits_on_it_which_is_why_it_would_go_early(self) -> None:
        self.assertIn("sets OrderPlaced, which 1 slice steers by", self.rows()["ORD-01"])
        self.assertIn("which nothing steers by", self.rows()["BIL-01"])

    def test_a_row_says_what_holds_it_and_who_owes_that(self) -> None:
        """The hard constraint, as against the judgement: a row cannot be proposed above what sets its marks."""
        self.assertIn("steers by OrderPlaced (ORD-01) and PricingPort (ORD-02)", self.rows()["BIL-01"])
        self.assertIn("steers by nothing", self.rows()["ORD-01"])

    def test_a_row_says_where_it_falls_in_its_capability_because_that_is_what_a_demo_is_of(self) -> None:
        self.assertIn("first of place-an-order", self.rows()["ORD-01"])
        self.assertIn("place-an-order, after ORD-01", self.rows()["ORD-02"])

    def test_an_observed_slice_is_named_as_a_record_rather_than_proposed_as_work(self) -> None:
        """It is what the code already does, so there is no question of when it runs."""
        charted = {**CHART, "slices": {**CHART["slices"],
                                       "ORD-00": {"fairway": "ordering", "capability": "place-an-order",
                                                  "sets": [], "steers_by": [], "observed": True}}}
        self.assertIn("observed", dict(chart.order_reasons(charted))["ORD-00"])
        self.assertNotIn("first of", dict(chart.order_reasons(charted))["ORD-00"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
