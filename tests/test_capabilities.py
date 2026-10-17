"""The capability: what a person's demo is of, and what says one is owed.

Version 1 stopped a person at the end of every slice and showed them a fraction of a capability to assemble
in their head. A whole capability is owed its gates first — gaps, design review, adversary, mutation and the
hand's walk, since 2026-10-17 — and nobody is stopped for them. The stop a person attends runs once its last
slice has merged and its gate record says `Cleared:`.

The other thing held here is that acceptance and hoisting never touch. Acceptance says the capability is
right; hoisting says the business wants it live, which may be another quarter or never. A capability the
business is deliberately holding back is not a late one, and a board that derived one state from the other
could not tell the two apart.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.project import demo_stop

ROOT = Path(__file__).resolve().parents[1]


def module():
    path = ROOT / "assets/toolkit/scripts/agents/capabilities.py"
    spec = importlib.util.spec_from_file_location("capabilities_script", path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(loaded)
    return loaded


CAPS = module()

CHART: dict = {
    "slices": {
        "ORD-01": {"capability": "place-an-order", "fairway": "ordering"},
        "ORD-02": {"capability": "place-an-order", "fairway": "ordering"},
        "BIL-01": {"capability": "bill-an-order", "fairway": "billing"},
    }
}


def merged(slice_id: str) -> dict:
    return {"v": 1, "kind": "merged", "slice": slice_id, "fairway": "ordering", "commit": "abc"}


def accepted(capability: str) -> dict:
    return {"v": 1, "kind": "accepted", "capability": capability, "fairway": "ordering"}


class GroupingTest(unittest.TestCase):
    def test_a_capability_is_its_slices_in_split_order(self) -> None:
        self.assertEqual(CAPS.slices_by_capability(CHART)["place-an-order"], ["ORD-01", "ORD-02"])

    def test_a_slice_with_no_capability_is_in_none(self) -> None:
        """check-chart refuses that chart; this reader does not invent a group for it."""
        self.assertEqual(CAPS.slices_by_capability({"slices": {"X": {"fairway": "ordering"}}}), {})


class DueTest(unittest.TestCase):
    def test_nothing_is_due_before_the_last_slice_merges(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01")])
        self.assertEqual(CAPS.due(rows), [])

    def test_a_capability_owes_its_gates_when_its_last_slice_merges(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02")])
        self.assertEqual([row["capability"] for row in CAPS.gates_due(rows)], ["place-an-order"])
        self.assertEqual(CAPS.due(rows), [], "a demo before the gates clear shows the person what nobody read")

    def test_a_capability_is_due_a_demo_once_its_gates_clear(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02")], {"place-an-order"})
        self.assertEqual([row["capability"] for row in CAPS.due(rows)], ["place-an-order"])
        self.assertEqual(CAPS.gates_due(rows), [])

    def test_gates_are_not_owed_before_the_last_slice_merges(self) -> None:
        self.assertEqual(CAPS.gates_due(CAPS.state(CHART, [merged("ORD-01")])), [])

    def test_a_part_merged_capability_says_what_it_waits_on(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01")])
        row = next(r for r in rows if r["capability"] == "place-an-order")
        self.assertEqual(row["waiting"], ["ORD-02"])
        self.assertEqual(row["merged"], 1)

    def test_an_accepted_capability_is_no_longer_due(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02"), accepted("place-an-order")])
        self.assertEqual(CAPS.due(rows), [])

    def test_one_capability_completing_does_not_make_another_due(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02")])
        self.assertNotIn("bill-an-order", [row["capability"] for row in CAPS.due(rows)])


class ReleaseTest(unittest.TestCase):
    def test_accepted_and_hoisted_are_separate_and_neither_is_derived(self) -> None:
        """A capability the business is deliberately holding back is not a late one."""
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02"), accepted("place-an-order")])
        row = next(r for r in rows if r["capability"] == "place-an-order")
        self.assertTrue(row["accepted"])
        self.assertFalse(row["hoisted"], "acceptance must never imply a hoist")

    def test_a_capability_can_be_hoisted_and_the_two_states_stay_apart(self) -> None:
        rows = CAPS.state(CHART, [merged("ORD-01"), merged("ORD-02"), accepted("place-an-order"),
                                  {"v": 1, "kind": "flag-hoisted", "flag": "place-an-order", "where": "prod"}])
        row = next(r for r in rows if r["capability"] == "place-an-order")
        self.assertTrue(row["accepted"])
        self.assertTrue(row["hoisted"])

    def test_the_trigger_mentions_no_flag_at_all(self) -> None:
        """Under the open release mode there is no flag, and the demo still happens."""
        rows = CAPS.state(CHART, [merged("BIL-01")], {"bill-an-order"})
        self.assertEqual([row["capability"] for row in CAPS.due(rows)], ["bill-an-order"])


class GateRecordTest(unittest.TestCase):
    """`Cleared:` in the capability's `gates.md` is what the reader takes as the gates having run."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.saved = CAPS.SPECS
        CAPS.SPECS = Path(self.directory.name)
        self.addCleanup(setattr, CAPS, "SPECS", self.saved)

    def record(self, capability: str, text: str) -> None:
        path = CAPS.SPECS / "001-orders" / "capabilities" / capability / "gates.md"
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")

    def test_a_record_ending_cleared_counts(self) -> None:
        self.record("place-an-order", "## Gaps\nnone\n\nCleared: 2026-10-17 · abc123\n")
        self.assertEqual(CAPS.cleared("001-orders", ["place-an-order", "bill-an-order"]), {"place-an-order"})

    def test_a_record_with_no_cleared_line_does_not(self) -> None:
        """Four gates run and the fifth not yet is a capability still owed its gates."""
        self.record("place-an-order", "## Gaps\nnone\n\nCleared:\n")
        self.assertEqual(CAPS.cleared("001-orders", ["place-an-order"]), set())


