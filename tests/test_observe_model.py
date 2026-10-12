"""One observed capability, read against a real fixture, passes generated check-model and make chart.

The resulting record is authored as /observe instructs; Markdown commands execute in a person's agent
session, not as parsers. This proof runs its pinned examples, checks evidence against the source, then
uses the actual generated gate and chart rather than asserting only on the command's prose.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
import yaml  # type: ignore[import-untyped]

from slipwai.layout import Layout
from slipwai.origin import Adoption
from slipwai.scaffold import project_files
from slipwai.services import App

TOOLS = Path(__file__).resolve().parents[1] / ".python-tools"
SOURCE = '''\
def confirm_order(order):
    if order["status"] != "draft":
        raise ValueError("only a draft can be confirmed")
    order["status"] = "confirmed"
    order["version"] += 1
    return dict(order)


def order_summary(order):
    return {"id": order["id"], "status": order["status"]}


def order_screen(order):
    return f'<form><output>{order["status"]}</output><button>Confirm order</button></form>'
'''
PINNED = '''\
import unittest
from orders import confirm_order, order_screen, order_summary


class PinnedOrderTests(unittest.TestCase):
    def test_confirm_draft(self):
        order = {"id": "O-1", "status": "draft", "version": 0}
        self.assertEqual(confirm_order(order), {"id": "O-1", "status": "confirmed", "version": 1})
        self.assertEqual(order_summary(order), {"id": "O-1", "status": "confirmed"})
        self.assertIn('<output>confirmed</output>', order_screen(order))

    def test_confirmed_order_is_rejected(self):
        order = {"id": "O-1", "status": "confirmed", "version": 1}
        with self.assertRaisesRegex(ValueError, "only a draft"):
            confirm_order(order)
        self.assertEqual(order["version"], 1)
'''
EXAMPLES = '''\
# Confirm an order — observed examples

Rule 1: A draft may be confirmed.
Given order O-1 is draft at version 0, when confirm_order is called,
then its status is confirmed at version 1 and order_summary displays confirmed.
Pinned by PinnedOrderTests.test_confirm_draft in apps/orders/test_pinned.py:6-10.

Rule 2: A confirmed order cannot be confirmed again.
Given O-1 is confirmed at version 1, when confirm_order is called again,
then it raises "only a draft can be confirmed" and version stays 1.
Pinned by PinnedOrderTests.test_confirmed_order_is_rejected in apps/orders/test_pinned.py:12-16.
Runs with: python3 -m unittest test_pinned, from apps/orders.
'''
EVENTS = '''\
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderDrafted:
    id: str

@dataclass(frozen=True)
class OrderConfirmed:
    id: str
'''
EVENT_HANDLER = '''\
from events import OrderConfirmed

def confirm_order(history):
    if order_summary(history)["status"] != "draft":
        raise ValueError("only a draft can be confirmed")
    history.append(OrderConfirmed(history[0].id))

def order_summary(history):
    return {"id": history[0].id, "status": "confirmed" if any(isinstance(event, OrderConfirmed)
            for event in history) else "draft"}

def order_screen(history):
    return f'<form><output>{order_summary(history)["status"]}</output></form>'
'''
EVENT_TEST = '''\
import unittest
from events import OrderDrafted, OrderConfirmed
from orders import confirm_order, order_summary

class PinnedEventOrderTests(unittest.TestCase):
    def test_confirm_draft(self):
        history = [OrderDrafted("O-1")]
        confirm_order(history)
        self.assertEqual(history, [OrderDrafted("O-1"), OrderConfirmed("O-1")])
        self.assertEqual(order_summary(history), {"id": "O-1", "status": "confirmed"})
'''


class ObservedCapabilityProof(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.use_make = os.name != "nt"
        self.layout = Layout("delivery")
        self.app = App("orders", "apps/orders", "service", "python", None, 0, generated=False,
                       commands={"test": "python3 -m unittest test_pinned"},
                       provenance={"kind": "confirmed", "language": "confirmed"},
                       toolchain={"kind": "python", "ecosystem": "python"})
        for relative, content in project_files("shop", "event-modelling", "none", [self.app],
                                                self.layout, Adoption()).items():
            self.write(relative, content)
        self.write("apps/orders/orders.py", SOURCE)
        self.write("apps/orders/test_pinned.py", PINNED)
        self.write("specs/ordering/slices/ORD-OBS/examples.md", EXAMPLES)
        self.write("specs/ordering/slices/ORD-VIEW/examples.md", EXAMPLES)
        self.write("delivery/docs/event-model/mockups/order.txt",
                   "+ Order O-1 +\n| Status: draft / confirmed |\n| [Confirm order] |\n")
        self.write("delivery/survey/pinned.md",
                   "| Behaviour | Seam | Tests | Runs with |\n| Confirm order | handler | "
                   "apps/orders/test_pinned.py | python3 -m unittest test_pinned |\n")
        self.write("specs/ordering/observations/confirm-order.md", """# Observe confirm-order

