"""`slipwai.relocate`: the records a project wrote that a newer keel keeps somewhere else.

No merge carries a file neither side generated, so `migrate` moves these itself after the merge, with
`git mv` so the history follows the file. These hold the move, the refusal to write over a file already at
the new home, and that nothing else in the tree is touched.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from slipwai.migrate import commit_says, refresh
from slipwai.relocate import relocate


class RelocateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.git("init", "--quiet", "--initial-branch=main")

    def git(self, *argv: str) -> str:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv], cwd=self.root,
                              capture_output=True, text=True, check=True).stdout

    def write(self, path: str, text: str) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(text, encoding="utf-8")

    def commit(self) -> None:
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "t")

    def test_a_feature_dispatch_ledger_moves_under_slipwai_and_is_staged(self) -> None:
        self.write("specs/001-path/dispatch-ledger.jsonl", '{"slice": "SB1"}\n')
        self.write("specs/001-path/spec.md", "# spec\n")
        self.commit()
        moved, left = relocate(self.root)
        self.assertEqual(moved, ("specs/001-path/dispatch-ledger.jsonl -> .slipwai/dispatch/001-path.jsonl",))
        self.assertEqual(left, ())
        self.assertEqual((self.root / ".slipwai/dispatch/001-path.jsonl").read_text(encoding="utf-8"),
                         '{"slice": "SB1"}\n')
        self.assertFalse((self.root / "specs/001-path/dispatch-ledger.jsonl").exists())
        self.assertTrue((self.root / "specs/001-path/spec.md").exists())
        staged = self.git("diff", "--cached", "--name-status", "-M").split()
        self.assertEqual(staged[0][0], "R", staged)

    def test_a_ledger_already_at_the_new_home_is_never_written_over(self) -> None:
        self.write("specs/001-path/dispatch-ledger.jsonl", '{"slice": "SB1"}\n')
        self.write(".slipwai/dispatch/001-path.jsonl", '{"slice": "SB2"}\n')
        self.commit()
        moved, left = relocate(self.root)
        self.assertEqual(moved, ())
        self.assertEqual(len(left), 1)
        self.assertIn("readers take both", left[0])
        self.assertEqual((self.root / ".slipwai/dispatch/001-path.jsonl").read_text(encoding="utf-8"),
                         '{"slice": "SB2"}\n')

    def test_migrates_refresh_commits_the_move_as_its_own_and_reports_it(self) -> None:
        """The commit after the merge carries the move, named as a move rather than as a projection."""
        self.write("specs/001-path/dispatch-ledger.jsonl", '{"slice": "SB1"}\n')
        self.commit()
        self.git("config", "user.name", "t")
        self.git("config", "user.email", "t@local")
        done = refresh(self.root, "warbook")
        self.assertIsNone(done.refused)
        self.assertEqual(done.relocated,
                         ("specs/001-path/dispatch-ledger.jsonl -> .slipwai/dispatch/001-path.jsonl",))
        self.assertEqual(done.changed, ())
        self.assertIn("Move warbook's records", self.git("log", "-1", "--format=%s"))
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertIn("moved specs/001-path/dispatch-ledger.jsonl", commit_says(done, merge=True))

    def test_an_untracked_or_unmatched_file_is_left_alone(self) -> None:
        self.write("specs/001-path/notes/dispatch-ledger.jsonl", "{}\n")
        self.commit()
        self.write("specs/002-other/dispatch-ledger.jsonl", "{}\n")
        self.assertEqual(relocate(self.root), ((), ()))
        self.assertTrue((self.root / "specs/002-other/dispatch-ledger.jsonl").exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