def decisions_gate():
    path = ROOT / "assets/toolkit/scripts/check-decisions.py"
    spec = importlib.util.spec_from_file_location("check_decisions_script", path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class TriggerRecordRowTest(unittest.TestCase):
    """A slice attacks nothing since 2026-10-17: it records its trigger table, and its capability is attacked.

    The trigger record is the slice's row in the adversary log, so `check-decisions` must read it as one, and
    a capability's skip row — nothing widened, nothing attacked — must not trip it either.
    """

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.gate = decisions_gate()
        self.gate.ROOT = Path(self.directory.name)
        self.gate.SPECS = self.gate.ROOT / "specs"
        self.feature = self.gate.SPECS / "001-orders"
        (self.feature / "slices").mkdir(parents=True)
        (self.feature / "slices/README.md").write_text("| Slice | Accepted |\n|---|---|\n| S01 | today |\n",
                                                        encoding="utf-8")

    def test_a_trigger_record_is_the_slice_s_row(self) -> None:
        (self.feature / "adversary-log.md").write_text(
            "## S01 · abc123 · 2026-10-17 · trigger record\n\n| Trigger | Status | Evidence |\n",
            encoding="utf-8")
        self.assertEqual(self.gate.check_adversary_rows(), [])

    def test_a_capability_skip_row_beside_it_is_accepted(self) -> None:
        (self.feature / "adversary-log.md").write_text(
            "## S01 · abc123 · 2026-10-17 · trigger record\n\n"
            "## place-an-order · abc124 · 2026-10-18 · skipped: no slice widened a trigger\n\nSpawned:\n",
            encoding="utf-8")
        self.assertEqual(self.gate.check_adversary_rows(), [])

    def test_no_row_at_all_is_still_refused(self) -> None:
        (self.feature / "adversary-log.md").write_text("", encoding="utf-8")
        self.assertEqual(len(self.gate.check_adversary_rows()), 1)


class DemoStopTest(unittest.TestCase):
    def section(self) -> str:
        return " ".join(demo_stop.demo_stop(event=True).split())

    def test_the_stop_says_it_is_per_capability(self) -> None:
        self.assertIn("per capability, not per slice", self.section())

    def test_the_walk_stops_nobody(self) -> None:
        section = self.section()
        self.assertIn("records a verdict in three words", section)
        self.assertIn("nobody is stopped for that", section.lower())

    def test_the_stop_waits_for_the_capability_gates(self) -> None:
        section = self.section()
        self.assertIn("**Before the stop, the capability gates.**", section)
        self.assertIn("specs/<feature>/capabilities/<capability>/gates.md", section)

    def test_it_names_the_command_that_says_what_is_owed(self) -> None:
        self.assertIn("capabilities.py --due", self.section())

    def test_accepting_is_not_a_release_decision(self) -> None:
        section = self.section()
        self.assertIn("Accepting it is not a release decision", section)
        self.assertIn("nothing here asks about a flag or moves one", section)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