Source: state columns and their writes; project.json orders.eventSourced is false.

## Extraction — table orders

| Column | Transition | Business fact | Write read off | Pinned example |
|---|---|---|---|---|
| status | draft → confirmed | OrderConfirmed | apps/orders/orders.py:4 | apps/orders/test_pinned.py:8 |

First move: ORD-VIEW, state-view over orders' own current data; the write path remains unchanged.
""")
        self.model = self.observed_model()
        self.save_model()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def run_command(self, *argv: str, here: str = ".") -> subprocess.CompletedProcess[str]:
        commands = [list(argv)]
        if argv[0] == "python3":
            commands = [[sys.executable, *argv[1:]]]
        if argv[0] == "make" and not self.use_make:
            # CI's Windows leg has Python and Git, not make. Run the exact generated target scripts;
            # the Unix proof still exercises the actual generated Makefile and its relocated recipes.
            scripts = {"check-model": "delivery/scripts/event-model/check.py",
                       "chart": "delivery/scripts/event-model/chart.py",
                       "check-chart": "delivery/scripts/check-chart.py"}
            self.assertEqual(argv[1:3], ("-f", "delivery/Makefile"))
            commands = [[sys.executable, scripts[target]] for target in argv[3:]]
        stdout, stderr, code = [], [], 0
        for command in commands:
            result = subprocess.run(command, cwd=self.root / here, capture_output=True, text=True, timeout=30,
                                    env={**os.environ, "PYTHONPATH": str(TOOLS)})
            stdout.append(result.stdout)
            stderr.append(result.stderr)
            code = result.returncode
            if code:
                break
        return subprocess.CompletedProcess(argv, code, "".join(stdout), "".join(stderr))

    def checked(self, *argv: str, here: str = ".") -> str:
        result = self.run_command(*argv, here=here)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def observed_model(self) -> dict:
        ui = {"type": "ui", "name": "order_screen", "mockups": [
            {"state": "draft", "at": "delivery/docs/event-model/mockups/order.txt"},
            {"state": "confirmed", "at": "delivery/docs/event-model/mockups/order.txt"}]}
        shared = {"capability": "confirm-order", "service": "orders", "context": "orders",
                  "status": "observed", "actor": "clerk", "code": ["apps/orders/orders.py"]}
        return {"version": 1, "slices": [
            {**shared, "id": "ORD-OBS", "pattern": "state-change", "stream": "orders.id",
             "gwt": "specs/ordering/slices/ORD-OBS/examples.md", "frames": [ui,
                 {"type": "cmd", "name": "ConfirmOrder", "data": "order: id, status, version"},
                 {"type": "evt", "name": "OrderConfirmed", "attributes": [
                     {"name": "id", "type": "string", "identifies": "order"},
                     {"name": "version", "type": "number"}]}]},
            {**shared, "id": "ORD-VIEW", "pattern": "state-view", "reads": ["OrderConfirmed"],
             "materialisation": "live", "gwt": "specs/ordering/slices/ORD-VIEW/examples.md", "frames": [
                 {"type": "rmo", "name": "order_summary", "data": "id, status"}, ui]},
        ]}

    def save_model(self) -> None:
        self.write("delivery/docs/event-model/model.yaml", yaml.safe_dump(self.model, sort_keys=False))

    def test_one_capability_has_real_pinned_evidence_and_the_generated_gates_accept_it(self) -> None:
        self.checked("python3", "-m", "unittest", "test_pinned", here="apps/orders")
        self.assertEqual(SOURCE.splitlines()[3], '    order["status"] = "confirmed"')
        command = (self.root / "delivery/commands/observe.md").read_text()
        self.assertIn("make -f delivery/Makefile check-model", command)
        self.checked("make", "-f", "delivery/Makefile", "check-model", "chart", "check-chart")
        chart = yaml.safe_load((self.root / "specs/ordering/chart.yaml").read_text())
        self.assertEqual(chart["slices"]["ORD-OBS"]["sets"], ["OrderConfirmed"])
        self.assertIs(chart["slices"]["ORD-OBS"]["observed"], True)
        self.assertEqual(chart["slices"]["ORD-VIEW"]["steers_by"], ["OrderConfirmed"])
        self.assertTrue(all(item["status"] == "observed" for item in self.model["slices"]))
        self.assertEqual(self.model["slices"][0]["frames"][0]["type"], "ui")
        self.assertEqual((self.root / "apps/orders/orders.py").read_text(), SOURCE)

    def test_a_row_operation_name_fails_the_real_gate_before_chart_rendering(self) -> None:
        self.model["slices"][0]["frames"][2]["name"] = "OrdersUpdated"
        self.model["slices"][1]["reads"] = ["OrdersUpdated"]
        self.save_model()
        result = self.run_command("make", "-f", "delivery/Makefile", "check-model")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OrdersUpdated", result.stdout + result.stderr)

    def test_the_no_make_path_runs_real_targets_and_preserves_first_failure(self) -> None:
        self.use_make = False
        self.checked("make", "-f", "delivery/Makefile", "check-model", "chart", "check-chart")
        chart = self.root / "specs/ordering/chart.yaml"
        self.assertTrue(chart.is_file())
        chart.unlink()
        self.model["slices"][0]["frames"][2]["name"] = "OrdersUpdated"
        self.model["slices"][1]["reads"] = ["OrdersUpdated"]
        self.save_model()
        result = self.run_command("make", "-f", "delivery/Makefile", "check-model", "chart", "check-chart")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OrdersUpdated", result.stdout + result.stderr)
        self.assertFalse(chart.exists(), "a failed check-model must stop before chart rendering")

    def test_a_relocated_model_without_slice_identity_refuses_chart_rendering(self) -> None:
        del self.model["slices"][0]["id"]
        self.save_model()
        result = self.run_command("make", "-f", "delivery/Makefile", "chart")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no `id`", result.stdout + result.stderr)
        self.assertFalse((self.root / "specs/ordering/chart.yaml").exists())

    def test_the_relocated_chart_gate_detects_drift_from_its_model(self) -> None:
        self.checked("make", "-f", "delivery/Makefile", "chart")
        path = self.root / "specs/ordering/chart.yaml"
        path.write_text(path.read_text().replace("confirm-order", "other-capability"))
        result = self.run_command("make", "-f", "delivery/Makefile", "check-chart")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("disagree(s)", result.stdout + result.stderr)

    def test_the_confirmed_events_rung_reads_existing_event_evidence(self) -> None:
        self.write("apps/orders/events.py", EVENTS)
        self.write("apps/orders/orders.py", EVENT_HANDLER)
        self.write("apps/orders/test_events.py", EVENT_TEST)
        self.checked("python3", "-m", "unittest", "test_events", here="apps/orders")
        self.write("specs/ordering/observations/confirm-order.md", """# Observe confirm-order

