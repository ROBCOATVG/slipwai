"""In-flight proposals are not work authorization; historic ids and trunk evidence survive the crossing."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import checkout_packages  # noqa: F401

from slipwai.assets import ROOT
from slipwai.migration_flight import json_bytes, plan_context, read, settings


def script(relative: str):
    spec = importlib.util.spec_from_file_location("migration_script", ROOT / "assets/toolkit/scripts" / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class YAML:
    def yaml(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))


class FlightTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.feature = self.root / "specs/ordering"
        (self.feature / "slices/ORD-01").mkdir(parents=True)
        (self.feature / "story-split.md").write_text("ORD-01 ORD-02 ORD-03", encoding="utf-8")
        self.document = {"profile": "standard", "target": "none", "layout": {"delivery": "."},
                         "deployables": {"service": {"kind": "service", "path": "apps/service",
                                                     "contexts": ["ordering", "billing"]}}}

    def test_explicit_structure_context_is_not_guessed_from_other_prose(self) -> None:
        self.assertEqual(plan_context("# Structure Decision\nContext: ordering\n", ["ordering", "billing"]), "ordering")
        self.assertEqual(plan_context("billing might fit", ["ordering", "billing"]), "unplaced")
        self.assertEqual(plan_context("", ["ordering"]), "ordering")

    def test_two_contexts_and_unreadable_slice_preserve_ids_and_seed_only_proven_implementation(self) -> None:
        (self.feature / "slices/ORD-01/plan.md").write_text("# Structure Decision\nContext: ordering\n")
        (self.feature / "slices/ORD-02").mkdir()
        (self.feature / "slices/ORD-02/plan.md").write_text("# Structure Decision\nContext: billing\n")
        old = "# Decisions\n\n## D1 — keep this id\n**When:** 2026-01-01\n\n## D2 — next\n"
        (self.feature / "decisions.md").write_text(old, encoding="utf-8")
        with patch("slipwai.migration_flight.shipped",
                   side_effect=lambda root, slice_id: "abc" if slice_id == "ORD-01" else None):
            flight = read(self.root, self.document, YAML())
        self.assertEqual(flight.counts, (3, 1))
        self.assertEqual(flight.files["fairways/main/ordering/decisions.md"].decode(), old)
        self.assertIn("## D1", flight.files["specs/ordering/decisions.md"].decode())
        self.assertEqual([(line.kind, line.fields["slice"]) for _, _, line in flight.logs], [("merged", "ORD-01")])
        state = json.loads(flight.files[".slipwai/migration.json"])
        chart = json.loads(flight.files["specs/ordering/chart.yaml"])
        (self.root / ".slipwai").mkdir()
        (self.root / ".slipwai/migration.json").write_bytes(json_bytes(state))
        (self.feature / "chart.yaml").write_bytes(json_bytes(chart))
        guard = script("agents/clearance.py")
        guard.ROOT = self.root
        self.assertIn("confirmation", guard.cleared(chart, set(), "ORD-01"))
        self.assertEqual(guard.cleared_slices(chart, set()), [])
        confirmation = script("check-migration.py")
        with patch.object(confirmation, "project_root", return_value=self.root):
            self.assertEqual(confirmation.main([]), 1)
            self.assertEqual(confirmation.main(["--confirm"]), 1)
            chart["slices"]["ORD-03"]["fairway"] = "ordering"
            (self.feature / "chart.yaml").write_bytes(json_bytes(chart))
            self.assertEqual(confirmation.main(["--confirm"]), 0)
        self.assertIs(guard.cleared(chart, set(), "ORD-01"), True)

    def test_model_choices_are_preserved_and_review_is_null_per_harness(self) -> None:
        (self.root / ".specify").mkdir()
        (self.root / ".specify/models.json").write_text(
            json.dumps({"roles": {"claude": {"fast": "chosen", "skipper": "old"}}}))
        files = {"project.json": json_bytes(self.document),
                 ".specify/models.json": json_bytes({"roles": {"claude": {"fast": "default", "review": "host"}}})}
        with patch("slipwai.migration_flight.git", return_value=b""):
            settings(self.root, self.document, files)
        self.assertEqual(json.loads(files[".specify/models.json"])["roles"]["claude"],
                         {"fast": "chosen", "review": None, "decide": "old"})
        self.assertEqual(json.loads(files["project.json"])["releaseMode"], "open")
