"""The split's surfaces against what a person approved, in both directions.

Both failures this gate catches are silent. A slice that delivers a state nobody approved is built against
something never agreed, which in version 1 was found at the demo of the slice that built it. And an approved
state no slice delivers is the one nobody would otherwise notice at all: a person looked at a drawing, said
yes, and the split did not carry it — afterwards an unbuilt surface looks exactly like a surface nobody
asked for, with no error and no gap in the tests to find it by.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-surfaces.py"

STATES = """
## Surface: Order confirmation
- populated — approved
- empty cart — approved
- offline — n/a: server-rendered, there is no offline mode
- partial refund — parked: waiting on whether partial refunds exist (inbox 2026-10-07)
"""

SPLIT = """
## Split Candidates
| Slice | Value | Includes | Defers | Surfaces and states | Acceptance Examples | Release Constraint |
|---|---|---|---|---|---|---|
| ORD-01 | places an order | the path | refunds | Order confirmation · populated | one | none |
| ORD-02 | handles an empty cart | the guard | — | Order confirmation · empty cart | one | none |
"""


class SurfaceGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-surfaces.py")
        (self.tree / "project.json").write_text("{}", encoding="utf-8")
        (self.tree / "specs/ordering/mockups").mkdir(parents=True)
        spec = importlib.util.spec_from_file_location("surfaces", self.tree / "scripts/check-surfaces.py")
        assert spec is not None and spec.loader is not None
        self.module = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(self.module)

    def write(self, states: str = STATES, split: str = SPLIT) -> None:
        (self.tree / "specs/ordering/mockups/mock-states.md").write_text(
            textwrap.dedent(states).lstrip(), encoding="utf-8")
        (self.tree / "specs/ordering/story-split.md").write_text(
            textwrap.dedent(split).lstrip(), encoding="utf-8")

    def run_gate(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "scripts/check-surfaces.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)

    def test_a_split_that_delivers_exactly_the_approved_states_passes(self) -> None:
        self.write()
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_slice_delivering_a_parked_state_is_refused_and_says_it_is_parked(self) -> None:
        """A parked state is a question still open, not a thing to build against."""
        self.write(split=SPLIT.replace("Order confirmation · empty cart",
                                       "Order confirmation · partial refund"))
        done = self.run_gate()
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("it is `parked` there", done.stderr)

    def test_a_slice_delivering_a_state_nobody_has_seen_is_refused(self) -> None:
        self.write(split=SPLIT.replace("Order confirmation · empty cart",
                                       "Order confirmation · bulk upload"))
        done = self.run_gate()
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("not in that surface's states at all", done.stderr)

    def test_a_slice_delivering_a_surface_nobody_has_seen_is_refused(self) -> None:
        self.write(split=SPLIT.replace("Order confirmation · empty cart", "Admin console · populated"))
        done = self.run_gate()
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("Nobody has seen it", done.stderr)

    def test_an_approved_state_no_slice_delivers_is_refused(self) -> None:
        """The direction nobody would otherwise notice."""
        self.write(split=SPLIT.replace(
            "| ORD-02 | handles an empty cart | the guard | — | Order confirmation · empty cart | one | none |\n", ""))
        done = self.run_gate()
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("was approved and no slice delivers it", done.stderr)
        self.assertIn("looks exactly like a surface nobody asked for", done.stderr)

    def test_two_slices_delivering_one_state_is_refused(self) -> None:
        both = "Order confirmation · populated; Order confirmation · empty cart"
        self.write(split=SPLIT.replace("| Order confirmation · empty cart |", f"| {both} |"))
        done = self.run_gate()
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("One state is one slice's", done.stderr)

    def test_several_states_in_one_cell_are_read(self) -> None:
        self.write(split=SPLIT.replace(
            "| ORD-02 | handles an empty cart | the guard | — | Order confirmation · empty cart | one | none |\n", "")
            .replace("Order confirmation · populated",
                     "Order confirmation · populated; Order confirmation · empty cart"))
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_state_marked_not_applicable_need_not_be_delivered(self) -> None:
        """`n/a` carries its reason and is a decision, not an omission."""
        self.write()
        self.assertEqual(self.run_gate().returncode, 0)

    def test_a_feature_with_no_surfaces_passes_with_the_column_empty(self) -> None:
        empty = SPLIT.replace("Order confirmation · populated", "")
        self.write(states="surfaces: none — a migration, with nothing a person meets\n",
                   split=empty.replace("Order confirmation · empty cart", ""))
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_feature_that_says_no_surfaces_and_then_names_one_is_refused(self) -> None:
        self.write(states="surfaces: none — a migration, with nothing a person meets\n")
        done = self.run_gate()
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("One of the two is wrong", done.stderr)

    def test_a_feature_that_has_not_run_the_stage_is_not_a_failure(self) -> None:
        """Whether the stage ran is the mock-up review rung's business, not this gate's."""
        (self.tree / "specs/ordering/story-split.md").write_text(textwrap.dedent(SPLIT).lstrip(),
                                                                 encoding="utf-8")
        done = self.run_gate()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("nothing to hold", done.stdout)

    def test_every_refusal_ends_on_the_command_that_fixes_it(self) -> None:
        self.write(split=SPLIT.replace("Order confirmation · empty cart", "Order confirmation · partial refund"))
        self.assertIn("Run: python3 scripts/check-surfaces.py", self.run_gate().stderr)


class RedrawTest(unittest.TestCase):
    """`make surfaces` after a disapproval draws again, rather than reviewing the drafts it was told no to."""

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        sys.path.insert(0, str(ROOT / "assets/toolkit/scripts/agents"))
        self.addCleanup(sys.path.remove, str(ROOT / "assets/toolkit/scripts/agents"))
        spec = importlib.util.spec_from_file_location(
            "surfaces_stage", ROOT / "assets/toolkit/scripts/agents/surfaces.py")
        assert spec is not None and spec.loader is not None
        module: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.SPECS = self.tree / "specs"
        self.module = module
        self.home = self.tree / "specs/001-orders/mockups"
        self.home.mkdir(parents=True)

    def states(self, body: str) -> None:
        (self.home / "mock-states.md").write_text(body, encoding="utf-8")

    def test_a_first_drawing_is_not_a_redraw(self) -> None:
        self.assertEqual(self.module.turned_down("001-orders"), "")

    def test_every_state_parked_is_a_storyboard_turned_down(self) -> None:
        self.states("## Surface: Basket\n- Empty \u2014 parked: no styling\n- Full \u2014 parked: no styling\n")
        self.assertIn("no styling", self.module.turned_down("001-orders"))

    def test_a_storyboard_part_way_through_its_verdicts_is_not_redrawn(self) -> None:
        """Some approved is a person in the middle of `/mockups`, and a redraw would throw that away."""
        self.states("## Surface: Basket\n- Empty \u2014 approved\n- Full \u2014 parked: is a total shown?\n")
        self.assertEqual(self.module.turned_down("001-orders"), "")

    def test_the_old_verdicts_are_kept_and_the_new_drawing_waits_on_its_own(self) -> None:
        said = "## Surface: Basket\n- Empty \u2014 parked: no styling\n"
        self.states(said)
        self.module.retire("001-orders", said)
        self.states(said.replace("no styling", "still none"))
        self.module.retire("001-orders", said.replace("no styling", "still none"))
        self.assertFalse((self.home / "mock-states.md").exists())
        kept = (self.home / "disapproved.md").read_text(encoding="utf-8")
        self.assertEqual(kept.count("## Redrawn"), 2)
        self.assertLess(kept.index("no styling"), kept.index("still none"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
