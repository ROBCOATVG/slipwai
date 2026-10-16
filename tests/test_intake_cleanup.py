"""A migration proposes where loose requirements could be recorded, and moves nothing by itself."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.project import intake_cleanup

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "assets/toolkit/scripts/apply-intake.py"


def project() -> Path:
    root = Path(tempfile.mkdtemp())
    (root / "docs").mkdir()
    (root / "docs/prd.md").write_text("# First\n", encoding="utf-8")
    (root / "docs/getting-started.md").write_text("# Start\n", encoding="utf-8")
    (root / "docs/billing-requirements.md").write_text("# Billing requirements\n", encoding="utf-8")
    (root / "docs/notes.md").write_text("# A note\n", encoding="utf-8")
    feature = root / "specs/001-demo"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Demo\n", encoding="utf-8")
    return root


class ProposalTest(unittest.TestCase):
    def test_the_first_feature_and_an_existing_specification_stay(self) -> None:
        rows = {row["path"]: row for row in intake_cleanup.propose(project())["rows"]}
        self.assertEqual(rows["docs/prd.md"]["action"], "keep")
        self.assertEqual(rows["specs/001-demo/spec.md"]["action"], "keep")
        self.assertNotIn("docs/getting-started.md", rows)

    def test_a_requirements_document_is_proposed_and_a_note_is_left_for_a_person(self) -> None:
        rows = {row["path"]: row for row in intake_cleanup.propose(project())["rows"]}
        self.assertEqual(rows["docs/billing-requirements.md"]["action"], "intake")
        self.assertFalse(rows["docs/billing-requirements.md"]["confirmed"])
        self.assertEqual(rows["docs/notes.md"]["action"], "ask")

    def test_apply_moves_only_a_confirmed_intake_row(self) -> None:
        root = project()
        proposal = intake_cleanup.propose(root)
        for row in proposal["rows"]:
            if row["path"] == "docs/billing-requirements.md":
                row["confirmed"] = True
        (root / ".slipwai").mkdir()
        (root / ".slipwai/intake-cleanup.json").write_text(json.dumps(proposal), encoding="utf-8")
        done = subprocess.run(["python3", str(SCRIPT)], cwd=root, text=True, capture_output=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((root / "docs/intake/billing-requirements/billing-requirements.md").is_file())
        self.assertFalse((root / "docs/billing-requirements.md").exists())
        self.assertTrue((root / "docs/prd.md").is_file())
        self.assertTrue((root / "docs/notes.md").is_file())
