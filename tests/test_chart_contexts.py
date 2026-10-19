"""`check-chart`'s seventh rule: a chart's fairways come from a context decision somebody can read.

Apart from `test_chart.py` because the fixture is shared: every suite whose tree reaches `check-chart` —
the rendered chart, the loop, the observed model — writes the same decision entry through `decided`, so the
shape the gate asks for is stated once.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-chart.py"
WHOLE = """
v: 1
feature: ordering
fairways:
  ORD: {context: ordering, service: apps/orders, owns: [apps/orders/**]}
  BIL: {context: billing, service: apps/billing, owns: [apps/billing/**]}
marks:
  OrderPlaced: {kind: event, schema: contracts/events/OrderPlaced.json}
  InvoiceRaised: {kind: event, schema: contracts/events/InvoiceRaised.json}
slices:
  ORD-01: {fairway: ORD, capability: place-an-order, sets: [OrderPlaced], steers_by: []}
  BIL-01: {fairway: BIL, capability: bill-an-order, sets: [InvoiceRaised], steers_by: [OrderPlaced]}
"""

#: Pass one's context answer, in the shape `check-decisions` holds, with the seam table it was read off. Every
#: chart with fairways owes one since the gate's seventh rule, so every fixture tree carries it.
CONTEXT_DECISION = """# Decisions

## D1 — Which bounded contexts does ordering touch?
- **Stage:** chart · **Slice:** — · **When:** 2026-10-19T09:00:00Z · **Stream:** ORD
- **Question:** Which bounded contexts does ordering touch, and is each one fairway?
- **Options:** one context; ordering and billing (recommended)
  | Candidate | Entities | Language · Change · Flow | What crosses | Confidence |
  |---|---|---|---|---|
  | ordering | Order | spec.md:12 order is a cart · prices change for sales · the customer | OrderPlaced | high |
  | billing | Invoice | spec.md:30 order is a debt · tax rules change · finance | — | high |
- **Decision:** two contexts, two fairways
- **Why:** the change and flow tests both fail across the seam · **Read against:** the specification
- **Decided by:** host (stage recommendation)
- **Confidence:** high · **Would reverse if:** billing turned out to price the order itself
- **Written to:** `specs/ordering/chart.yaml`
- **Status:** awaiting human confirmation
"""


def decided(tree: Path, text: str = CONTEXT_DECISION, feature: str = "ordering") -> None:
    """Write the feature's context decision, as pass one now always does. Other suites whose trees reach
    `check-chart` call this too, so the one fixture is the shape every one of them carries."""
    (tree / f"specs/{feature}").mkdir(parents=True, exist_ok=True)
    (tree / f"specs/{feature}/decisions.md").write_text(text.replace("ordering", feature), encoding="utf-8")


class ContextDecisionTest(unittest.TestCase):
    """Rule seven: the fairways were derived from a context decision somebody can read.

    A headless run once wrote "one context, so one fairway" into the split with no seam test, no table and no
    decision entry, and thirty-one slices queued behind one captain. The gate looked at the chart, found it
    whole, and passed it, because nothing asked where its one fairway came from.
    """

    ONE = """
    v: 1
    feature: ordering
    fairways:
      leaver: {context: leaver, service: apps/hr, owns: [apps/hr/**]}
    marks: {}
    slices:
    %s
    """

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-chart.py")
        (self.tree / "specs/ordering").mkdir(parents=True)
        (self.tree / "contracts/events").mkdir(parents=True)
        for event in ("OrderPlaced", "InvoiceRaised"):
            (self.tree / f"contracts/events/{event}.json").write_text("{}", encoding="utf-8")

    def run_gate(self, chart: str) -> subprocess.CompletedProcess[str]:
        (self.tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(chart).lstrip(), encoding="utf-8")
        return subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)

    def single(self, slices: int) -> str:
        rows = "\n    ".join(f"  S{n}: {{fairway: leaver, capability: leave, sets: [], steers_by: []}}"
                             for n in range(1, slices + 1))
        return self.ONE % rows

    def test_one_fairway_with_no_decision_is_refused_and_told_how_to_fix_it(self) -> None:
        done = self.run_gate(self.single(3))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("one fairway, `leaver`, and no recorded decision says why", done.stderr)
        self.assertIn("Which bounded contexts does ordering touch?", done.stderr)
        self.assertIn("seam table", done.stderr)

    def test_several_fairways_with_no_decision_are_refused_too(self) -> None:
        done = self.run_gate(WHOLE)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("2 fairways and no recorded decision", done.stderr)

    def test_a_decision_with_no_seam_table_is_refused(self) -> None:
        decided(self.tree, "\n".join(line for line in CONTEXT_DECISION.splitlines() if "|" not in line))
        done = self.run_gate(WHOLE)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("carries no seam table", done.stderr)

    def test_a_legitimately_single_context_feature_passes_once_its_decision_is_recorded(self) -> None:
        decided(self.tree, CONTEXT_DECISION.replace("two contexts, two fairways", "one context, one fairway"))
        done = self.run_gate(self.single(3))
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_crowded_fairway_owes_the_invariant_that_keeps_it_whole(self) -> None:
        decided(self.tree)
        done = self.run_gate(self.single(13))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("`leaver` (13 slices) holds more than 12 slices", done.stderr)
        self.assertIn("Why not split:", done.stderr)

    def test_a_crowded_fairway_passes_with_its_why_not_split_said(self) -> None:
        decided(self.tree, CONTEXT_DECISION.replace(
            "- **Decision:**", "- **Why not split:** every approval reads the whole case at once (FR-3)\n"
                               "- **Decision:**"))
        self.assertEqual(self.run_gate(self.single(13)).returncode, 0)

    def test_twelve_is_not_crowded(self) -> None:
        decided(self.tree)
        self.assertEqual(self.run_gate(self.single(12)).returncode, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
