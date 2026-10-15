"""`scripts/agents/preflight.py`: the worktree's environment asked once, before a delegate meets it.

Run the way a project runs it — the script copied into a temporary project with a `project.json` — so what
is held is its report and its exit code, not an import.
"""
from __future__ import annotations

import json
import os
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

    def run_it(self, *flags: str, session: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        """Run it with every harness's own session variable cleared unless a case sets one.

        Otherwise the answer depends on which harness the suite itself is running under: a run inside
        Claude Code sets `CLAUDE_CODE_SESSION_ID`, and `preflight` would read the *suite's* harness rather
        than the fixture's. Cleared here so that what each case sets is the whole of what it reads.
        """
        environment = {key: value for key, value in os.environ.items()
                       if key not in ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID")}
        return subprocess.run([sys.executable, str(self.script), *flags], capture_output=True, text=True,
                              cwd=self.root, timeout=120, env={**environment, **(session or {})})

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

    def with_harness(self, integration: str = "claude") -> None:
        """The siblings a real project has beside this script, and the Spec Kit record of what is installed."""
        for name in ("harness.py", "registry.json"):
            (self.script.parent / name).write_text(
                (TOOLKIT_ROOT / f"scripts/agents/{name}").read_text(encoding="utf-8"), encoding="utf-8")
        (self.root / ".specify").mkdir(exist_ok=True)
        (self.root / ".specify/integration.json").write_text(
            json.dumps({"installed_integrations": [integration]}), encoding="utf-8")
        (self.root / "agents").mkdir(exist_ok=True)
        (self.root / "agents/sail-slice-watch.md").write_text("brief", encoding="utf-8")

    def test_a_checkout_with_no_projected_delegate_types_fails_and_names_make_agents(self) -> None:
        """The cloud checkout. `agents/` arrives with the clone and `.claude/agents/` is ignored by git,
        so a session there reads a method built on delegates and has none to call."""
        self.project({})
        self.with_harness()
        done = self.run_it()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("FAIL delegates", done.stdout)
        self.assertIn("make agents", done.stdout)

    def test_the_projected_types_being_there_is_a_pass(self) -> None:
        self.project({})
        self.with_harness()
        (self.root / ".claude/agents").mkdir(parents=True)
        (self.root / ".claude/agents/sail-slice-watch.md").write_text("brief", encoding="utf-8")
        done = self.run_it()
        self.assertIn("ok   delegates", done.stdout)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_harness_with_no_sub_agents_is_recorded_and_never_failed(self) -> None:
        """Thirty of the registry's thirty-six rows. A gate that failed them would be turned off in a week."""
        self.project({})
        self.with_harness(integration="cline")
        done = self.run_it()
        self.assertIn("no delegate types", done.stdout)
        self.assertIn("none delegates", done.stdout)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_the_record_is_written_only_when_it_is_asked_for(self) -> None:
        """`dispatch.py` will not write a ledger line without one, and a stale one is not evidence."""
        self.project({})
        self.with_harness()
        self.run_it()
        self.assertFalse((self.root / ".slipwai/preflight.json").is_file())
        self.run_it("--record")
        written = json.loads((self.root / ".slipwai/preflight.json").read_text(encoding="utf-8"))
        self.assertIs(written["delegates"], False)
        self.assertIn("make agents", written["why"])
        self.assertTrue(written["at"].endswith("Z"))

    def test_the_session_own_harness_decides_over_what_is_installed(self) -> None:
        """Installed and running right now are different questions, and only the second one decides."""
        self.project({})
        self.with_harness(integration="cline")
        done = self.run_it(session={"CODEX_THREAD_ID": "t"})
        self.assertIn(".codex/agents", done.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
