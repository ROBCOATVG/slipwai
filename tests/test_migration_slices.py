"""What a crossing takes to be a slice, and which event names it keeps (issue 95).

A version 1 project's crossing listed scenario and requirement ids as slices to place, and slices the model
cannot hold, so its confirmation never succeeded; and `check-model` then failed every event the project had
already written for a naming rule that arrived after it. These hold the three things that fixed it: a split
names its slices in its slice graph's first column, the confirmation judges the chart, and the crossing
records the names its built slices hold.
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import checkout_packages  # noqa: F401
from test_migration_flight import YAML, script

from slipwai.migration_flight import json_bytes, read
from slipwai.migration_slices import NAMES_FROM, named


class SlicesTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.feature = self.root / "specs/ordering"
        (self.feature / "slices/ORD-01").mkdir(parents=True)
        (self.feature / "story-split.md").write_text(
            "## Slice graph\n| Slice | depends_on |\n|---|---|\n| ORD-01 | — |\n", encoding="utf-8")
        self.document = {"profile": "standard", "target": "none", "layout": {"delivery": "."},
                         "deployables": {"service": {"kind": "service", "path": "apps/service",
                                                     "contexts": ["ordering", "billing"]}}}

    #: A version 1 split as one really read: ids of other things quoted in the notes, a run of slices the
    #: model has no frames for, and a directory under `slices/` that is not a slice at all.
    SPLIT = """# Split

FR-006 is the requirement all of this serves, and V-10 the rule.

## Slice graph
| Slice | depends_on | parallel_ok_with | Notes |
|---|---|---|---|
| S1 | — | — | The walking skeleton |
| S2 | S1 | any, **not S3** | CS-3 refuses a founder; see R-11 and FR-006 |
| `S3` | S1 | W5 only | Shares a screen with S2 (V-10) |
| S38–S40 | S1 | — | Hardening: no frames of their own, so CS-15 is proved elsewhere |

