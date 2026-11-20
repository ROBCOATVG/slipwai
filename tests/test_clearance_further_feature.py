"""Clearance asked about a further feature, whose slices are rows on the first feature's chart.

One chart per project, under the first feature. `--feature <a later one>` was refused as uncharted, a later
feature's story was looked for under the chart's feature, and only the chart feature's split was read.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
#: S1 is the chart's own; S2 and S3 are a later feature's, S4 a third's. S3 is a view steering by a mark
#: nothing has set, which only its story can give.
CHART = """v: 1
feature: 001-first
fairways: {f: {}}
marks: {}
slices:
  S1: {fairway: f, capability: c, sets: [Made], steers_by: []}
  S2: {fairway: f, capability: c, feature: 002-further, sets: [Further], steers_by: []}
  S3: {fairway: f, capability: c, feature: 002-further, pattern: state-view, sets: [], steers_by: [Made]}
  S4: {fairway: f, capability: c, feature: 003-third, sets: [], steers_by: []}
"""


class FurtherFeatureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "project"
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        for name in ("clearance.py", "logs.py", "feedback.py"):
            shutil.copy(ROOT / "assets/toolkit/scripts/agents" / name, place / name)
        for name in ("001-first", "002-further", "003-third", "004-not-on-the-chart"):
            (self.root / "specs" / name).mkdir(parents=True)
        (self.root / "specs/001-first/chart.yaml").write_text(CHART, encoding="utf-8")

    def asked(self, *flags: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "scripts/agents/clearance.py", *flags],
                              cwd=self.root, capture_output=True, text=True, check=False)

    def answer(self, feature: str) -> dict:
        done = self.asked("--json", "--feature", feature)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return json.loads(done.stdout)

    def test_a_further_feature_is_answered_with_its_own_rows_of_the_chart(self) -> None:
        found = self.answer("002-further")
        self.assertEqual((found["feature"], found["chart"]), ("002-further", "001-first"))
        self.assertEqual(sorted(found["states"]), ["S2", "S3"])
        self.assertEqual(found["ready"], {"f": ["S2"]})
        self.assertEqual(sorted(self.answer("003-third")["states"]), ["S4"])
        said = self.asked("--feature", "002-further").stdout
        self.assertIn("slices start now in 002-further, on the chart of 001-first", said)
        self.assertNotIn("  S1  ", said, "no row of its own for a slice of another feature")

    def test_the_chart_s_own_feature_is_answered_with_every_row_as_it_was(self) -> None:
        found = self.answer("001-first")
        self.assertEqual(sorted(found["states"]), ["S1", "S2", "S3", "S4"])
        self.assertNotIn("chart", found)
        said = self.asked().stdout
        self.assertIn("about 001-first alone; 004-not-on-the-chart has no chart", said)

    def test_a_feature_with_no_row_on_any_chart_still_cannot_be_scheduled(self) -> None:
        done = self.asked("--feature", "004-not-on-the-chart")
        self.assertEqual(done.returncode, 1)
        self.assertIn("cannot schedule 004-not-on-the-chart", done.stderr)

    def test_a_story_under_the_slice_s_own_feature_gives_the_mark_it_steers_by(self) -> None:
        self.assertEqual(self.answer("002-further")["states"]["S3"]["state"], "blocked")
        story = self.root / "specs/002-further/slices/S3/try-it.json"
        story.parent.mkdir(parents=True)
        story.write_text(json.dumps({"given": [{"event": "Made"}], "steps": []}), encoding="utf-8")
        self.assertEqual(self.answer("002-further")["states"]["S3"]["state"], "implementation-ready")

    def test_each_feature_s_split_is_read_for_its_own_slices(self) -> None:
        (self.root / "specs/002-further/story-split.md").write_text(
            "## Slice graph\n\n| Slice | depends_on | parallel_ok_with |\n|---|---|---|\n"
            "| S2 | S1 | — |\n| all others | S2 | — |\n", encoding="utf-8")
        why = self.answer("002-further")["states"]
        self.assertIn("S1", why["S2"]["why"])
        whole = self.answer("001-first")["states"]
        self.assertEqual(whole["S1"]["state"], "preparation-ready", "`all others` is the rest of 002, never S1")
        self.assertEqual(whole["S4"]["state"], "implementation-ready", "nor a third feature's S4")
        self.assertIn("S2", whole["S3"]["why"])

    def test_a_slice_marked_done_in_its_own_feature_s_register_is_read_as_done_marked(self) -> None:
        (self.root / "specs/002-further/slices").mkdir()
        (self.root / "specs/002-further/slices/README.md").write_text(
            "| Slice | Done |\n|---|---|\n| S2 | 2026-11-20 |\n", encoding="utf-8")
        done = self.asked("--baseline-marks")
        self.assertIn("S2 sets Further — recorded", done.stdout, done.stderr)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
