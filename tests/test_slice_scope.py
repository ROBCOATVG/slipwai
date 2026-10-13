"""`check-slice-scope` reading the chart: the context boundary, held on both profiles.

Version 1's gate found the boundary in `model.yaml`. A standard-profile project has no model, so the gate
found no service and no context, and any code in any deployable passed — the whole boundary was a comment
there. In the experiment it was worse than that: the gate was red for the entire run because the factory's
own manifest declared no deployable, and twenty slices merged with it red.

The chart fixes both, because it exists on either profile and says what each fairway owns. What is held
here is that a slice branch touching another fairway's paths is refused with both fairways named, that a
path no fairway claims is nobody's to refuse, and that a project with no chart loses nothing it had.
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

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-slice-scope.py"

CHART = """
v: 1
feature: ordering
fairways:
  ordering: {context: ordering, service: apps/orders, owns: [apps/orders/**]}
  billing: {context: billing, service: apps/billing, owns: [apps/billing/**]}
marks:
  OrderPlaced: {kind: event, schema: contracts/events/OrderPlaced.json}
slices:
  ORD-01: {fairway: ordering, capability: place-an-order, sets: [OrderPlaced], steers_by: []}
  BIL-01: {fairway: billing, capability: bill-an-order, sets: [], steers_by: [OrderPlaced]}
"""


def gate_module(tree: Path):
    """Load the gate from a tree laid out like a project, which is how it finds its own root."""
    spec = importlib.util.spec_from_file_location(f"scope_{tree.name}", tree / "scripts/check-slice-scope.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


class OwnedPathsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-slice-scope.py")
        (self.tree / "specs/ordering").mkdir(parents=True)
        (self.tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(CHART).lstrip(), encoding="utf-8")
        (self.tree / "project.json").write_text('{"deployables": {}}', encoding="utf-8")
        for argument in ("init -q -b main", "config user.email g@example.com", "config user.name g"):
            subprocess.run(["git", *argument.split()], cwd=self.tree, capture_output=True, check=True)
        self.module = gate_module(self.tree)

    def scope(self, slice_id: str, chart: str | None = None):
        """The gate reading this tree's chart — or a chart written for the test, for the layouts a
        temporary tree has no code in."""
        if chart is not None:
            (self.tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(chart).lstrip(),
                                                                 encoding="utf-8")
        return self.module.Scope(slice_id, "main")

    def test_a_slice_may_touch_what_its_own_fairway_owns(self) -> None:
        self.assertIsNone(self.scope("ORD-01").fairway_violation("apps/orders/src/place.ts"))

    def test_a_slice_may_not_touch_what_another_fairway_owns(self) -> None:
        found = self.scope("ORD-01").fairway_violation("apps/billing/src/invoice.ts")
        assert found is not None
        self.assertIn("owned by fairway `billing`", found)
        self.assertIn("this slice is in `ordering`", found)

    def test_a_service_holding_several_contexts_is_divided_in_every_language(self) -> None:
        """The chart writes `<service>/**/<context>/**` for a service holding several contexts, because the
        directory a context lives in sits at a different depth in every language.

        It used to write `<service>/src/<context>/**`, which is where TypeScript puts one and nowhere Go,
        Java, Python or Rust does — so on those the pattern matched nothing, nothing was owned, and this
        rule refused nothing while reporting the branch in scope. A gate that fails gets fixed; that one
        passed. Both layouts are held here, because the fix must not trade one language for another.
        """
        chart = CHART.replace(
            "ordering: {context: ordering, service: apps/orders, owns: [apps/orders/**]}",
            "ordering: {context: ordering, service: apps/warbook, owns: [apps/warbook/**/ordering/**]}",
        ).replace(
            "billing: {context: billing, service: apps/billing, owns: [apps/billing/**]}",
            "billing: {context: billing, service: apps/warbook, owns: [apps/warbook/**/billing/**]}",
        )
        for path in ("apps/warbook/billing/domain/invoice.go",      # Go, Java, Python, Rust
                     "apps/warbook/src/billing/domain/invoice.ts",  # TypeScript
                     "apps/warbook/internal/billing/invoice.go"):   # and wherever else a language keeps it
            with self.subTest(path=path):
                found = self.scope("ORD-01", chart=chart).fairway_violation(path)
                assert found is not None, f"{path} is owned by billing and nothing refused it"
                self.assertIn("owned by fairway `billing`", found)

    def test_a_context_is_a_whole_segment_and_never_part_of_a_word(self) -> None:
        """`billings/` is not `billing/`. A rule that matched inside a word would refuse a slice for a
        directory that is somebody else's name, which is the opposite failure and just as quiet."""
        chart = CHART.replace(
            "billing: {context: billing, service: apps/billing, owns: [apps/billing/**]}",
            "billing: {context: billing, service: apps/warbook, owns: [apps/warbook/**/billing/**]}",
        )
        self.assertIsNone(self.scope("ORD-01", chart=chart).fairway_violation("apps/warbook/billings/x.go"))

    def test_the_refusal_says_a_mark_is_how_two_fairways_meet(self) -> None:
        """Because the next question a reader has is what to do instead, and there is exactly one answer."""
        found = self.scope("BIL-01").fairway_violation("apps/orders/src/place.ts")
        assert found is not None
        self.assertIn("share nothing but marks", found)

    def test_a_path_no_fairway_claims_is_nobody_s_to_refuse(self) -> None:
        """`owns` says what is divided, not what exists. Other rules still hold these paths."""
        self.assertIsNone(self.scope("ORD-01").fairway_violation("tools/build.sh"))

    def test_a_slice_the_chart_does_not_name_loses_nothing_it_had(self) -> None:
        """The same reading as a branch that is not a slice branch: nothing to hold, not everything refused."""
        self.assertIsNone(self.scope("SHP-09").fairway_violation("apps/billing/src/invoice.ts"))

    def test_a_project_with_no_chart_holds_what_it_always_held(self) -> None:
        (self.tree / "specs/ordering/chart.yaml").unlink()
        module = gate_module(self.tree)
        self.assertIsNone(module.Scope("ORD-01", "main").fairway_violation("apps/billing/src/invoice.ts"))


class UnreadableChartTest(unittest.TestCase):
    """A chart that is there and cannot be parsed is a refusal, never a quiet pass.

    The first version of `load_chart` fell back to the event-model checker's bundled parser, which is
    excluded on the standard profile — the profile this whole boundary was built for. So on a
    standard-profile machine without PyYAML the boundary held nothing while the gate still printed that the
    branch touched only what one slice may. A pass with the chart unread reads exactly like a pass with it
    held, which is the one thing a gate must never do.
    """

    def test_a_chart_that_cannot_be_parsed_is_reported_rather_than_skipped(self) -> None:
        tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tree, True)
        (tree / "scripts").mkdir()
        shutil.copy(GATE, tree / "scripts/check-slice-scope.py")
        (tree / "specs/ordering").mkdir(parents=True)
        (tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(CHART).lstrip(), encoding="utf-8")
        (tree / "project.json").write_text('{"deployables": {}}', encoding="utf-8")
        module = gate_module(tree)
        # No parser, and no event-model checker to borrow one from: the standard profile without PyYAML.
        module.load_chart = lambda text: module.UNREADABLE
        with self.assertRaises(module.ChartUnreadable):
            module.chart_fairways("ORD-01")

    def test_the_scope_records_it_rather_than_losing_it(self) -> None:
        tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tree, True)
        (tree / "scripts").mkdir()
        shutil.copy(GATE, tree / "scripts/check-slice-scope.py")
        (tree / "specs/ordering").mkdir(parents=True)
        (tree / "specs/ordering/chart.yaml").write_text(textwrap.dedent(CHART).lstrip(), encoding="utf-8")
        (tree / "project.json").write_text('{"deployables": {}}', encoding="utf-8")
        for argument in ("init -q -b main", "config user.email g@example.com", "config user.name g"):
            subprocess.run(["git", *argument.split()], cwd=tree, capture_output=True, check=True)
        module = gate_module(tree)
        module.load_chart = lambda text: module.UNREADABLE
        scope = module.Scope("ORD-01", "main")
        self.assertEqual(scope.unreadable, "specs/ordering/chart.yaml")
        self.assertIsNone(scope.fairway, "an unread chart must not read as a slice with no fairway")


class OwnedPatternTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / "scripts").mkdir()
        shutil.copy(GATE, self.tree / "scripts/check-slice-scope.py")
        self.module = gate_module(self.tree)

    def test_a_double_star_entry_is_a_prefix_which_is_what_a_chart_means_by_it(self) -> None:
        owned = self.module.owned_by
        self.assertTrue(owned("apps/orders/src/a/b.ts", ["apps/orders/**"]))
        self.assertTrue(owned("apps/orders", ["apps/orders/**"]))
        self.assertFalse(owned("apps/orders-admin/x.ts", ["apps/orders/**"]),
                         "a sibling whose name starts the same is a different app")

    def test_anything_else_falls_through_to_a_glob_so_a_chart_may_name_one_file(self) -> None:
        self.assertTrue(self.module.owned_by("apps/orders/openapi.yaml", ["apps/*/openapi.yaml"]))
        self.assertFalse(self.module.owned_by("apps/orders/src/x.ts", ["apps/*/openapi.yaml"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
