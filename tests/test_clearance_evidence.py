"""Clearance reads two facts besides the logs: what the dispatch ledgers say was started, and what git merged.

From one run with five slices in flight: clearance said `0 running`, because the host had started them by
hand and written no `claimed` line, and offered their slots to other features' work; and a slice merged that
morning held a slot until somebody wrote its `merged` line by hand. Both answers were already in things a
reader can trust — a ledger line written at the moment of dispatch, and trunk's own history — so these cases
hold that clearance reads them, and reads them narrowly enough that neither turns into a way to mark work
done that is not.

Run as a project runs it — the script copied into a temporary git repository — because what is held is
what it says about a real history, not an import. In `SLOW`: every case builds a repository.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"
CHART = ("v: 1\nfeature: 036-shared\nfairways:\n  f:\n    owns: []\nmarks:\n  Placed: {}\n"
         "slices:\n"
         "  SB1:\n    fairway: f\n    capability: c\n    sets: []\n    steers_by: []\n"
         "  SB1X:\n    fairway: f\n    capability: c\n    sets: []\n    steers_by: []\n"
         "  SB2:\n    fairway: f\n    capability: c\n    sets: [Placed]\n    steers_by: []\n")


class EvidenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "project"
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        for name in ("clearance.py", "logs.py"):
            (place / name).write_text((AGENTS / name).read_text(encoding="utf-8"), encoding="utf-8")
        (self.root / "project.json").write_text(json.dumps({"name": "t"}), encoding="utf-8")
        (self.root / "specs/036-shared").mkdir(parents=True)
        (self.root / "specs/036-shared/chart.yaml").write_text(CHART, encoding="utf-8")
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.commit("start")

    def git(self, *argv: str) -> str:
        done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *argv], cwd=self.root,
                              capture_output=True, text=True, check=True, timeout=60)
        return done.stdout

    def commit(self, subject: str) -> None:
        self.git("commit", "-q", "--allow-empty", "-m", subject)

    def branch_merged(self, branch: str, subject: str, delete: bool = True) -> None:
        """A slice branch with work on it, merged into main the way a forge merges a pull request."""
        self.git("checkout", "-q", "-b", branch)
        self.commit(f"{branch.split('/')[-1]}: the work")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", subject, branch)
        if delete:
            self.git("branch", "-q", "-D", branch)

    def ledger(self, slice_id: str, band: str = "implement", outcome: str = "dispatched") -> None:
        path = self.root / ".slipwai/dispatch/036-shared" / f"{slice_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"v": 1, "t": "2026-10-17T08:00:00Z", "feature": "036-shared",
                                    "slice": slice_id, "band": band, "slot": 1, "outcome": outcome,
                                    "why": "slot 1 of 5", "delegate": "sail-slice-watch", "harness": "claude",
                                    "machine": "m", "worktree": f"../project-{slice_id}"}) + "\n",
                        encoding="utf-8")

    def states(self) -> dict:
        done = subprocess.run([sys.executable, "scripts/agents/clearance.py", "--json", "--feature", "036-shared"],
                              cwd=self.root, capture_output=True, text=True, timeout=120)
        found = json.loads(done.stdout)
        self.assertNotIn("error", found, found)
        return found

    def test_a_slice_its_ledger_says_was_dispatched_is_running_with_no_claimed_line(self) -> None:
        self.ledger("SB1")
        found = self.states()
        self.assertEqual(found["states"]["SB1"]["state"], "running")
        self.assertIn("dispatch ledger", found["states"]["SB1"]["why"])
        self.assertEqual(found["numbers"]["running"], 1)
        self.assertNotIn("SB1", [row["slice"] for row in found["schedule"]["start"]])

    def test_a_prepare_band_is_spent_once_the_slices_marks_are_set(self) -> None:
        """Otherwise every prepared slice waiting for its implementation slot holds one."""
        self.ledger("SB2", band="prepare")
        self.assertEqual(self.states()["states"]["SB2"]["state"], "running")
        deck = self.root / ".slipwai/logs/036-shared/f.jsonl"
        deck.parent.mkdir(parents=True, exist_ok=True)
        deck.write_text(json.dumps({"v": 1, "t": "2026-10-17T09:00:00Z", "kind": "mark-set", "fairway": "f",
                                    "slice": "SB2", "mark": "Placed"}) + "\n", encoding="utf-8")
        found = self.states()
        self.assertEqual(found["states"]["SB2"]["state"], "implementation-ready")
        self.assertIn("SB2", [row["slice"] for row in found["schedule"]["start"]])

    def test_a_slice_whose_branch_trunk_merged_is_done_after_the_forge_deletes_the_branch(self) -> None:
        self.ledger("SB1")
        self.branch_merged("slice/SB1", "Merge pull request #39 from owner/slice/SB1")
        found = self.states()
        self.assertEqual(found["states"]["SB1"]["state"], "done")
        self.assertIn("read from git", found["states"]["SB1"]["why"])
        self.assertEqual(found["numbers"]["running"], 0)

    def test_a_branch_cut_from_a_merged_one_is_not_merged_with_it(self) -> None:
        """A slice branch cut from another and not yet worked on has that one's tip, so the tip says nothing."""
        self.ledger("SB1")
        self.git("checkout", "-q", "-b", "slice/SB1X")
        self.commit("SB1X: the work")
        self.git("branch", "-q", "slice/SB1")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", "Merge pull request #40 from owner/slice/SB1X", "slice/SB1X")
        found = self.states()
        self.assertEqual(found["states"]["SB1X"]["state"], "done")
        self.assertEqual(found["states"]["SB1"]["state"], "running")

    def test_a_longer_id_that_begins_with_this_one_is_not_this_one(self) -> None:
        """SB10VB merging is not SB10V merging; the run this came from had both."""
        self.ledger("SB1")
        self.branch_merged("slice/SB1X", "Merge pull request #40 from owner/slice/SB1X")
        found = self.states()
        self.assertEqual(found["states"]["SB1X"]["state"], "done")
        self.assertEqual(found["states"]["SB1"]["state"], "running")

    def test_trunk_merged_into_a_slice_branch_is_not_the_slice_landing(self) -> None:
        """Trunk's history holds that merge once the branch lands somewhere else; only first-parent counts."""
        self.ledger("SB1")
        self.git("checkout", "-q", "-b", "slice/SB1")
        self.commit("SB1: the work")
        self.git("merge", "-q", "--no-ff", "-m", "Merge branch 'main' into slice/SB1", "main")
        self.git("checkout", "-q", "-b", "elsewhere")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", "Merge branch 'elsewhere'", "elsewhere")
        self.git("branch", "-q", "-D", "slice/SB1")
        self.assertEqual(self.states()["states"]["SB1"]["state"], "running")

    def test_a_free_disk_floor_holds_every_slot(self) -> None:
        (self.root / "harbour.json").write_text(json.dumps({"boilers": 5, "disk_floor_gb": 10 ** 9}),
                                                encoding="utf-8")
        found = self.states()
        self.assertEqual(found["schedule"]["start"], [])
        self.assertTrue(found["schedule"]["queued"])
        self.assertTrue(all("disk_floor_gb" in row["why"] for row in found["schedule"]["queued"]))
        self.assertIn("git worktree remove", found["held"])

    def test_no_floor_or_room_to_spare_holds_nothing(self) -> None:
        (self.root / "harbour.json").write_text(json.dumps({"boilers": 5, "disk_floor_gb": 0.001}),
                                                encoding="utf-8")
        found = self.states()
        self.assertEqual(found["held"], "")
        self.assertTrue(found["schedule"]["start"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
