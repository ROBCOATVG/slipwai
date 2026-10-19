"""`make chart` on the event profile: the chart derived from the model, never written beside it.

The model already names each slice's context and service, types the events each slice produces, and says
what each slice reads. So the chart is not authored here, it is rendered — and `check-chart` refuses a
committed chart that has drifted from the model, the way `make check-drawio` holds the committed canvas.
Two answers to one question diverge silently, because nothing else reads both.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
from test_chart_contexts import decided

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "assets/toolkit/scripts/check-chart.py"


def chart_module() -> Any:
    """The renderer, loaded from the toolkit. It runs in a project, so it is not importable by name."""
    import importlib.util
    specification = importlib.util.spec_from_file_location(
        "toolkit_chart", ROOT / "assets/toolkit/scripts/event-model/chart.py")
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


chart = chart_module()

MODEL = """
version: 1
slices:
  - id: PlaceOrder
    context: ordering
    service: orders
    capability: place-an-order
    pattern: state-change
    frames:
      - {type: ui, name: Cart}
      - {type: cmd, name: PlaceOrder}
      - {type: evt, name: OrderPlaced}
  - id: RaiseInvoice
    context: billing
    service: billing
    capability: bill-an-order
    pattern: automation
    reads: [OrderPlaced]
    frames:
      - {type: rmo, name: PlacedOrders}
      - {type: pcr, name: Invoicer}
      - {type: cmd, name: RaiseInvoice}
      - {type: evt, name: InvoiceRaised}
"""
MANIFEST = """
{"deployables": {"orders": {"kind": "service", "path": "apps/orders", "contexts": ["ordering"]},
                 "billing": {"kind": "service", "path": "apps/billing", "contexts": ["billing", "tax"]}}}
