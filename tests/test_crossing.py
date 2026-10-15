"""`scripts/check-crossing.py`: what a migration carried, and what it could not.

The merge carries the files; it cannot carry the state those files are about. One repository migrated
cleanly and twenty minutes later had one chart covering the first of its two features, eleven slices still
marked `modelled` that were built and merged, a log ref the design names and nothing had ever created, and
no hook path. Every gate it had passed. These are those questions, asked out loud.

A report and not a gate unless asked, so the cases hold both: what it says, and that it only fails under
`--strict`. A project mid-crossing is not a broken project.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from slipwai.assets import TOOLKIT_ROOT

GATE = TOOLKIT_ROOT / "scripts/check-crossing.py"


class CrossingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "project"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "project.json").write_text(json.dumps({"name": "t"}), encoding="utf-8")
        shutil.copy(GATE, self.root / "scripts/check-crossing.py")
        self.git("init", "--quiet", "--initial-branch=main")

    def git(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                              cwd=self.root, capture_output=True, text=True, check=False)

    def feature(self, name: str, *, chart: list[str] | None = None,
                slices: list[str] | None = None) -> Path:
        where = self.root / "specs" / name
        where.mkdir(parents=True, exist_ok=True)
        for one in slices or []:
            (where / "slices" / one).mkdir(parents=True, exist_ok=True)
        if chart is not None:
            (where / "chart.yaml").write_text(
                f"v: 1\nfeature: {name}\nmarks: {{}}\nslices:\n"
                + "".join(f"  {one}:\n    fairway: f\n" for one in chart), encoding="utf-8")
        return where

    def run_it(self, *flags: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "scripts/check-crossing.py", *flags], cwd=self.root,
                              capture_output=True, text=True, check=False)

    def rows(self) -> dict[str, dict]:
        done = self.run_it("--json")
        return {row["check"]: row for row in json.loads(done.stdout)["checks"]}

    def test_a_feature_with_no_chart_is_owed_and_named(self) -> None:
        """The failure this exists for: clearance answers for charted features, so an uncharted one is not
        half-scheduled — it is invisible, and a `/sail` on it gets another feature's answer."""
        self.feature("001-first", chart=["S1"])
        self.feature("036-second", chart=None, slices=["SB1"])
        row = self.rows()["charts"]
        self.assertIs(row["ok"], False)
        self.assertIn("036-second", row["what"])
        self.assertIn("make chart", row["fix"])

    def test_every_feature_charted_is_a_pass(self) -> None:
        self.feature("001-first", chart=["S1"])
        self.feature("036-second", chart=["SB1"], slices=["SB1"])
        self.assertIs(self.rows()["charts"]["ok"], True)

    def test_a_slice_folder_in_no_chart_is_owed(self) -> None:
        self.feature("036-second", chart=["SB1"], slices=["SB1", "UI9"])
        row = self.rows()["covered"]
        self.assertIs(row["ok"], False)
        self.assertIn("036-second/UI9", row["what"])

    def test_no_mark_has_ever_been_set_is_owed_with_the_one_command(self) -> None:
        self.feature("036-second", chart=["SB1"], slices=["SB1"])
        row = self.rows()["marks"]
        self.assertIs(row["ok"], False)
        self.assertIn("--baseline-marks", row["fix"])

    def test_a_recorded_mark_is_a_pass(self) -> None:
        self.feature("036-second", chart=["SB1"], slices=["SB1"])
        path = self.root / ".slipwai/logs/036-second/f.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"v": 1, "kind": "mark-set", "slice": "SB1"}) + "\n", encoding="utf-8")
        self.assertIs(self.rows()["marks"]["ok"], True)

    def test_a_project_with_no_remote_is_asked_nothing_about_travel(self) -> None:
        """One machine. Everything works; nothing travels, and that is not something owed."""
        self.feature("036-second", chart=["SB1"])
        self.assertIsNone(self.rows()["travel"]["ok"])

    def test_a_remote_with_no_log_ref_is_owed(self) -> None:
        self.feature("036-second", chart=["SB1"])
        self.git("remote", "add", "origin", str(self.root / "nowhere.git"))
        row = self.rows()["travel"]
        self.assertIs(row["ok"], False)
        self.assertIn("make depart", row["fix"])

    def test_an_unset_hook_path_is_owed_and_a_set_one_passes(self) -> None:
        self.feature("036-second", chart=["SB1"])
        (self.root / ".githooks").mkdir()
        self.assertIs(self.rows()["hooks"]["ok"], False)
        self.git("config", "core.hooksPath", ".githooks")
        self.assertIs(self.rows()["hooks"]["ok"], True)

    def test_it_reports_without_failing_unless_strict(self) -> None:
        """A project mid-crossing is not a broken project; a command that refused to run is one nobody
        runs twice. `--strict` is what the migration's own follow-up asks for."""
        self.feature("036-second", chart=None, slices=["SB1"])
        self.assertEqual(self.run_it().returncode, 0)
        self.assertIn("OWED", self.run_it().stdout)
        self.assertEqual(self.run_it("--strict").returncode, 1)

    def test_an_empty_project_is_asked_nothing_it_cannot_answer(self) -> None:
        """Adopted, before its first chart. Everything here is `none`, and nothing is owed."""
        done = self.run_it("--strict")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("nothing owed", done.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
