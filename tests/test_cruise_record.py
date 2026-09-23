"""`/cruise`'s record: the owner brief a run decides from, and the gate that holds what it wrote down.

A run with nobody at the wheel is trusted through its record. The brief is where a person steers a run without
stopping it; `decisions.md` and `demo-log.md` are where every decision and every demo can be read back and
overturned; and `scripts/check-decisions.py` is what keeps an entry from being written in a shape nobody can
audit, or citing a path that is not in the tree.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.project.cruise import DECISION_ENTRY
from slipwai.project.cruise_agents import DECISIONS, DEMO_LOG, OWNER_BRIEF
from slipwai.project.cruise_record import DEMO_ENTRY
from slipwai.project.decisions import PAGE

DECISION = """## D1 — Which capability flag holds S4 back
- **Stage:** release-constraint · **Slice:** S4 · **When:** 2026-09-22T14:03Z · **Iteration:** 12
- **Question:** continues `campaign-reports`, opens a new key, or releasable on merge?
- **Options:** continue `campaign-reports` (recommended by the stage) · open `report-confirmation` · no flag
- **Decision:** continue `campaign-reports`
- **Why:** S4 completes the capability S2 opened; the actor sees one thing, "reports".
- **Decided by:** host (stage recommendation)
- **Confidence:** high · **Would reverse if:** the spec splits confirmation into its own actor journey
- **Written to:** `specs/f/slices/S4/plan.md`
- **Status:** standing
"""
SECOND = """
## D2 — Which service owns S5
- **Stage:** plan · **Slice:** S5 · **When:** 2026-09-22T15:10Z · **Iteration:** 13
- **Question:** which service's purpose covers a points table?
- **Options:** campaign (recommended) · reporting
- **Decision:** campaign
- **Why:** the table is read by the organiser who records battles, and that is campaign's purpose.
- **Decided by:** drive-skipper (opus)
- **Confidence:** medium · **Would reverse if:** a reporting service gains a purpose of its own
- **Written to:** `specs/f/slices/S5/plan.md`
- **Status:** overridden by human 2026-09-23
"""
DEMO = """## 2026-09-22T16:00Z — accepted · iteration 13 · drive-hand (host)
- **Started with:** `make demo` · **Seeded:** none
- **Driven through:** agent-browser
- **Examples:** R1 e1: passed · R2 e1: passed
- **Evidence:** `demo/r1-e1.png`
- **Feedback:** none; a label note for the next slice
"""


def gate(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", "scripts/check-decisions.py"], cwd=repo, text=True, capture_output=True)


def record(repo: Path, decisions: str = DECISION, demo: str = DEMO, evidence: bool = True) -> None:
    feature = repo / "specs/f"
    (feature / "slices/S4").mkdir(parents=True, exist_ok=True)
    (feature / "slices/S5").mkdir(parents=True, exist_ok=True)
    (feature / "slices/S4/plan.md").write_text("# plan\n")
    (feature / "slices/S5/plan.md").write_text("# plan\n")
    (feature / "decisions.md").write_text("# Decisions\n\n" + decisions)
    (feature / "slices/S4/demo-log.md").write_text("# Demos\n\n" + demo)
    shot = feature / "slices/S4/demo/r1-e1.png"
    if evidence:
        shot.parent.mkdir(exist_ok=True)
        shot.write_bytes(b"png")
    elif shot.exists():
        shot.unlink()


class CruiseRecordTest(FactoryTestCase):
    def test_the_owner_brief_ships_as_placeholders_the_skipper_reads_before_every_decision(self) -> None:
        """The brief is the person's lever on a run that never stops: the skipper reads it before deciding, a
        person edits it at any time, and nothing generated rewrites it. It carries the two entry shapes so
        the person who overrules a decision knows what they are reading."""
        for profile in ("event-modelling", "standard"):
            with tempfile.TemporaryDirectory() as directory:
                repo = self.generate(directory, "brief", profile, "python")
                self.assertEqual(PAGE, OWNER_BRIEF)
                brief = (repo / PAGE).read_text()
                self.assertTrue(brief.startswith("# [PROJECT_NAME] — the product owner's brief"))
                self.assertIn("`/cruise` runs `/drive` with nobody at the wheel", brief)
                self.assertIn("The `drive-skipper`\ndelegate reads it before every product decision", brief)
                self.assertIn("Edit it at any time: the next decision reads the new text", brief)
                self.assertIn("This file is human-owned. `/cruise` reads it and never writes it", brief)
                for heading in ("## Who the actor is", "## What the product is for", "## Priorities and tie-breakers",
                                "## Taste", "## Out of scope", "## Always ask a person",
                                "## What the record looks like"):
                    self.assertIn(heading, brief)
                # The shapes are the command's, not a second copy of them.
                self.assertIn(DECISION_ENTRY, brief)
                self.assertIn(DEMO_ENTRY, brief)
                self.assertIn(f"`{DECISIONS}`", brief)
                self.assertIn(f"`{DEMO_LOG}`", brief)
                self.assertIn("`make check-decisions` holds both files", brief)
                # The skipper's own brief names the page it reads.
                self.assertIn(OWNER_BRIEF, (repo / "agents/drive-skipper.md").read_text())
                script = repo / "scripts/check-decisions.py"
                self.assertTrue(script.is_file())
                self.assertTrue(script.stat().st_mode & 0o111, "the gate runs like its siblings")

    def test_the_gate_passes_a_true_record_and_an_empty_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "record", "standard", "python")
            empty = gate(repo)
            self.assertEqual(empty.returncode, 0, empty.stderr)
            self.assertIn("check-decisions: no decisions.md or demo-log.md under specs/ — nothing recorded yet",
                          empty.stdout)
            record(repo, DECISION + SECOND)
            passed = gate(repo)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertIn("check-decisions: 2 decision(s) in 1 file(s), 1 demo(s) in 1 log(s), every field present "
                          "and every path in the tree, every done slice in the adversary log", passed.stdout)
            # The bosun writes `Decided by: drive-bosun`, as the command tells it to, with or without its model:
            # a run's first workaround left `make verify` failing on exactly the entry it had been told to write.
            for signed in ("drive-bosun", "drive-bosun (opus)"):
                record(repo, DECISION.replace("host (stage recommendation)", signed) + SECOND)
                bosun = gate(repo)
                self.assertEqual(bosun.returncode, 0, (signed, bosun.stdout, bosun.stderr))

    def test_a_finished_slice_with_no_row_in_the_adversary_log_is_a_finding(self) -> None:
        """`/adversary` runs after every acceptance and writes a row either way — the attack, or the skip with the
        rows it relied on — and says an unwritten row is a pass that has to be run again. A slice was delivered
        with none, through a gate that held the decision and demo logs and never looked here. Done is what the
        ladder calls done: a register row, or `status: implemented` in the event model."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "attacked", "standard", "python")
            (repo / "specs/f/slices/S1").mkdir(parents=True)
            (repo / "specs/f/slices/README.md").write_text("| Slice | Accepted |\n|---|---|\n| S1 | 2026-09-22 |\n")
            refused = gate(repo)
            self.assertEqual(refused.returncode, 1)
            self.assertIn("specs/f/adversary-log.md: no row for S1, which is done — `/adversary` runs after every "
                          "acceptance and records the attack or the skip", refused.stderr)
            (repo / "specs/f/adversary-log.md").write_text("# Adversary log\n\n## S1 · abc1234 · 2026-09-22\n\n"
                                                           "| Trigger | Status | Evidence |\n|---|---|---|\n"
                                                           "| new endpoint | not present | prior row |\n\n"
                                                           "Spawned:\nOmitted: none\nFindings: none\n")
            self.assertEqual(gate(repo).returncode, 0)
            (repo / "docs/event-model").mkdir(parents=True)
            (repo / "docs/event-model/model.yaml").write_text(
                "version: 1\nslices:\n  - id: S2\n    status: implemented\n  - id: S3\n    status: planned\n")
            refused = gate(repo)
            self.assertEqual(refused.returncode, 1)
            self.assertIn("no row for S2, which is done", refused.stderr)
            self.assertNotIn("S3", refused.stderr)

    def test_the_gate_refuses_every_shape_a_run_could_write_wrong(self) -> None:
        """Each malformation is one finding naming the file, the line and what the shape is — a decision nobody
        can audit, a path never written, a number skipped, a verdict outside the three the benchmark knows."""
        why = "- **Why:** S4 completes the capability S2 opened; the actor sees one thing, \"reports\".\n"
        cases = [
            ("missing field", DECISION.replace(why, ""), DEMO, True,
             "specs/f/decisions.md:3: D1 is missing **Why:**"),
            ("bad status", DECISION.replace("- **Status:** standing", "- **Status:** maybe"), DEMO, True,
             "D1 `Status` is 'maybe'; it is standing, overridden by D<m> or overridden by human <date>"),
            ("bad decided-by", DECISION.replace("host (stage recommendation)", "the model"), DEMO, True,
             "D1 `Decided by` is 'the model'; it is host (stage recommendation), host (standing decision D<m>), "
             "drive-skipper (<model>), drive-bosun or human"),
            ("path not in tree", DECISION.replace("`specs/f/slices/S4/plan.md`", "`specs/f/slices/S9/plan.md`"), DEMO,
             True, "D1 `Written to` names `specs/f/slices/S9/plan.md`, which is not in the tree"),
            ("placeholder left", DECISION.replace("`specs/f/slices/S4/plan.md`", "`specs/<feature>/plan.md`"), DEMO,
             True, "D1 `Written to` still carries a placeholder: specs/<feature>/plan.md"),
            ("gap in numbering", DECISION + SECOND.replace("## D2", "## D3"), DEMO, True,
             "D3 where D2 was expected — entries are numbered contiguously"),
            ("fields out of order",
             DECISION.replace("- **Decision:** continue `campaign-reports`\n" + why, why)
             .replace("- **Decided by:**", "- **Decision:** continue `campaign-reports`\n- **Decided by:**"),
             DEMO, True, "D1's fields are out of order; the shape is Stage, Question"),
            ("bad verdict", DECISION, DEMO.replace("— accepted ·", "— passed ·"), True,
             "specs/f/slices/S4/demo-log.md:3: verdict 'passed' is not one of accepted, behaviour, implementation"),
            ("evidence missing", DECISION, DEMO, False,
             "`Evidence` names `demo/r1-e1.png`, which is not in the tree"),
            ("demo field missing", DECISION,
             DEMO.replace("- **Feedback:** none; a label note for the next slice\n", ""), True,
             "the 2026-09-22T16:00Z demo is missing **Feedback:**"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "shapes", "standard", "python")
            for name, decisions, demo, evidence, finding in cases:
                record(repo, decisions, demo, evidence)
                refused = gate(repo)
                self.assertEqual(refused.returncode, 1, name)
                self.assertIn("check-decisions: the record is not in the shape commands/cruise.md shows",
                              refused.stderr, name)
                self.assertIn(finding, refused.stderr, name)
            # `none` is the one evidence line that names no path: a demo with no screen has nothing to shoot.
            record(repo, DECISION, DEMO.replace("`demo/r1-e1.png`", "none"), False)
            self.assertEqual(gate(repo).returncode, 0)
