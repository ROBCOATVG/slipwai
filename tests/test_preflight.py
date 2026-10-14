"""`scripts/agents/preflight.py`: the worktree's environment asked once, before a delegate meets it.

Run the way a project runs it — the script copied into a temporary project with a `project.json` — so what
is held is its report and its exit code, not an import.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from slipwai.assets import TOOLKIT_ROOT

SCRIPT = TOOLKIT_ROOT / "scripts/agents/preflight.py"


class PreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        (place / "preflight.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        self.script = place / "preflight.py"

    def project(self, deployables: dict, extensions: list[str] | None = None) -> None:
        (self.root / "project.json").write_text(json.dumps({"deployables": deployables}), encoding="utf-8")
        if extensions is not None:
            (self.root / ".slipwai").mkdir(exist_ok=True)
            (self.root / ".slipwai/extensions.json").write_text(json.dumps({"extensions": extensions}),
                                                                  encoding="utf-8")

    def run_it(self, *flags: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.script), *flags], capture_output=True, text=True,
                              cwd=self.root, timeout=120)

    def test_a_language_nobody_checks_is_said_and_not_passed(self) -> None:
        self.project({"svc": {"language": "cobol", "path": "apps/svc", "kind": "service"}})
        done = self.run_it("--json")
        report = json.loads(done.stdout)
        row = next(row for row in report["checks"] if row["check"] == "cobol:apps/svc")
        self.assertIsNone(row["ok"])
        self.assertIn("no check recorded", row["what"])

    def test_every_project_is_asked_for_a_python_and_a_socket(self) -> None:
        self.project({})
        report = json.loads(self.run_it("--json").stdout)
        self.assertEqual({row["check"] for row in report["checks"]} & {"python", "socket"}, {"python", "socket"})

    def test_an_elected_index_that_is_not_in_the_checkout_fails_with_the_fix(self) -> None:
        """Delegates in unindexed checkouts tried the index route and fell back, one by one."""
        self.project({}, extensions=["codegraph"])
        done = self.run_it()
        self.assertEqual(done.returncode, 1)
        self.assertIn("FAIL index:codegraph", done.stdout)
        self.assertIn("missing in this checkout", done.stdout)

    def test_an_elected_index_that_is_present_passes(self) -> None:
        self.project({}, extensions=["codegraph"])
        (self.root / ".codegraph").mkdir()
        done = self.run_it()
        self.assertIn("ok   index:codegraph", done.stdout)

    def test_a_missing_toolchain_names_what_to_install(self) -> None:
        self.project({"svc": {"language": "go", "path": "apps/svc", "kind": "service"}})
        report = json.loads(self.run_it("--json").stdout)
        go = next(row for row in report["checks"] if row["check"] == "go:apps/svc")
        self.assertIn(go["ok"], (True, False))
        if not go["ok"]:
            self.assertIn("PATH", go["fix"])

    def test_the_summary_line_counts_what_failed(self) -> None:
        self.project({}, extensions=["codegraph"])
        done = self.run_it()
        self.assertIn("1 check(s) failed", done.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