Source: confirmed events; orders.writeModel=events, provenance.writeModel=confirmed.

| Event type | Producer | Module | Pinned example |
|---|---|---|---|
| OrderConfirmed | apps/orders/orders.py:6 | apps/orders/events.py:8 | apps/orders/test_events.py:9 |

First move: ORD-VIEW, state-view over the wrapped service's existing projection.
""")
        for slice_id in ("ORD-OBS", "ORD-VIEW"):
            self.write(f"specs/ordering/slices/{slice_id}/examples.md", """# Observed event examples

Given history [OrderDrafted(O-1)], when confirm_order executes,
then the log contains [OrderDrafted(O-1), OrderConfirmed(O-1)] and order_summary shows confirmed.
Pinned by PinnedEventOrderTests.test_confirm_draft, apps/orders/test_events.py:6-10.
Runs with: python3 -m unittest test_events, from apps/orders.
""")
        document = json.loads((self.root / "project.json").read_text())
        document["deployables"]["orders"].update({"eventSourced": True, "writeModel": "events"})
        document["deployables"]["orders"]["provenance"]["writeModel"] = "confirmed"
        self.write("project.json", json.dumps(document))
        self.model["slices"][0]["code"].append("apps/orders/events.py")
        self.model["slices"][0]["stream"] = "order.id"
        self.model["slices"][0]["frames"][1]["data"] = "history"
        self.model["slices"][0]["frames"][2]["attributes"] = [{"name": "id", "type": "string",
                                                              "identifies": "order"}]
        self.model["slices"][1]["liveBudget"] = {"events": 10, "because": "one order stream"}
        self.save_model()
        self.checked("make", "-f", "delivery/Makefile", "check-model", "chart", "check-chart")


if __name__ == "__main__":
    unittest.main()
