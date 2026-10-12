"""A reconstructed base has the same three-way text semantics as Git's history base."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import checkout_packages  # noqa: F401

from slipwai import migration_merge
from slipwai.errors import GenerationError
from slipwai.migration_merge import git, install, merge, modes, tracked


class MergeTest(unittest.TestCase):
    def test_person_only_and_factory_only_changes_are_both_retained(self) -> None:
        result = merge({"ours": b"old", "theirs": b"old"},
                       {"ours": b"person", "theirs": b"old", "own-page": b"own"},
                       {"ours": b"old", "theirs": b"factory", "new-page": b"new"})
        self.assertEqual(result.files, {"ours": b"person", "theirs": b"factory",
                                        "own-page": b"own", "new-page": b"new"})
        self.assertFalse(result.conflicts)

    def test_separate_hunks_in_a_renamed_file_merge(self) -> None:
        before = b"first\nkeep\nkeep\nkeep\nlast\n"
        result = merge({"new": before}, {"new": before.replace(b"first", b"person")},
                       {"new": before.replace(b"last", b"factory")})
        self.assertEqual(result.files["new"], b"person\nkeep\nkeep\nkeep\nfactory\n")
        self.assertFalse(result.conflicts)

    def test_old_windows_newlines_do_not_make_independent_edits_conflict(self) -> None:
        before = b"first\r\nkeep\r\nkeep\r\nkeep\r\nlast\r\n"
        own = before.replace(b"first", b"person")
        offered = before.replace(b"last", b"factory").replace(b"\r\n", b"\n")
        result = merge({"page": before}, {"page": own}, {"page": offered})
        self.assertFalse(result.conflicts)
        self.assertEqual(result.files["page"], own.replace(b"last", b"factory"))

    def test_competing_edits_keep_conflict_markers_and_all_three_index_stages(self) -> None:
        result = merge({"new": b"before\n"}, {"new": b"person\n"}, {"new": b"factory\n"})
        self.assertIn(b"<<<<<<< ours/new", result.files["new"])
        self.assertEqual(result.conflicts["new"], (b"before\n", b"person\n", b"factory\n"))

    def test_delete_modify_and_binary_conflicts_are_not_silently_lost(self) -> None:
        result = merge({"deleted": b"old", "binary": b"\0old"}, {"binary": b"\0own"},
                       {"deleted": b"new", "binary": b"\0new"})
        self.assertEqual(set(result.conflicts), {"deleted", "binary"})
        self.assertEqual(result.files["binary"], b"\0own")


class RemedyTest(unittest.TestCase):
    """Every refusal ends with the command that fixes it, and never with one that destroys commits."""

    def test_a_failure_before_the_undo_point_does_not_send_a_person_to_a_stale_orig_head(self) -> None:
        with tempfile.TemporaryDirectory() as scratch, self.assertRaises(GenerationError) as caught:
            git(Path(scratch), "rev-parse", "HEAD")
        message = str(caught.exception)
        self.assertNotIn("ORIG_HEAD", message)
        self.assertIn("Nothing in this project was changed", message)
        self.assertIn("slipwai migrate", message)


class GitMergeTest(unittest.TestCase):
    def command(self, *args: str) -> str:
        done = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True)
        return done.stdout.strip()

    def fixture(self, own: bytes, new: bytes) -> tuple[dict[str, bytes], dict[str, bytes], str]:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.command("init", "-q", "-b", "main")
        self.command("config", "user.name", "proof")
        self.command("config", "user.email", "proof@example.invalid")
        (self.root / "new.md").write_bytes(b"first\nkeep\nkeep\nkeep\nlast\n")
        self.command("add", "-A")
        self.command("commit", "-qm", "base")
        before = tracked(self.root)
        self.command("checkout", "-qb", "offered")
        (self.root / "new.md").write_bytes(new)
        self.command("add", "-A")
        self.command("commit", "-qm", "offered")
        theirs, commit = tracked(self.root), self.command("rev-parse", "HEAD")
        self.command("checkout", "-q", "main")
        (self.root / "new.md").write_bytes(own)
        self.command("add", "-A")
        self.command("commit", "-qm", "person")
        return before, theirs, commit

    def test_gits_own_control_files_are_written_with_the_newline_git_reads(self) -> None:
        """A `\\n` in MERGE_HEAD is a byte, not a line ending, and Python's text mode does not know it.

        On Windows the default translation wrote `<sha>\\r\\n`; git read the object name as `<sha>\\r` and
        the crossing died with "Corrupt MERGE_HEAD file" *after* the merge was half made — the worst
        moment for it, in somebody else's repository. Read as bytes and on every platform, because the
        platform this was written on cannot reproduce it.

        Down the conflict path, which is where these files survive: a clean commit removes them.
        """
        before, theirs, commit = self.fixture(b"person\nkeep\nkeep\nkeep\nlast\n",
                                              b"factory\nkeep\nkeep\nkeep\nlast\n")
        install(self.root, merge(before, tracked(self.root), theirs), commit, "Crossing", modes(self.root))
        self.assertEqual(self.command("rev-parse", "MERGE_HEAD"), commit)
        for name in ("MERGE_HEAD", "MERGE_MODE", "MERGE_MSG"):
            path = self.root / self.command("rev-parse", "--git-path", name)
            with self.subTest(control=name):
                self.assertTrue(path.is_file(), f"{name} is not there to check")
                self.assertNotIn(b"\r\n", path.read_bytes(), f"{name} carries a translated line ending")

    def test_clean_crossing_is_one_merge_commit_with_the_real_project_undo_point(self) -> None:
        before, theirs, commit = self.fixture(b"person\nkeep\nkeep\nkeep\nlast\n",
                                              b"first\nkeep\nkeep\nkeep\nfactory\n")
        original = self.command("rev-parse", "HEAD")
        install(self.root, merge(before, tracked(self.root), theirs), commit, "Crossing", modes(self.root))
        self.assertEqual(self.command("rev-list", "--parents", "-1", "HEAD").split()[1:], [original, commit])
        self.assertEqual(self.command("rev-parse", "ORIG_HEAD"), original)
        self.assertEqual((self.root / "new.md").read_bytes(), b"person\nkeep\nkeep\nkeep\nfactory\n")
        self.assertEqual(self.command("status", "--porcelain"), "")

    def test_ignored_person_file_refuses_before_the_undo_point_or_any_file_changes(self) -> None:
        before, theirs, commit = self.fixture(b"person\nkeep\nkeep\nkeep\nlast\n",
                                              b"first\nkeep\nkeep\nkeep\nfactory\n")
        own = tracked(self.root)
        (self.root / ".git/info/exclude").write_text("local.cache\n", encoding="utf-8")
        (self.root / "local.cache").write_bytes(b"person's local cache")
        result = merge(before, own, theirs)
        result.files["local.cache"] = b"factory replacement"
        from slipwai.errors import GenerationError
        with self.assertRaisesRegex(GenerationError, "ignored or untracked"):
            install(self.root, result, commit, "Crossing", modes(self.root))
        self.assertEqual(tracked(self.root), own)
        self.assertEqual((self.root / "local.cache").read_bytes(), b"person's local cache")
        self.assertEqual(self.command("rev-parse", "HEAD"), self.command("rev-parse", "refs/heads/main"))
        refused = subprocess.run(["git", "rev-parse", "--verify", "ORIG_HEAD"], cwd=self.root,
                                 capture_output=True, check=False)
        self.assertNotEqual(refused.returncode, 0)

    def test_only_a_crossing_that_wrote_orig_head_offers_the_undo_that_rewinds_to_it(self) -> None:
        before, theirs, commit = self.fixture(b"person\nkeep\nkeep\nkeep\nlast\n",
                                              b"first\nkeep\nkeep\nkeep\nfactory\n")
        with self.assertRaises(GenerationError) as early:
            git(self.root, "rev-parse", "--verify", "refs/heads/absent")
        self.assertNotIn("ORIG_HEAD", str(early.exception))
        install(self.root, merge(before, tracked(self.root), theirs), commit, "Crossing", modes(self.root))
        with self.assertRaises(GenerationError) as late:
            git(self.root, "rev-parse", "--verify", "refs/heads/absent")
        self.assertIn("git reset --hard ORIG_HEAD", str(late.exception))

    def test_no_one_git_command_line_carries_a_whole_projects_paths(self) -> None:
        before, theirs, commit = self.fixture(b"person\nkeep\nkeep\nkeep\nlast\n",
                                              b"first\nkeep\nkeep\nkeep\nfactory\n")
        result = merge(before, tracked(self.root), theirs)
        result.files.update({f"apps/service/src/main/java/com/example/orders/Order{number:05d}.java": b"x\n"
                             for number in range(1000)})
        original, lengths = migration_merge.git, []

        def spy(root: Path, *arguments: str, data: bytes | None = None) -> bytes:
            lengths.append(sum(len(part) + 1 for part in arguments))
            return original(root, *arguments, data=data)

        with patch("slipwai.migration_merge.git", spy):
            install(self.root, result, commit, "Crossing", modes(self.root))
        # Windows refuses a command line over 32767 characters, and the OSError it would raise here lands
        # after `materialise` has already rewritten the working tree.
        self.assertGreater(sum(len(name) for name in result.files), 32767)
        self.assertLess(max(lengths), 32000)
        self.assertEqual(self.command("status", "--porcelain"), "")
        self.assertEqual(len(tracked(self.root)), len(result.files))

    def test_conflict_is_normal_git_state_and_abort_restores_the_persons_work(self) -> None:
        before, theirs, commit = self.fixture(b"person\nkeep\nkeep\nkeep\nlast\n",
                                              b"factory\nkeep\nkeep\nkeep\nlast\n")
        original = self.command("rev-parse", "HEAD")
        own = tracked(self.root)
        install(self.root, merge(before, own, theirs), commit, "Crossing", modes(self.root))
        self.assertEqual(self.command("diff", "--name-only", "--diff-filter=U"), "new.md")
        self.assertEqual(self.command("rev-parse", "MERGE_HEAD"), commit)
        self.command("merge", "--abort")
        self.assertEqual(self.command("rev-parse", "HEAD"), original)
        self.assertEqual(tracked(self.root), own)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
