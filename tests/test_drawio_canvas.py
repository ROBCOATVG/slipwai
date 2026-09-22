"""The committed draw.io canvas: written by `make model-drawio`, held current by `make check-drawio`.

Every case runs the targets a generated project actually invokes, over one generated project, because the
whole point of the canvas is the gate: `check-drawio` sits inside `verify` and has to fail on a stale or
missing file with the fix in its message, and pass byte for byte on a regenerated one.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from support import FactoryTestCase

MODEL_HEADER = "version: 1\nrender:\n  lanes:\n    ui: actor\n    data: none\n    events: stream\n"
SLICES = (
    "slices:\n"
    "  - id: S1\n    name: Place an order\n    pattern: state-change\n    status: modelled\n"
    "    actor: Guest\n    stream: order-{orderId}\n"
    "    frames:\n      - {type: ui, name: CheckoutScreen}\n"
    "      - {type: cmd, name: PlaceOrder}\n      - {type: evt, name: OrderPlaced}\n"
    "  - id: S2\n    name: Take payment\n    pattern: automation\n    status: modelled\n"
    "    actor: PaymentProcessor\n    context: billing\n    reads: [OrderPlaced]\n"
    "    materialisation: async\n"
    "    guard:\n      by: [order]\n      because: an order is charged once\n"
    "    frames:\n      - {type: rmo, name: Unpaid}\n      - {type: pcr, name: ChargeOnPlaced}\n"
    "      - {type: cmd, name: Charge}\n      - {type: evt, name: Charged}\n"
    "  - id: S3\n    name: See what was charged\n    pattern: state-view\n    status: modelled\n"
    "    actor: Guest\n    reads: [OrderPlaced, Charged]\n"
    "    frames:\n      - {type: rmo, name: Charges}\n"
)


def run(repo: Path, *target: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["make", *target], cwd=repo, text=True, capture_output=True)


class DrawioCanvasTest(FactoryTestCase):
    def test_the_canvas_is_written_checked_and_proved_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "canvas", language="python")
            makefile = (repo / "Makefile").read_text()
            # In `verify`, after the model's own gate: a canvas reachable only by name is a canvas nobody checks.
            self.assertRegex(makefile, r"verify: [^\n]*\bcheck-model check-drawio\b")
            for target in ("model-drawio:", "check-drawio:", "model-drawio-test:"):
                self.assertIn(target, makefile)
            # The verify workflow gives a project with no Node of its own one, for exactly this gate.
            workflow = (repo / ".github/workflows/verify.yml").read_text()
            self.assertIn("actions/setup-node@v6", workflow)
            self.assertNotIn("cache: npm", workflow)

            canvas = repo / "docs/event-model/model.drawio"
            model = repo / "docs/event-model/model.yaml"

            # The shipped model is empty: no canvas, and nothing to check — but not a failure either.
            empty = run(repo, "check-drawio")
            self.assertEqual(empty.returncode, 0, empty.stderr)
            self.assertIn("no slices yet", empty.stdout)
            self.assertFalse(canvas.exists())

            model.write_text(MODEL_HEADER + SLICES)
            # A model with slices and no canvas is the missing case, told apart from the stale one.
            missing = run(repo, "check-drawio")
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("is missing", missing.stderr)
            self.assertIn("Run make model-drawio and commit the result", missing.stderr)

            written = run(repo, "model-drawio")
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertTrue(canvas.is_file())
            first = canvas.read_bytes()
            self.assertTrue(first.endswith(b"</mxfile>\n"))
            current = run(repo, "check-drawio")
            self.assertEqual(current.returncode, 0, current.stderr)
            self.assertIn("is current", current.stdout)

            # The file is well-formed XML, ids are unique, every parent resolves, and nothing carries a clock.
            root = ET.fromstring(first)
            self.assertEqual(root.tag, "mxfile")
            self.assertNotIn("modified", root.attrib)
            self.assertNotIn("agent", root.attrib)
            cells = root.findall("./diagram/mxGraphModel/root/mxCell")
            ids = [cell.get("id") for cell in cells]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(ids[:2], ["0", "1"])
            known = set(ids)
            for cell in cells[2:]:
                self.assertIn(cell.get("parent"), known, cell.get("id"))
                for end in ("source", "target"):
                    if cell.get(end) is not None:
                        self.assertIn(cell.get(end), known)
            # Uncompressed, so a reviewer can diff it: the boxes are named in plain text.
            for name in ("OrderPlaced", "ChargeOnPlaced", "Charges"):
                self.assertIn(name.encode(), first)
            # And the reader's caption names every event it reads, sorted, as its own text cell.
            self.assertIn(b"reads Charged, OrderPlaced", first)

            # Regenerating an unchanged model is byte-identical.
            again = run(repo, "model-drawio")
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(canvas.read_bytes(), first)

            # Proved to fail: a hand edit is stale, and the message names the fix.
            canvas.write_bytes(first.replace(b"OrderPlaced", b"OrderAccepted", 1))
            stale = run(repo, "check-drawio")
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("is stale", stale.stderr)
            self.assertIn("Run make model-drawio and commit the result", stale.stderr)
            self.assertNotIn("is missing", stale.stderr)
            # The check changed nothing: the file is still the edited one until it is regenerated.
            self.assertIn(b"OrderAccepted", canvas.read_bytes())

            # A changed model changes the file — otherwise the check would pass stale work.
            model.write_text(MODEL_HEADER + SLICES.replace("name: OrderPlaced", "name: OrderAccepted").replace(
                "[OrderPlaced", "[OrderAccepted"
            ))
            changed = run(repo, "model-drawio")
            self.assertEqual(changed.returncode, 0, changed.stderr)
            self.assertNotEqual(canvas.read_bytes(), first)
            self.assertEqual(run(repo, "check-drawio").returncode, 0)

            # Emptied again, the canvas left behind is stale like any other; regenerating removes it.
            model.write_text(MODEL_HEADER + "slices: []\n")
            leftover = run(repo, "check-drawio")
            self.assertNotEqual(leftover.returncode, 0)
            self.assertIn("still exists", leftover.stderr)
            self.assertEqual(run(repo, "model-drawio").returncode, 0)
            self.assertFalse(canvas.exists())

            # The planner's and serialiser's own suites, from the target a project gets.
            tested = run(repo, "model-drawio-test")
            self.assertEqual(tested.returncode, 0, tested.stderr + tested.stdout)
            # Node's test runner reports in TAP (`# fail 0`) to a pipe and in its spec style (`ℹ fail 0`) to a
            # terminal, and the forge's runner hands the job a terminal; the count is what matters, not the prefix.
            self.assertRegex(tested.stdout, r"\bfail 0\b")
            self.assertNotRegex(tested.stdout, r"\bpass 0\b")

    def test_the_canvas_agrees_with_the_mermaid_diagram(self) -> None:
        """Same order, same lanes, same arrows, same colours: the two renderings ask the model the same
        questions, and this holds the answers together on a generated project."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "two-renderings")
            (repo / "docs/event-model/model.yaml").write_text(MODEL_HEADER + SLICES)
            install = subprocess.run(
                ["npm", "--prefix", str(repo / "scripts/event-model"), "install",
                 "--no-audit", "--no-fund", "--loglevel=error"],
                cwd=repo, text=True, capture_output=True,
            )
            self.assertEqual(install.returncode, 0, install.stderr)
            probe = repo / "scripts/event-model/probe-canvas.mts"
            probe.write_text(
                "import { planBoard } from './board-plan.ts';\n"
                "import { renderGlobalMermaid } from './mermaid.ts';\n"
                "import { SWATCHES } from './palette.ts';\n"
                "import { loadModel } from './workspace.ts';\n"
                "const model = loadModel();\n"
                "const plan = planBoard(model);\n"
                "const boxes = plan.items.filter((item) => item.key.startsWith('frame-'));\n"
                "console.log(JSON.stringify({\n"
                "  order: boxes.map((box) => box.key),\n"
                "  fills: boxes.map((box) => box.fill),\n"
                "  reads: plan.connectors.filter((c) => c.kind === 'reads').map((c) => `${c.from}>${c.to}`),\n"
                "  swatches: SWATCHES,\n"
                "  mermaid: renderGlobalMermaid(model),\n"
                "}));\n"
            )
            done = subprocess.run(
                [str(repo / "scripts/event-model/node_modules/.bin/tsx"), str(probe)],
                cwd=repo, text=True, capture_output=True,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            report = json.loads(done.stdout)
            lines = report["mermaid"].splitlines()
            mermaid_numbers = [int(line.split()[1]) for line in lines if line[:3] in ("rf ", "tf ")]
            self.assertEqual(report["order"], [f"frame-{n}" for n in mermaid_numbers])
            # The reads the Mermaid source declares (`->> n` on a slice's first box) are the canvas's reads.
            declared = []
            for line in report["mermaid"].splitlines():
                if " ->> " in line:
                    target = int(line.split()[1])
                    sources = [int(part.split()[0]) for part in line.split(" ->> ")[1:]]
                    declared += [f"frame-{n}>frame-{target}" for n in sources]
            self.assertEqual(sorted(report["reads"]), sorted(declared))
            # One palette: the fills are Mermaid's own defaults, which is what the SVG is drawn with.
            self.assertEqual(report["swatches"]["evt"]["fill"], "#ffb778")
            self.assertEqual(report["swatches"]["cmd"]["fill"], "#bcd6fe")
            self.assertEqual(set(report["fills"]) <= {s["fill"] for s in report["swatches"].values()}, True)
