"""What clearance says about a feature it cannot answer for.

`chart()` takes the first feature with a chart, so a project with two features and one chart answered for
the charted one whatever it was asked about — and a `/sail 036` on the uncharted one read every slice of
the *other* feature as queued or blocked, took that for *nothing may start*, and went its own way. A calm
wrong answer is the worst thing this command can give, which is why it is a refusal and its own suite.
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


class RefusalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "project"
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        for name in ("clearance.py", "logs.py", "ids.py", "claims.py"):
            source = ROOT / "assets/toolkit/scripts/agents" / name
            if source.is_file():
                shutil.copy(source, place / name)

    def feature(self, name: str, charted: bool) -> None:
        where = self.root / "specs" / name
        where.mkdir(parents=True, exist_ok=True)
        if charted:
            (where / "chart.yaml").write_text(
                f"v: 1\nfeature: {name}\nfairways:\n  f: {{}}\nmarks: {{}}\n"
                f"slices:\n  S1:\n    fairway: f\n    capability: c\n    sets: []\n    steers_by: []\n",
                encoding="utf-8")

    def run_it(self, *flags: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "scripts/agents/clearance.py", *flags],
                              cwd=self.root, capture_output=True, text=True, check=False)

    def test_a_named_feature_with_no_chart_cannot_be_scheduled(self) -> None:
        self.feature("001-first", charted=True)
        self.feature("036-second", charted=False)
        done = self.run_it("--feature", "036-second")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("cannot schedule 036-second", done.stderr)
        self.assertIn("001-first", done.stderr)

    def test_the_refusal_is_the_json_error_too(self) -> None:
        self.feature("001-first", charted=True)
        self.feature("036-second", charted=False)
        done = self.run_it("--json", "--feature", "036-second")
        self.assertEqual(done.returncode, 1)
        self.assertIn("cannot schedule", json.loads(done.stdout)["error"])

    def test_answering_for_one_feature_says_which_it_is_not_about(self) -> None:
        self.feature("001-first", charted=True)
        self.feature("036-second", charted=False)
        done = self.run_it()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("about 001-first alone", done.stdout)
        self.assertIn("036-second", done.stdout)

    def test_a_project_with_no_chart_at_all_is_still_the_calm_answer(self) -> None:
        """Adopted, before its first chart. Nothing was asked for, so nothing is refused."""
        done = self.run_it()
        self.assertEqual(done.returncode, 0)
        self.assertIn("no chart yet", done.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
