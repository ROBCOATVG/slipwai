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
from slipwai.fleet import Fairway, inbox, state_of
from slipwai.migration_flight import json_bytes, plan_context, read, shipped
from slipwai.migration_settings import settings


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

    def model(self, *slices: dict) -> dict:
        path = self.root / "docs/event-model/model.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json_bytes({"slices": list(slices)}))
        with patch("slipwai.migration_flight.shipped",
                   side_effect=lambda root, slice_id: "abc" if slice_id == "ORD-01" else None):
            flight = read(self.root, self.document, YAML())
        written = json.loads(flight.files["docs/event-model/model.yaml"])
        return {str(item["id"]): item.get("status") for item in written["slices"]}

    def test_trunk_promotes_a_slice_and_never_demotes_one_the_person_placed(self) -> None:
        self.assertEqual(
            self.model({"id": "ORD-01", "status": "proposed"}, {"id": "ORD-02", "status": "proposed"},
                       {"id": "ORD-03", "status": "implemented"}),
            {"ORD-01": "implemented", "ORD-02": "proposed", "ORD-03": "implemented"})

    def test_a_slice_with_no_recorded_status_is_not_given_one_the_crossing_invented(self) -> None:
        self.assertEqual(self.model({"id": "ORD-02", "context": "billing"}), {"ORD-02": None})

    def test_a_forge_merge_naming_the_claim_branch_is_the_same_evidence_as_gits_own(self) -> None:
        def history(subject: str) -> bytes:
            return b"c0ffee\x00" + subject.encode("utf-8") + b"\n\x00"

        for subject in ("Merge branch 'slice/ORD-01'",
                        "Merge branch 'slice/ORD-01' into 'main'",
                        "Merge pull request #12 from acme/slice/ORD-01",
                        "Merge remote-tracking branch \"origin/slice/ORD-01\"",
                        "a squashed subject\n\nSlice-done: ORD-01"):
            with self.subTest(subject=subject), patch("slipwai.migration_flight.git",
                                                      return_value=history(subject)):
                self.assertEqual(shipped(self.root, "ORD-01"), "c0ffee")
        for subject in ("Merge branch 'slice/ORD-010'", "Merged slice/ORD-01",
                        "Start work on slice/ORD-01 and its chart",
                        "Revert \"Merge branch 'slice/ORD-01'\""):
            with self.subTest(subject=subject), patch("slipwai.migration_flight.git",
                                                      return_value=history(subject)):
                self.assertIsNone(shipped(self.root, "ORD-01"))

    def test_the_queued_inbox_crosses_as_unanswered_told_lines_in_version_1_s_own_order(self) -> None:
        said = self.root / ".specify"
        said.mkdir()
        (said / "cruise-told.jsonl").write_text(json.dumps(
            {"at": "2026-01-01T09:00:00Z", "text": "taken by the iteration that died", "now": False}) + "\n",
            encoding="utf-8")
        (said / "cruise-inbox.jsonl").write_text("".join(json.dumps(line) + "\n" for line in (
            {"at": "2026-01-01T10:00:00Z", "text": "still queued", "now": True},
            {"at": "2026-01-01T11:00:00Z", "text": "  and this one  ", "now": False})), encoding="utf-8")
        with patch("slipwai.migration_flight.shipped", return_value=None):
            flight = read(self.root, self.document, YAML())
        lines = [line for _, _, line in flight.logs]
        self.assertEqual([(line.t, line.fields["message"]) for line in lines if line.kind == "told"],
                         [("2026-01-01T09:00:00Z", "taken by the iteration that died"),
                          ("2026-01-01T10:00:00Z", "still queued"),
                          ("2026-01-01T11:00:00Z", "and this one")])
        self.assertEqual([row["what"] for row in inbox([Fairway("main", "ordering", lines)])],
                         ["taken by the iteration that died", "still queued", "and this one"])

    def test_a_project_that_never_split_still_carries_its_words_and_why_it_stopped(self) -> None:
        (self.feature / "story-split.md").unlink()
        said = self.root / ".specify"
        said.mkdir()
        (said / "cruise-inbox.jsonl").write_text(
            json.dumps({"at": "2026-01-01T10:00:00Z", "text": "the invoice flow is wrong"}) + "\n",
            encoding="utf-8")
        (self.root / "specs/cruise-log.jsonl").write_text(
            json.dumps({"iteration": 4, "last_line": "cruise: parked: waiting on the gate"}) + "\n",
            encoding="utf-8")
        with patch("slipwai.migration_flight.shipped", return_value=None):
            flight = read(self.root, self.document, YAML())
        self.assertEqual(flight.features, {})
        self.assertEqual([(feature, fairway, line.kind) for feature, fairway, line in flight.logs],
                         [("ordering", "main", "told"), ("ordering", "main", "parked")])
        self.assertEqual([line.fields["message"] for _, _, line in flight.logs if line.kind == "told"],
                         ["the invoice flow is wrong"])
        self.assertEqual([line.fields["why"] for _, _, line in flight.logs if line.kind == "parked"],
                         ["waiting on the gate"])

    def test_a_project_with_no_feature_directory_at_all_still_lands_its_words_somewhere(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / ".specify").mkdir()
            (root / ".specify/cruise-inbox.jsonl").write_text(
                json.dumps({"at": "2026-01-01T10:00:00Z", "text": "do not lose this"}) + "\n", encoding="utf-8")
            with patch("slipwai.migration_flight.shipped", return_value=None):
                flight = read(root, self.document, YAML())
        self.assertEqual([(feature, fairway, line.fields["message"]) for feature, fairway, line in flight.logs],
                         [("main", "main", "do not lose this")])

    def park(self, *endings: str) -> list[str]:
        """What the crossing records after a version 1 run whose log ends on each of these last lines."""
        found = []
        for number, ending in enumerate(endings, start=1):
            (self.root / "specs/cruise-log.jsonl").write_text(
                json.dumps({"iteration": number, "last_line": ending}) + "\n", encoding="utf-8")
            with patch("slipwai.migration_flight.shipped", return_value=None):
                flight = read(self.root, self.document, YAML())
            found.append("; ".join(line.fields["why"] for _, _, line in flight.logs if line.kind == "parked"))
        return found

    def test_every_version_1_ending_but_done_crosses_as_a_park_that_says_why(self) -> None:
        reasons = self.park("cruise: parked: the gate is red", "cruise: stopped: human", "cruise: done",
                            "cruise: continue", "interrupted: a person's message", "no last line")
        self.assertEqual(reasons[0], "the gate is red")
        self.assertEqual(reasons[2], "")
        for reason, iteration in ((reasons[1], "2"), (reasons[3], "4"), (reasons[4], "5"), (reasons[5], "6")):
            self.assertIn(f"iteration {iteration}", reason)
        self.assertIn("person", reasons[1])
        for reason, ending in ((reasons[3], "cruise: continue"), (reasons[4], "interrupted: a person's message"),
                               (reasons[5], "no last line")):
            self.assertIn(ending, reason)
            self.assertIn("without recording", reason)

    def test_an_open_claim_branch_crosses_as_the_slice_still_in_flight(self) -> None:
        for slice_id in ("ORD-01", "ORD-03"):
            (self.feature / f"slices/{slice_id}").mkdir(parents=True, exist_ok=True)
            (self.feature / f"slices/{slice_id}/plan.md").write_text("# Structure Decision\nContext: ordering\n")
        with patch("slipwai.migration_flight.shipped",
                   side_effect=lambda root, slice_id: "abc" if slice_id == "ORD-01" else None):
            flight = read(self.root, self.document, YAML(), claims={"ORD-03"})
        self.assertEqual([(line.kind, line.fields["slice"]) for _, _, line in flight.logs
                          if line.kind in ("merged", "claimed")],
                         [("merged", "ORD-01"), ("claimed", "ORD-03")])
        self.assertEqual({fairway for _, fairway, line in flight.logs if line.kind == "claimed"}, {"ordering"})
        working = Fairway("ordering", "ordering",
                          [line for _, fairway, line in flight.logs if fairway == "ordering"])
        self.assertEqual(working.slice_now, "ORD-03")
        self.assertEqual(state_of(working), "working")

    def test_no_claim_branch_seeds_nothing_and_a_merged_slice_is_not_claimed_as_well(self) -> None:
        with patch("slipwai.migration_flight.shipped", return_value="abc"):
            flight = read(self.root, self.document, YAML(), claims={"ORD-01"})
        self.assertEqual([line.kind for _, _, line in flight.logs if line.kind == "claimed"], [])

    def test_model_choices_are_preserved_and_review_is_null_per_harness(self) -> None:
        (self.root / ".specify").mkdir()
        (self.root / ".specify/models.json").write_text(
            json.dumps({"roles": {"claude": {"fast": "chosen", "skipper": "old"}}}))
        files = {"project.json": json_bytes(self.document),
                 ".specify/models.json": json_bytes({"roles": {"claude": {"fast": "default", "review": "host"}}})}
        with patch("slipwai.migration_settings.git", return_value=b""):
            settings(self.root, self.document, files)
        self.assertEqual(json.loads(files[".specify/models.json"])["roles"]["claude"],
                         {"fast": "chosen", "review": None, "decide": "old"})
        self.assertEqual(json.loads(files["project.json"])["releaseMode"], "open")
