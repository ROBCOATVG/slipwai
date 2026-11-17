"""Where the product is decides how dark a merge is: read, said, moved, and never changed silently.

A flag is how merging and releasing become two decisions, which is right for a product people use and pure
drag for one nobody uses yet. lean-coffee-club opened a flag on its first capability, and its first two
slices stalled on flags no actor needed. What is held here is that a new project starts pre-launch and
merges in the open, that a project with no state recorded keeps merging flagged as it always has, that
version 2's first spellings still read, and that moving the state writes the state and its ADR together.
"""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import release_state
from slipwai.cli_release_state import release_state_main

ROOT = Path(__file__).resolve().parents[1]


class ModeTest(unittest.TestCase):
    def test_each_state_merges_under_its_own_mode(self) -> None:
        self.assertEqual(release_state.mode_of({"state": "pre-launch"}), "open")
        self.assertEqual(release_state.mode_of({"state": "pilot"}), "keystone")
        self.assertEqual(release_state.mode_of({"state": "live"}), "flagged")

    def test_a_project_that_recorded_no_state_keeps_merging_flagged(self) -> None:
        self.assertIsNone(release_state.state_of({}))
        self.assertEqual(release_state.mode_of({}), "flagged",
                         "a missing state read as pre-launch would send a live product's merges to its users")
        self.assertEqual(release_state.mode_of({"state": "somewhere"}), "flagged")

    def test_the_first_spellings_still_read_as_the_state_they_meant(self) -> None:
        self.assertEqual(release_state.state_of({"state": "slipway"}), "pre-launch")
        self.assertEqual(release_state.state_of({"state": "sea-trials"}), "pilot")
        self.assertEqual(release_state.state_of({"state": "in-service"}), "live")

    def test_promoted_is_declared_and_kept_whatever_the_state(self) -> None:
        self.assertEqual(release_state.mode_of({"state": "pre-launch", "release": "promoted"}), "promoted")

    def test_the_module_imports_only_the_standard_library_so_a_project_can_run_it(self) -> None:
        text = (ROOT / "src/slipwai/release_state.py").read_text(encoding="utf-8")
        self.assertNotIn("from .", text)
        carried = (ROOT / "assets/toolkit/scripts/agents/release_state.py").read_text(encoding="utf-8")
        self.assertTrue(carried.endswith(text), "make shared carries the keel's module byte for byte")


class ProjectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "project.json").write_text(json.dumps(
            {"schema": 2, "name": "club", "target": "azure", "shape": "skiff", "capabilities": []}, indent=2) + "\n")
        (self.root / "docs/adr").mkdir(parents=True)
        (self.root / "docs/adr/0001-record-architecture-decisions.md").write_text("# 0001\n")

    def test_an_unrecorded_state_is_said_with_how_to_record_it(self) -> None:
        said = release_state.said(self.root)
        self.assertIn("state: unrecorded · mode: flagged", said)
        self.assertIn("--set <state>", said)

    def test_flags_an_open_product_does_not_need_are_named(self) -> None:
        (self.root / "project.json").write_text(json.dumps({"state": "pre-launch"}))
        (self.root / "infra/service").mkdir(parents=True)
        (self.root / "infra/service/flags.auto.tfvars").write_text('club = {\n  sign-in = "off"\n}\n')
        said = release_state.said(self.root)
        self.assertIn("mode: open", said)
        self.assertIn("1 flag(s) declared that this mode does not need: sign-in = off", said)

    def test_moving_the_state_writes_it_beside_the_target_and_an_adr(self) -> None:
        written = release_state.move(self.root, "pre-launch", "Nobody outside the team uses it yet.",
                                     date(2026, 11, 17))
        document = json.loads((self.root / "project.json").read_text())
        self.assertEqual(document["state"], "pre-launch")
        self.assertEqual(list(document)[:4], ["schema", "name", "target", "state"])
        adr = self.root / "docs/adr/0002-the-product-is-pre-launch.md"
        self.assertEqual(written, [self.root / "project.json", adr])
        text = adr.read_text()
        self.assertIn("# 0002. The product is pre-launch", text)
        self.assertIn("The product's state was **unrecorded**", text)
        self.assertIn("Nobody outside the team uses it yet.", text)
        self.assertIn("It merges **open**", text)

    def test_a_move_needs_a_reason_and_a_real_state_and_a_change(self) -> None:
        with self.assertRaisesRegex(release_state.Refused, "--why needs the reason"):
            release_state.move(self.root, "live", "  ")
        with self.assertRaisesRegex(release_state.Refused, "not a product state"):
            release_state.move(self.root, "slipway", "the old word")
        release_state.move(self.root, "live", "Customers signed up.")
        with self.assertRaisesRegex(release_state.Refused, "already live"):
            release_state.move(self.root, "live", "again")

    def test_the_command_says_and_moves(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            release_state_main([], self.root)
        self.assertIn("state: unrecorded", out.getvalue())
        out = io.StringIO()
        with redirect_stdout(out):
            release_state_main(["pilot", "--why", "Two teams are piloting it."], self.root)
        self.assertIn("the product is pilot", out.getvalue())
        self.assertEqual(json.loads((self.root / "project.json").read_text())["state"], "pilot")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            release_state_main(["live"], self.root)


class GenerationTest(unittest.TestCase):
    def test_a_new_project_starts_pre_launch_and_a_replay_keeps_what_is_recorded(self) -> None:
        from slipwai.project.metadata import metadata
        from slipwai.release_state import NEW_STATE
        self.assertEqual(NEW_STATE, "pre-launch")
        self.assertEqual(json.loads(metadata("club", "standard", "none", [], state="pre-launch"))["state"],
                         "pre-launch")
        self.assertNotIn("state", json.loads(metadata("club", "standard", "none", [])),
                         "no state is written where none was recorded")

    def test_the_release_stage_reads_the_mode_rather_than_weighing_a_flag(self) -> None:
        from slipwai.project.flags import flag_stage
        stage = flag_stage([])
        self.assertIn("python3 scripts/agents/release_state.py", stage)
        for mode in ("**open**", "**keystone**", "**flagged**", "**promoted**"):
            self.assertIn(mode, stage)
        self.assertIn("Never move the state to make a slice easier", stage)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