## Parking Lot
ORD-99 was dropped.
"""

    def split(self) -> None:
        (self.feature / "story-split.md").write_text(self.SPLIT, encoding="utf-8")
        for name in ("S1", "S2", "S38", "W5"):
            (self.feature / "slices" / name).mkdir(parents=True, exist_ok=True)

    def test_a_split_gives_only_the_slices_its_slice_graph_names_in_its_first_column(self) -> None:
        """Issue 95: `CS-3`, `FR-006`, `R-11` and `V-10` were quoted in the notes and became slices nobody
        could place, which left `--confirm` impossible and every fairway unclaimable."""
        self.split()
        with patch("slipwai.migration_flight.shipped", return_value=None):
            flight = read(self.root, self.document, YAML())
        chart = json.loads(flight.files["specs/ordering/chart.yaml"])
        self.assertEqual(sorted(chart["slices"]),
                         ["ORD-01", "S1", "S2", "S3", "S38", "S39", "S40", "W5"],
                         "the first column and the slice directories, and nothing from the prose")

    def test_a_split_older_than_the_slice_graph_names_its_slices_in_its_candidates_table(self) -> None:
        candidates = ("PAY-9 is prose.\n\n## Split Candidates\n| Slice | Value |\n|---|---|\n"
                      "| **PAY-1** pay by card | FR-2 |\n| PAY-2, PAY-3 | — |\n\n"
                      "| Requirement | Slice |\n|---|---|\n| FR-7 | PAY-1 |\n")
        self.assertEqual(named(candidates), ["PAY-1", "PAY-2", "PAY-3"])
        self.assertEqual(named("PAY-1 and PAY-2, in a sentence."), [])

    def test_a_run_keeps_its_padding_and_a_modelled_id_is_read_however_it_is_spelled(self) -> None:
        graph = "## Slice graph\n| Slice | depends_on |\n|---|---|\n| L02–L04 | — |\n| place-order | L02 |\n"
        self.assertEqual(named(graph), ["L02", "L03", "L04"])
        self.assertEqual(named(graph, ["place-order", "order"]), ["L02", "L03", "L04", "place-order"])

    def test_on_the_event_profile_the_model_says_what_a_slice_is(self) -> None:
        """A split-only slice has no frames, the model's grammar admits no slice without one, and the chart
        is rendered from the model — so it can never be placed. It is named, not left in `unplaced`."""
        self.split()
        self.document["profile"] = "event-modelling"
        path = self.root / "docs/event-model/model.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json_bytes({"slices": [
            {"id": "S1", "context": "ordering", "status": "implemented"},
            {"id": "S2", "context": "billing", "status": "planned"},
            {"id": "S3", "status": "proposed"}]}))
        with patch("slipwai.migration_flight.shipped", return_value=None):
            flight = read(self.root, self.document, YAML())
        chart = json.loads(flight.files["specs/ordering/chart.yaml"])
        self.assertEqual(list(chart["slices"]), ["S1", "S2", "S3"])
        self.assertEqual(flight.features["ordering"]["unplaced"], ["S3"],
                         "a slice the model holds and gives no context is the only kind a person can place")
        self.assertEqual(flight.unmodelled, {"ordering": ["ORD-01", "S38", "S39", "S40", "W5"]})

    def test_confirmation_judges_the_chart_and_not_the_list_the_crossing_wrote(self) -> None:
        """What a project that already crossed holds: a list of names its chart can never carry."""
        (self.root / ".slipwai").mkdir()
        state: dict = {"v": 1, "features": {"ordering": {"proposed": ["ordering", "billing"],
                                                   "unplaced": ["CS-3", "FR-006", "S38", "W5", "S2"]}}}
        (self.root / ".slipwai/migration.json").write_bytes(json_bytes(state))
        chart: dict = {"v": 1, "feature": "ordering",
                 "fairways": {"ordering": {}, "billing": {}},
                 "slices": {"S1": {"fairway": "ordering"}, "S2": {"fairway": "unplaced"}}}
        (self.feature / "chart.yaml").write_bytes(json_bytes(chart))
        confirmation = script("check-migration.py")
        with patch.object(confirmation, "project_root", return_value=self.root):
            said = io.StringIO()
            with contextlib.redirect_stdout(said):
                self.assertEqual(confirmation.main(["--confirm"]), 1, "a charted slice is still unplaced")
            self.assertIn("S2", said.getvalue())
            self.assertNotIn("FR-006", said.getvalue(), "a refusal names only what can be placed")
            chart["slices"]["S2"]["fairway"] = "billing"
            (self.feature / "chart.yaml").write_bytes(json_bytes(chart))
            said = io.StringIO()
            with contextlib.redirect_stdout(said):
                self.assertEqual(confirmation.main(["--confirm"]), 0, said.getvalue())
            for name in ("CS-3", "FR-006", "S38", "W5"):
                self.assertIn(name, said.getvalue(), "what the chart does not hold is said, not refused")
            self.assertNotIn("S2", said.getvalue())
        written = json.loads((self.root / ".slipwai/migration.json").read_text(encoding="utf-8"))
        self.assertEqual(written["features"]["ordering"], {"proposed": [], "unplaced": []})
        self.assertIn("confirmed", written)
        claims = script("agents/claims.py")
        self.assertNotIn("confirmation", claims.take(self.root, "billing", "this-machine").why or "")

    def kept(self, *slices: dict) -> object:
        """The event names the crossing records for these slices, or None where it writes no file."""
        path = self.root / "docs/event-model/model.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json_bytes({"slices": list(slices)}))
        with patch("slipwai.migration_flight.shipped",
                   side_effect=lambda root, slice_id: "abc" if slice_id == "ORD-01" else None):
            self.flight = read(self.root, self.document, YAML())
        written = self.flight.files.get(NAMES_FROM)
        return json.loads(written)["events"] if written is not None else None

    @staticmethod
    def raising(slice_id: str, status: str, *events: str, **frame: object) -> dict:
        return {"id": slice_id, "status": status, "frames": [
            {"type": "cmd", "name": f"Do{slice_id.replace('-', '')}"},
            *({"type": "evt", "name": event, **frame} for event in events)]}

    def test_the_crossing_records_the_event_names_of_slices_that_may_already_be_in_a_log(self) -> None:
        """Issue 95: a stored event cannot be renamed, so the naming rules ask nothing of one."""
        self.assertEqual(self.kept(
            self.raising("S1", "implemented", "WorkspaceCreated", "DocumentNotReceived"),
            self.raising("S2", "observed", "LedgerUpdated"),
            self.raising("S3", "implemented", "WorkspaceCreated", "PaymentTaken")),
            ["DocumentNotReceived", "LedgerUpdated", "PaymentTaken", "WorkspaceCreated"])
        self.assertEqual(self.flight.kept, ["DocumentNotReceived", "LedgerUpdated", "PaymentTaken",
                                            "WorkspaceCreated"])
        self.assertEqual(NAMES_FROM, script("event-model/check.py").NAMES_FROM, "the gate reads what this writes")

    def test_a_slice_nobody_has_built_keeps_no_name(self) -> None:
        """The stricter of the issue's two readings: modelled and never written can still be renamed."""
        self.assertEqual(self.kept(
            self.raising("S1", "implemented", "WorkspaceCreated"),
            self.raising("S2", "planned", "ModelVersionCreated"),
            self.raising("S3", "modelled", "InviteNotSent"),
            self.raising("S4", "proposed", "ThingDeleted"),
            {"id": "S5", "frames": [{"type": "evt", "name": "StatuslessUpdated"}]}), ["WorkspaceCreated"])

    def test_a_slice_trunk_proves_shipped_keeps_its_names_whatever_its_status_said(self) -> None:
        self.assertEqual(self.kept(self.raising("ORD-01", "proposed", "OrderCreated")), ["OrderCreated"])

    def test_a_project_with_nothing_in_a_log_gets_no_file_and_is_held_on_every_name(self) -> None:
        self.assertIsNone(self.kept(self.raising("S2", "planned", "ModelVersionCreated")))
        self.assertEqual(self.flight.kept, [])

    def test_the_names_are_recorded_once_and_a_second_crossing_leaves_them(self) -> None:
        """Rewriting it would forgive every name added under the rule since."""
        (self.root / ".specify").mkdir()
        (self.root / NAMES_FROM).write_text('{"events": ["WorkspaceCreated"]}', encoding="utf-8")
        self.assertIsNone(self.kept(self.raising("S1", "implemented", "WorkspaceCreated", "LaterUpdated")))
        self.assertEqual(self.flight.kept, [])

    def test_what_the_crossing_writes_is_what_the_gate_then_passes(self) -> None:
        gate = script("event-model/check.py")
        self.kept(self.raising("S1", "implemented", "WorkspaceCreated"), self.raising("S2", "planned", "RowUpdated"))
        (self.root / ".specify").mkdir()
        (self.root / NAMES_FROM).write_bytes(self.flight.files[NAMES_FROM])
        with patch.object(gate, "ROOT", self.root):
            self.assertEqual(gate.held_event_names(), frozenset({"WorkspaceCreated"}))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
