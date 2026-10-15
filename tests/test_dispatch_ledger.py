"""`scripts/agents/dispatch.py`: what was started, written at the moment of dispatch.

The decision to run one slice at a time was free and left no trace, so a run that fanned out and a run that
did not were indistinguishable afterwards except by reading a transcript by hand. These cases hold the two
halves of fixing that: it will not write a line on an answer it does not have, and when it cannot delegate
it says so in the file rather than deciding quietly.

Run as a project runs it — the script and its siblings copied into a temporary project — so what is held is
its exit code and the file it leaves behind, not an import.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"
#: Everything `dispatch.py` reaches for, and the whole of it.
SIBLINGS = ("dispatch.py", "harness.py", "logs.py", "registry.json", "clearance.py", "claims.py", "ids.py")


class LedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "project"
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in SIBLINGS:
            source = AGENTS / name
            if source.is_file():
                (place / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        (self.root / "project.json").write_text(json.dumps({"name": "t"}), encoding="utf-8")
        self.feature = self.root / "specs/036-shared"
        (self.feature / "slices").mkdir(parents=True)

    def chart(self) -> None:
        (self.feature / "chart.yaml").write_text(
            "v: 1\nfeature: 036-shared\nfairways:\n  f:\n    owns: []\nmarks: {}\n"
            "slices:\n  SB1:\n    fairway: f\n    capability: c\n    sets: []\n    steers_by: []\n"
            "  SB2:\n    fairway: f\n    capability: c\n    sets: []\n    steers_by: []\n", encoding="utf-8")

    def flown(self, delegates: bool | None, when: datetime | None = None) -> None:
        (self.root / ".slipwai").mkdir(exist_ok=True)
        at = (when or datetime.now(UTC)).isoformat(timespec="seconds").replace("+00:00", "Z")
        (self.root / ".slipwai/preflight.json").write_text(json.dumps({
            "v": 1, "at": at, "checks": [], "failed": 0, "delegates": delegates,
            "why": "Claude Code reads 13 delegate type(s) from .claude/agents/" if delegates else
                   ".claude/agents/ holds none of this project's 13 delegate types"}), encoding="utf-8")

    def run_it(self, *flags: str) -> subprocess.CompletedProcess:
        environment = {key: value for key, value in os.environ.items()
                       if key not in ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID")}
        return subprocess.run([sys.executable, "scripts/agents/dispatch.py", "--feature", "036-shared",
                               *flags], cwd=self.root, capture_output=True, text=True, timeout=120,
                              env=environment)

    def ledger(self) -> list[dict]:
        path = self.feature / "dispatch-ledger.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_it_refuses_to_write_a_line_without_a_preflight_answer(self) -> None:
        """Skipping the check is not refused. It just leaves nothing here to dispatch with."""
        self.chart()
        done = self.run_it()
        self.assertEqual(done.returncode, 1)
        self.assertIn("make preflight", done.stderr)
        self.assertEqual(self.ledger(), [])

    def test_an_answer_from_hours_ago_is_not_an_answer_about_this_checkout(self) -> None:
        self.chart()
        self.flown(True, when=datetime.now(UTC) - timedelta(hours=3))
        done = self.run_it()
        self.assertEqual(done.returncode, 1)
        self.assertIn("minutes old", done.stderr)
        self.assertEqual(self.ledger(), [])

    def test_an_unreadable_answer_is_said_rather_than_crashed_on(self) -> None:
        self.chart()
        (self.root / ".slipwai").mkdir(exist_ok=True)
        (self.root / ".slipwai/preflight.json").write_text("not json", encoding="utf-8")
        done = self.run_it()
        self.assertEqual(done.returncode, 1)
        self.assertIn("make preflight", done.stderr)

    def test_a_session_that_cannot_delegate_takes_the_earliest_and_names_the_rest(self) -> None:
        """The prose rule, applied by the thing that writes it down instead of by the thing reading it."""
        self.chart()
        self.flown(False)
        done = self.run_it()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        written = self.ledger()
        self.assertEqual([row["outcome"] for row in written][:1], ["taken-here"])
        self.assertTrue(all(row["outcome"] == "left-named" for row in written[1:]), written)
        self.assertTrue(all("delegate types" in row["why"] for row in written), written)
        self.assertTrue(all(row["delegate"] == "" for row in written), written)

    def test_a_session_that_can_delegate_records_the_worktree_and_the_type(self) -> None:
        self.chart()
        self.flown(True)
        self.assertEqual(self.run_it().returncode, 0)
        written = self.ledger()
        self.assertTrue(written, "nothing was written")
        self.assertTrue(all(row["outcome"] == "dispatched" for row in written), written)
        self.assertTrue(all(row["delegate"] == "sail-slice-watch" for row in written), written)
        self.assertTrue(all(row["worktree"].endswith(row["slice"]) for row in written), written)

    def test_the_ledger_is_appended_to_and_never_rewritten(self) -> None:
        """Its earlier lines are the whole evidence; a file that was ever rewritten has none."""
        self.chart()
        self.flown(True)
        self.run_it()
        first = self.ledger()
        self.run_it()
        self.assertEqual(self.ledger()[:len(first)], first)
        self.assertGreater(len(self.ledger()), len(first))

    def test_every_line_says_which_machine_and_which_harness_wrote_it(self) -> None:
        self.chart()
        self.flown(True)
        self.run_it()
        for row in self.ledger():
            self.assertTrue(row["machine"], row)
            self.assertEqual(row["v"], 1)
            self.assertTrue(row["t"].endswith("Z"), row)

    def test_a_feature_with_no_chart_writes_nothing_and_says_why(self) -> None:
        self.flown(True)
        done = self.run_it()
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.ledger(), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
