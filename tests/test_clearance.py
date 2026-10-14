"""Clearance: what lets a slice start, and what it says when it may not.

Version 1 asked whether a slice's own contract was settled, which a slice could only answer about itself.
That serialised a fresh fairway, because nothing said what a slice was waiting *for*. The rule here is the
one issue #32 asked for: a slice starts when every mark it steers by has been set, and a mark is set when
some slice wrote a `mark-set` line for it at its own first stage. So a sibling unblocks this one by having
planned, not by having merged, which is the whole of the parallelism the plan promises.

Two things are held here besides the rule. State comes from log lines and never from a status field,
because in the first attempt `model.yaml` said `planned` for eight slices that were built and merged. And a
refusal names every mark that is missing and who owes it, because a fairway told one blocker at a time is a
fairway blocked once per blocker.
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
    spec = importlib.util.spec_from_file_location("clearance_script", path)
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


def mark_set(mark: str, by: str) -> dict:
    return {"v": 1, "kind": "mark-set", "mark": mark, "slice": by, "fairway": "ordering"}


def marks(lines: list[dict] | None = None) -> set[str]:
    """The set of marks those log lines set — what the script folds out of the deck logs."""
    return {str(line["mark"]) for line in (lines or [])
            if line.get("kind") == "mark-set" and line.get("mark")}


class ClearanceTest(unittest.TestCase):
    def test_a_slice_steering_by_nothing_starts_at_once(self) -> None:
        """Which is what lets a fresh fairway fan out on its first iteration."""
        self.assertIs(chart.cleared(CHART, marks(), "ORD-01"), True)

    def test_a_slice_is_cleared_when_every_mark_it_steers_by_is_set(self) -> None:
        lines = [mark_set("OrderPlaced", "ORD-01"), mark_set("PricingPort", "ORD-02")]
        self.assertIs(chart.cleared(CHART, marks(lines), "BIL-01"), True)

    def test_one_mark_short_is_not_cleared(self) -> None:
        self.assertIsInstance(chart.cleared(CHART, [mark_set("OrderPlaced", "ORD-01")], "BIL-01"), str)

    def test_the_refusal_names_every_missing_mark_and_who_owes_it(self) -> None:
        """A fairway told one blocker at a time is a fairway blocked once per blocker."""
        why = chart.cleared(CHART, marks(), "BIL-01")
        assert isinstance(why, str)
        self.assertIn("OrderPlaced (set by ORD-01)", why)
        self.assertIn("PricingPort (set by ORD-02)", why)

    def test_a_mark_nobody_sets_says_the_chart_is_wrong_rather_than_blaming_a_slice(self) -> None:
        broken: dict = {**CHART, "slices": {"BIL-01": {"steers_by": ["ShipmentBooked"], "sets": []}}}
        why = chart.cleared(broken, marks(), "BIL-01")
        assert isinstance(why, str)
        self.assertIn("no slice sets it", why)

    def test_a_slice_the_chart_does_not_name_is_refused_and_not_cleared(self) -> None:
        """Answering True for a slice nobody charted would clear anything anyone asked about."""
        why = chart.cleared(CHART, marks(), "SHP-01")
        assert isinstance(why, str)
        self.assertIn("not on the chart", why)

    def test_a_merge_is_not_what_clears_a_sibling(self) -> None:
        """A `mark-set` line is written at the setter's first stage, in its own worktree, long before it
        merges. If a merge were the signal, every fairway would wait on every other one."""
        lines = [mark_set("OrderPlaced", "ORD-01"), mark_set("PricingPort", "ORD-02"),
                 {"kind": "claimed", "slice": "ORD-01"}]
        self.assertIs(chart.cleared(CHART, marks(lines), "BIL-01"), True)
        self.assertNotIn("merged", [line.get("kind") for line in lines])

    def test_a_line_kind_this_reader_does_not_know_is_ignored(self) -> None:
        """The deck log holds eleven kinds and grows. A reader that refused the unfamiliar would break
        every time one was added."""
        lines = [{"kind": "heartbeat"}, {"kind": "tokens", "mark": "OrderPlaced"},
                 mark_set("OrderPlaced", "ORD-01"), mark_set("PricingPort", "ORD-02")]
        self.assertIs(chart.cleared(CHART, marks(lines), "BIL-01"), True)

    def test_a_mark_set_line_with_no_mark_sets_nothing(self) -> None:
        self.assertEqual(marks([{"kind": "mark-set", "slice": "ORD-01"}]), set())


class ReadySetTest(unittest.TestCase):
    def test_the_cleared_set_is_in_the_charts_own_order_which_is_split_order(self) -> None:
        self.assertEqual(chart.cleared_slices(CHART, marks()), ["ORD-01", "ORD-02"])

    def test_a_setter_planning_clears_what_waits_on_it(self) -> None:
        lines = [mark_set("OrderPlaced", "ORD-01"), mark_set("PricingPort", "ORD-02")]
        self.assertEqual(chart.cleared_slices(CHART, marks(lines)), ["ORD-01", "ORD-02", "BIL-01"])


def line(kind: str, **fields: object) -> dict:
    return {"v": 1, "kind": kind, "fairway": "ordering", **fields}


def fold(*lines: dict):
    return chart.folded(list(lines))


def state_of(slice_id: str, *lines: dict, done: frozenset[str] = frozenset(),
             charted: dict = CHART) -> tuple[str, str]:
    return chart.position(charted, fold(*lines), slice_id, done)


class StateTest(unittest.TestCase):
    """One word hid a distinction: `ready` said nothing about whether a slice could be prepared, implemented, or
    was waiting on a person. Each state carries the sentence that says why, so a host never has to infer it."""

    def test_a_cleared_slice_that_has_not_set_its_own_marks_is_preparation_ready(self) -> None:
        state, why = state_of("ORD-01")
        self.assertEqual(state, "preparation-ready")
        self.assertIn("OrderPlaced", why)
        self.assertIn("mark-set", why)

    def test_a_cleared_slice_whose_own_marks_are_set_is_implementation_ready(self) -> None:
        state, _ = state_of("ORD-01", mark_set("OrderPlaced", "ORD-01"), line("decision", id="D1", what="x"))
        self.assertEqual(state, "implementation-ready")

    def test_a_slice_that_sets_nothing_has_nothing_to_settle(self) -> None:
        charted = {**CHART, "slices": {**CHART["slices"], "ORD-03": {"fairway": "ordering", "capability": "c",
                                                                      "sets": [], "steers_by": []}}}
        state, why = state_of("ORD-03", charted=charted)
        self.assertEqual(state, "implementation-ready")
        self.assertIn("sets nothing", why)

    def test_a_slice_waiting_on_an_unset_mark_is_blocked_and_names_the_setter(self) -> None:
        state, why = state_of("BIL-01")
        self.assertEqual(state, "blocked")
        self.assertIn("ORD-01", why)

    def test_a_claimed_slice_is_running_and_says_which_band(self) -> None:
        state, why = state_of("ORD-01", line("claimed", slice="ORD-01", t="2026-10-13T09:00:00Z"))
        self.assertEqual(state, "running")
        self.assertIn("preparing", why)
        state, why = state_of("ORD-01", line("claimed", slice="ORD-01"), mark_set("OrderPlaced", "ORD-01"))
        self.assertEqual((state, "implementing" in why), ("running", True))

    def test_a_slice_whose_capability_is_due_a_demo_is_awaiting_demo(self) -> None:
        state, why = state_of("ORD-01", line("claimed", slice="ORD-01"), mark_set("OrderPlaced", "ORD-01"),
                              line("demo-due", capability="place-an-order"))
        self.assertEqual(state, "awaiting-demo")
        self.assertIn("place-an-order", why)
        state, _ = state_of("ORD-01", line("claimed", slice="ORD-01"), mark_set("OrderPlaced", "ORD-01"),
                            line("demo-due", capability="place-an-order"),
                            line("accepted", capability="place-an-order"))
        self.assertEqual(state, "running")

    def test_a_merged_slice_is_done(self) -> None:
        state, _ = state_of("ORD-01", line("claimed", slice="ORD-01"), line("merged", slice="ORD-01", commit="abc123"))
        self.assertEqual(state, "done")

    def test_a_parked_fairway_reads_as_awaiting_decision_for_every_slice_in_it(self) -> None:
        state, why = state_of("ORD-02", line("parked", why="which currency"))
        self.assertEqual(state, "awaiting-decision")
        self.assertIn("which currency", why)

    def test_every_state_the_fold_can_produce_is_on_the_scale(self) -> None:
        self.assertEqual(len(chart.STATES), len(set(chart.STATES)))
        for state in ("blocked", "preparation-ready", "implementation-ready", "running", "awaiting-demo",
                      "awaiting-decision", "migration-evidence-required", "done"):
            self.assertIn(state, chart.STATES)


class AcceptanceTest(unittest.TestCase):
    """The six behaviours the scheduling rules are held to, each one a run that went wrong before it was written."""

    def test_two_cleared_slices_with_unsettled_contracts_prepare_concurrently(self) -> None:
        """Both set a mark nobody has set yet. That is not a reason to wait: preparing is what sets it."""
        planned = chart.schedule(chart.positions(CHART, fold()), slots=None, claims=set())
        started = {row["slice"]: row["band"] for row in planned["start"]}
        self.assertEqual(started, {"ORD-01": "prepare", "ORD-02": "prepare"})
        self.assertEqual([row["slice"] for row in planned["waiting"]], ["BIL-01"])

    def test_a_slice_awaiting_a_human_answer_does_not_stop_an_independent_sibling(self) -> None:
        found = chart.positions(CHART, fold(line("claimed", slice="ORD-01"),
                                            line("question", slice="ORD-01", id="Q1", what="which HTTP shape")))
        self.assertEqual(found["ORD-01"][0], "awaiting-decision")
        self.assertIn("Q1", found["ORD-01"][1])
        self.assertIn("BIL-01", found["ORD-01"][1], "the question says which siblings its answer unblocks")
        self.assertEqual(found["ORD-02"][0], "preparation-ready")
        self.assertEqual(found["BIL-01"][0], "blocked")
        self.assertIn("awaiting decision", found["BIL-01"][1])
        planned = chart.schedule(found, slots=None, claims=set())
        self.assertEqual([row["slice"] for row in planned["start"]], ["ORD-02"])

    def test_a_newly_approved_contract_starts_eligible_work_from_the_log_alone(self) -> None:
        """The decision line and the mark-set are all that change. No command is re-invoked; the next read of
        the schedule has the slice starting and the sibling it unblocked cleared."""
        before = chart.schedule(chart.positions(CHART, fold(
            line("claimed", slice="ORD-01"), line("question", slice="ORD-01", id="Q1", what="shape"))), None, set())
        self.assertNotIn("ORD-01", [row["slice"] for row in before["start"]])
        after = chart.positions(CHART, fold(
            line("claimed", slice="ORD-01"), line("question", slice="ORD-01", id="Q1", what="shape"),
            line("decision", id="Q1", what="REST, one resource"), mark_set("OrderPlaced", "ORD-01"),
            line("claimed", slice="ORD-02"), mark_set("PricingPort", "ORD-02")))
        self.assertEqual(after["ORD-01"][0], "running")
        self.assertIn("implementing", after["ORD-01"][1])
        self.assertEqual(after["BIL-01"][0], "preparation-ready")
        self.assertEqual([row["slice"] for row in chart.schedule(after, None, set())["start"]], ["BIL-01"])

    def test_more_ready_slices_than_slots_produce_a_visible_queue_that_refills_on_completion(self) -> None:
        planned = chart.schedule(chart.positions(CHART, fold()), slots=1, claims=set())
        self.assertEqual([row["slice"] for row in planned["start"]], ["ORD-01"])
        self.assertEqual([row["slice"] for row in planned["queued"]], ["ORD-02"])
        self.assertIn("no slot", planned["queued"][0]["why"])
        refilled = chart.schedule(chart.positions(CHART, fold(
            line("claimed", slice="ORD-01"), mark_set("OrderPlaced", "ORD-01"),
            line("merged", slice="ORD-01", commit="abc"))), slots=1, claims=set())
        self.assertEqual([row["slice"] for row in refilled["start"]], ["ORD-02"])
        self.assertEqual([row["slice"] for row in refilled["done"]], ["ORD-01"])

    def test_the_two_concurrency_numbers_are_read_as_two_things_and_printed_as_such(self) -> None:
        """`boilers` bounds slices and `fanout` bounds the delegates inside one; a run that read one as the
        other dispatched two where it had room for three. The line says both and what they add up to."""
        import json
        import tempfile
        config = Path(tempfile.mkdtemp()) / "harbour.json"
        config.write_text(json.dumps({"boilers": 3, "fanout": 2}), encoding="utf-8")
        numbers = chart.numbers_from(config, running=1)
        self.assertEqual((numbers["slots"], numbers["fanout"], numbers["tree"]), (2, 2, 9))
        self.assertEqual(chart.slots_from(config, 1), 2)
        line_ = chart.numbers_line(numbers)
        self.assertIn("2 slice(s) may start (boilers 3 − 1 running)", line_)
        self.assertIn("fanout 2 delegate(s) inside each slice", line_)
        self.assertIn("tree ≤ 9", line_)
        self.assertIn("unbounded", chart.numbers_line(chart.numbers_from(config.with_name("none.json"), 0)))

    def test_a_migrated_shipped_prerequisite_requires_recorded_evidence_not_a_fabricated_mark(self) -> None:
        """ORD-01 shipped before marks were logged: the done marker names it and no log does. BIL-01 is told
        *migration evidence required* and not *blocked*, nothing is cleared on the marker alone, and the
        baseline that records the evidence says on the line that it is a baseline."""
        state, why = state_of("BIL-01", mark_set("PricingPort", "ORD-02"), done=frozenset({"ORD-01"}))
        self.assertEqual(state, "migration-evidence-required")
        self.assertIn("--baseline-marks", why)
        self.assertNotIn("BIL-01", chart.cleared_slices(CHART, {"PricingPort"}), "the marker clears nothing")
        written, said = chart.baseline(CHART, {"ORD-01"}, [mark_set("PricingPort", "ORD-02")], "laptop")
        self.assertEqual([(row.fields["slice"], row.fields["mark"]) for row in written], [("ORD-01", "OrderPlaced")])
        self.assertEqual(written[0].fields["provenance"], "baseline")
        self.assertIn("evidence", written[0].fields)
        recorded = [mark_set("PricingPort", "ORD-02"), {"v": 1, **written[0].fields, "kind": "mark-set"}]
        state, why = state_of("BIL-01", *recorded, done=frozenset({"ORD-01"}))
        self.assertEqual(state, "preparation-ready")
        state, why = state_of("ORD-01", *recorded, done=frozenset({"ORD-01"}))
        self.assertIn("baseline", why, "a baselined mark is named as one wherever it clears something")
        again, refusal = chart.baseline(CHART, {"ORD-01", "ORD-02"}, recorded, "laptop")
        self.assertEqual(again, [])
        self.assertIn("already taken", refusal)

    def test_a_slice_that_shipped_before_the_mark_log_is_a_record_and_never_offered(self) -> None:
        """Before and after the baseline. The marker keeps it out of the ready set; it never clears a sibling."""
        state, why = state_of("ORD-01", done=frozenset({"ORD-01"}))
        self.assertEqual(state, "done")
        self.assertIn("marker", why)
        written, _ = chart.baseline(CHART, {"ORD-01"}, [], "laptop")
        recorded = [{"v": 1, **row.fields, "kind": "mark-set"} for row in written]
        state, why = state_of("ORD-01", *recorded, done=frozenset({"ORD-01"}))
        self.assertEqual(state, "done")
        self.assertIn("baseline", why)
        planned = chart.schedule(chart.positions(CHART, fold(*recorded), {"ORD-01"}), None, set())
        self.assertNotIn("ORD-01", [row["slice"] for row in planned["start"]])
        self.assertIn("ORD-01", [row["slice"] for row in planned["done"]])

    def test_a_failed_claim_lookup_never_becomes_all_slices_unclaimed(self) -> None:
        planned = chart.schedule(chart.positions(CHART, fold()), slots=None, claims=None)
        self.assertEqual(planned["start"], [])
        self.assertEqual({row["slice"] for row in planned["queued"]}, {"ORD-01", "ORD-02"})
        for row in planned["queued"]:
            self.assertIn("claims could not be read", row["why"])
        elsewhere = chart.schedule(chart.positions(CHART, fold()), slots=None, claims={"ORD-01"})
        self.assertEqual([row["slice"] for row in elsewhere["start"]], ["ORD-02"])
        self.assertIn("another session", elsewhere["queued"][0]["why"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