"""


class RenderedChartTest(unittest.TestCase):
    """`make chart` on the event profile: the chart is derived from the model, never written beside it."""

    def setUp(self) -> None:
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, True)
        for directory in ("scripts/event-model", "docs/event-model", "specs/ordering/slices"):
            (self.tree / directory).mkdir(parents=True)
        shutil.copy(ROOT / "assets/toolkit/scripts/event-model/chart.py", self.tree / "scripts/event-model/chart.py")
        shutil.copy(GATE, self.tree / "scripts/check-chart.py")
        (self.tree / "docs/event-model/model.yaml").write_text(textwrap.dedent(MODEL).lstrip(), encoding="utf-8")
        (self.tree / "project.json").write_text(textwrap.dedent(MANIFEST).lstrip(), encoding="utf-8")
        decided(self.tree)  # the context decision `check-chart` asks the fairways for

    def render(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "scripts/event-model/chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)

    def chart(self) -> dict:
        import yaml  # type: ignore[import-untyped]
        loaded = yaml.safe_load((self.tree / "specs/ordering/chart.yaml").read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)
        return loaded

    def test_the_model_renders_a_chart_the_gate_accepts(self) -> None:
        self.assertEqual(self.render().returncode, 0)
        done = subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_fairway_per_context_owning_what_that_context_holds(self) -> None:
        """A service with one context owns all of it; one holding several owns the context's own directory,
        at whatever depth its language keeps it.

        This asserted `apps/billing/src/billing/**` and so pinned the bug it was written to describe: `src/`
        is where a TypeScript service puts a context and nowhere a Go, Java, Python or Rust one does, and a
        pattern matching no file claims no file. The fairway rule refuses a path another fairway owns, so
        with nothing owned it refused nothing and reported every branch in scope.
        """
        self.render()
        fairways = self.chart()["fairways"]
        self.assertEqual(sorted(fairways), ["billing", "ordering"])
        self.assertEqual(fairways["ordering"]["owns"], ["apps/orders/**"])
        self.assertEqual(fairways["billing"]["owns"], ["apps/billing/**/billing/**"])

    def test_an_event_mark_points_at_the_model_rather_than_a_generated_schema(self) -> None:
        """Generating JSON Schema would mean inventing a type mapping, and that mapping would be the
        contract every other fairway steers by — a type system invented in a renderer, by nobody."""
        self.render()
        self.assertEqual(self.chart()["marks"]["OrderPlaced"],
                         {"kind": "event", "schema": "docs/event-model/model.yaml#OrderPlaced"})

    def test_what_a_slice_sets_and_steers_by_comes_from_its_frames_and_its_reads(self) -> None:
        self.render()
        slices = self.chart()["slices"]
        self.assertEqual(slices["PlaceOrder"]["sets"], ["OrderPlaced"])
        self.assertEqual(slices["PlaceOrder"]["steers_by"], [])
        self.assertEqual(slices["RaiseInvoice"]["steers_by"], ["OrderPlaced"])
        self.assertEqual(slices["RaiseInvoice"]["capability"], "bill-an-order")

    def test_rendering_twice_writes_the_same_chart(self) -> None:
        """A chart that churns on every render is a chart nobody can read a diff of."""
        self.render()
        first = (self.tree / "specs/ordering/chart.yaml").read_text(encoding="utf-8")
        self.render()
        self.assertEqual(first, (self.tree / "specs/ordering/chart.yaml").read_text(encoding="utf-8"))

    def test_a_chart_edited_by_hand_is_refused_against_the_model(self) -> None:
        """The model is the source of truth on this profile, so the chart is derived and never authored."""
        self.render()
        path = self.tree / "specs/ordering/chart.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("bill-an-order", "something-else"),
                        encoding="utf-8")
        done = subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("disagree(s) with docs/event-model/model.yaml", done.stderr)
        self.assertIn("run `make chart`", done.stderr)

    def test_the_chart_keeps_the_order_the_model_lists_its_slices_in(self) -> None:
        """Slice 18.1. The order of the `slices` block is the order every captain takes them in, so it is
        a decision — and a decision is taken by the split and written down, never spelled by whatever the
        ids happen to sort as. The renderer used to sort by id, which made `BIL-01` run before `ORD-01`
        for no reason anybody had given."""
        self.render()
        self.assertEqual(list(self.chart()["slices"]), ["PlaceOrder", "RaiseInvoice"])
        path = self.tree / "docs/event-model/model.yaml"
        model = path.read_text(encoding="utf-8")
        first = model.index("  - id: PlaceOrder")
        path.write_text(model[:first] + "\n".join(
            [model[model.index("  - id: RaiseInvoice"):].rstrip(),
             model[first:model.index("  - id: RaiseInvoice")].rstrip(), ""]), encoding="utf-8")
        self.render()
        self.assertEqual(list(self.chart()["slices"]), ["RaiseInvoice", "PlaceOrder"])
        # And the fairways with them: with 18.2 that block's order is which captain is lit first, so the
        # alphabet must not be what decides it either.
        self.assertEqual(list(self.chart()["fairways"]), ["billing", "ordering"])

    def test_a_chart_in_a_different_order_from_the_model_is_drift(self) -> None:
        """The same rows in another order are another decision about what runs first, so the gate reads
        them as disagreeing and names the first row that differs."""
        import yaml
        self.render()
        path = self.tree / "specs/ordering/chart.yaml"
        held = yaml.safe_load(path.read_text(encoding="utf-8"))
        held["slices"] = dict(reversed(list(held["slices"].items())))
        path.write_text(yaml.safe_dump(held, sort_keys=False), encoding="utf-8")
        done = subprocess.run([sys.executable, "scripts/check-chart.py"], cwd=self.tree,
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("RaiseInvoice", done.stderr)
        self.assertIn("order", done.stderr)
        self.assertIn("run `make chart`", done.stderr)

    def test_a_project_with_no_model_is_told_which_stage_writes_its_chart(self) -> None:
        (self.tree / "docs/event-model/model.yaml").unlink()
        done = self.render()
        self.assertEqual(done.returncode, 0)
        self.assertIn("written by /chart on this profile", done.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class SingleServiceTest(unittest.TestCase):
    """Found by generating a real project and running the loop in it, 2026-10-07.

    A project with one service and a web app has two deployables and still nothing to decide about which
    one owns a slice — so `service` is optional on the model's slice. The renderer resolved only the named
    one, left `fairways` empty, and wrote a chart whose every slice named a fairway the chart had not got.
    `check-chart` then refused the chart the renderer had just written, which is the worst pairing of a
    generator and its gate there is.
    """

    def test_the_only_service_owns_a_slice_that_names_none(self) -> None:
        deployables = {"service": {"kind": "service", "path": "apps/service"},
                       "web": {"kind": "web", "path": "apps/web"}}
        self.assertEqual(chart.only_service(deployables), "service")

    def test_a_web_app_is_never_the_one(self) -> None:
        """Resolving to it would put a context's code in the browser."""
        self.assertIsNone(chart.only_service({"web": {"kind": "web", "path": "apps/web"}}))

    def test_two_services_is_a_decision_and_is_left_to_the_slice(self) -> None:
        deployables = {"a": {"kind": "service"}, "b": {"kind": "service"}}
        self.assertIsNone(chart.only_service(deployables))

    def test_a_chart_the_renderer_writes_names_every_fairway_its_slices_name(self) -> None:
        """The pairing rule: whatever the renderer writes, the gate accepts."""
        model = {"slices": [
            {"id": "ORD-01", "context": "ordering", "capability": "Ordering",
             "frames": [{"type": "evt", "name": "OrderPlaced"}]},
            {"id": "BIL-01", "context": "billing", "capability": "Ordering",
             "frames": [{"type": "evt", "name": "OrderCharged"}]},
        ]}
        found = chart.render(model, {"service": {"kind": "service", "path": "apps/service"},
                                     "web": {"kind": "web", "path": "apps/web"}})
        named = {body["fairway"] for body in found["slices"].values()}
        self.assertTrue(named <= set(found["fairways"]), f"{named} vs {set(found['fairways'])}")


class UnreadableSliceTest(unittest.TestCase):
    """A model with three slices and no `id` on any of them rendered an empty chart and said "0 slices"
    as a success. A renderer that drops what it cannot read makes a chart with holes in it, and a chart
    with holes is what the whole of clearance then believes."""

    def test_a_slice_with_no_id_is_named_rather_than_dropped(self) -> None:
        found = chart.unreadable({"slices": [{"name": "Place an order"}, {"id": "ORD-01"}]})
        self.assertEqual(len(found), 1)
        self.assertIn("slice 1", found[0])

    def test_a_model_whose_slices_all_read_has_nothing_to_say(self) -> None:
        self.assertEqual(chart.unreadable({"slices": [{"id": "ORD-01"}]}), [])

    def test_a_model_with_no_slices_at_all_is_not_a_fault(self) -> None:
        self.assertEqual(chart.unreadable({"slices": []}), [])
        self.assertEqual(chart.unreadable({}), [])
