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

    def ledger(self, slice_id: str = "") -> list[dict]:
        """The run's file and every slice's own, in the order the lines were written — or one slice's."""
        place = self.root / ".slipwai/dispatch"
        paths = ([place / "036-shared" / f"{slice_id}.jsonl"] if slice_id else
                 [place / "036-shared.jsonl", *sorted((place / "036-shared").glob("*.jsonl"))])
        rows = [json.loads(line) for path in paths if path.is_file()
                for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return rows if slice_id else sorted(rows, key=lambda row: (row["t"], row["slot"]))

    def deck(self) -> list[dict]:
        place = self.root / ".slipwai/logs/036-shared"
        return [json.loads(line) for path in sorted(place.glob("*.jsonl"))
                for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def prepared_chart(self) -> None:
        """SB1 sets a mark, so it is handed `prepare` first and `implement` once the mark is set."""
        (self.feature / "chart.yaml").write_text(
            "v: 1\nfeature: 036-shared\nfairways:\n  f:\n    owns: []\nmarks:\n  Placed: {}\n"
            "slices:\n  SB1:\n    fairway: f\n    capability: c\n    sets: [Placed]\n    steers_by: []\n",
            encoding="utf-8")

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
        # With the run's other committed records, and never in the feature's specification any more.
        self.assertFalse((self.feature / "dispatch-ledger.jsonl").exists())

    def test_the_ledger_is_appended_to_and_never_rewritten(self) -> None:
        """Its earlier lines are the whole evidence; a file that was ever rewritten has none. A slice
        handed `prepare` and then `implement` is two lines in its own file, the first untouched."""
        self.prepared_chart()
        self.flown(True)
        self.assertEqual(self.run_it().returncode, 0)
        first = self.ledger("SB1")
        self.assertEqual([row["band"] for row in first], ["prepare"])
        deck = self.root / ".slipwai/logs/036-shared/f.jsonl"
        with deck.open("a", encoding="utf-8") as file:
            file.write(json.dumps({"v": 1, "t": "2026-10-17T09:00:00Z", "kind": "mark-set", "fairway": "f",
                                   "slice": "SB1", "mark": "Placed"}) + "\n")
        self.assertEqual(self.run_it().returncode, 0)
        self.assertEqual(self.ledger("SB1")[:1], first)
        self.assertEqual([row["band"] for row in self.ledger("SB1")], ["prepare", "implement"])

    def test_each_slice_has_its_own_file_so_slice_branches_never_meet_on_one(self) -> None:
        """Five slice branches appending to one shared file conflict at its last line; a file each never does."""
        self.chart()
        self.flown(True)
        self.run_it()
        for slice_id in ("SB1", "SB2"):
            self.assertEqual([row["slice"] for row in self.ledger(slice_id)], [slice_id])
        self.assertFalse((self.root / ".slipwai/dispatch/036-shared.jsonl").exists())

    def test_a_started_slice_is_claimed_so_the_next_dispatch_does_not_start_it_again(self) -> None:
        """Five slices built by hand with no `claimed` line read as `0 running`, and their slots were offered
        to other work."""
        self.chart()
        self.flown(True)
        self.run_it()
        claims = [row for row in self.deck() if row["kind"] == "claimed"]
        self.assertEqual(sorted(row["slice"] for row in claims), ["SB1", "SB2"])
        self.assertTrue(all(row["fairway"] == "f" for row in claims), claims)
        again = self.run_it()
        self.assertIn("nothing to dispatch", again.stdout)
        self.assertEqual(len(self.ledger()), 2)

    def test_a_named_slice_is_the_only_one_started(self) -> None:
        """`/sail SB2` asks for SB2, and a dispatch that followed the whole start set wrote lines for slices
        nobody had asked for — so the run wrote its own by hand and drifted from the shape."""
        self.chart()
        self.flown(True)
        done = self.run_it("--slice", "SB2")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([row["slice"] for row in self.ledger()], ["SB2"])

    def test_a_named_slice_that_may_not_start_is_said_with_clearances_reason(self) -> None:
        self.chart()
        self.flown(True)
        self.run_it("--slice", "SB2")
        done = self.run_it("--slice", "SB2,SB9")
        self.assertEqual(done.returncode, 1)
        self.assertIn("SB2 does not start now: running", done.stderr)
        self.assertIn("SB9 does not start now", done.stderr)

    def test_the_line_is_written_into_the_slices_worktree_where_one_exists(self) -> None:
        """So the slice branch commits it, and it rides in the pull request that lands the slice."""
        self.chart()
        self.flown(True)
        worktree = self.root.parent / "project-SB1"
        worktree.mkdir()
        (worktree / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        self.assertEqual(self.run_it().returncode, 0)
        copied = worktree / ".slipwai/dispatch/036-shared/SB1.jsonl"
        self.assertTrue(copied.is_file(), "the worktree has no line")
        self.assertEqual(json.loads(copied.read_text(encoding="utf-8")), self.ledger("SB1")[0])
        self.assertFalse((self.root.parent / "project-SB2/.slipwai").exists())

    def test_every_line_says_which_machine_and_which_harness_wrote_it(self) -> None:
        self.chart()
        self.flown(True)
        self.run_it()
        for row in self.ledger():
            self.assertTrue(row["machine"], row)
            self.assertEqual(row["v"], 1)
            self.assertTrue(row["t"].endswith("Z"), row)

    def shipped_without_marks(self) -> None:
        """A crossing's own state: SB1 is done in the tree and set its mark in no log, so SB2 — which
        steers by it — reads as waiting on work that merged before there was a log to write it in."""
        (self.feature / "chart.yaml").write_text(
            "v: 1\nfeature: 036-shared\nfairways:\n  f:\n    owns: []\n"
            "marks:\n  OrderPlaced: {}\n"
            "slices:\n"
            "  SB1:\n    fairway: f\n    capability: c\n    sets: [OrderPlaced]\n    steers_by: []\n"
            "  SB2:\n    fairway: f\n    capability: c\n    sets: []\n    steers_by: [OrderPlaced]\n",
            encoding="utf-8")
        (self.feature / "slices/SB1").mkdir(parents=True, exist_ok=True)
        (self.feature / "slices/README.md").write_text(
            "| Slice | What |\n|---|---|\n| `SB1` | shipped before the mark log existed |\n",
            encoding="utf-8")

    def test_it_takes_the_baseline_a_crossing_owes_rather_than_asking_for_it(self) -> None:
        """Left to a person this is a command nobody runs, and every slice steering by a shipped mark
        stays blocked for ever in a loop nobody is watching."""
        self.shipped_without_marks()
        self.flown(True)
        done = self.run_it()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        written = self.ledger()
        first = written[0]
        self.assertEqual(first["outcome"], "baselined")
        self.assertEqual(first["slice"], "")
        self.assertIn("baselined", first["why"])
        self.assertIn("SB2", [row["slice"] for row in written], "SB2 did not clear after the baseline")

    def test_the_baseline_it_took_is_stamped_in_the_log_as_derived(self) -> None:
        """An earned mark was written by the stage that did the work. A baselined one was inferred from a
        done marker, and a reader has to be able to tell which for ever."""
        self.shipped_without_marks()
        self.flown(True)
        self.run_it()
        written = [json.loads(line) for path in (self.root / ".slipwai/logs").rglob("*.jsonl")
                   for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        baselined = [row for row in written if row.get("kind") == "mark-set"]
        self.assertTrue(baselined, written)
        self.assertTrue(all(row.get("provenance") == "baseline" for row in baselined), baselined)

    def test_it_is_never_taken_twice(self) -> None:
        """One per project, ever. Otherwise it is a way past the gate rather than a crossing's catch-up."""
        self.shipped_without_marks()
        self.flown(True)
        self.run_it()
        self.flown(True)
        done = self.run_it()
        self.assertEqual(len([row for row in self.ledger() if row["outcome"] == "baselined"]), 1,
                         self.ledger())
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_feature_with_no_chart_writes_nothing_and_says_why(self) -> None:
        self.flown(True)
        done = self.run_it()
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.ledger(), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
