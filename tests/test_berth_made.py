"""A slice's worktree is made without an upstream, and an attempt that made only the branch is tried again.

manda's S72, S78, S83 and S97 each parked for a person on `a worktree for slice/<id> could not be made`,
with git's last word a hint about `--set-upstream-to`. The branch was there afterwards and the same command
worked when run again: captains abreast had each cut a branch from `origin/main`, git writes such a branch
an upstream in `.git/config`, and one of them lost that file to another.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from test_berth_furnishing import git, moorings


class BerthMadeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        self.root = self.home / "project"
        self.root.mkdir()
        (self.root / "a.txt").write_text("a\n", encoding="utf-8")
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "scaffold")
        git(self.home, "clone", "-q", "--bare", str(self.root), "forge.git")
        git(self.root, "remote", "add", "origin", str(self.home / "forge.git"))
        git(self.root, "fetch", "-q", "origin")
        self.module = moorings()

    def said(self, *argv: str) -> str:
        return subprocess.run(["git", *argv], cwd=self.root, capture_output=True, text=True, check=False).stdout.strip()

    def test_a_berth_cut_from_the_remote_s_trunk_is_given_no_upstream(self) -> None:
        made = self.module.add_worktree(self.root, self.home / "project-S1", "slice/S1", "origin/main")
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertEqual(self.said("config", "--get", "branch.slice/S1.merge"), "")
        self.assertEqual(self.said("rev-parse", "slice/S1"), self.said("rev-parse", "origin/main"))

    def test_an_attempt_that_made_the_branch_and_no_berth_is_tried_again(self) -> None:
        real = self.module.git
        seen: list[tuple[str, ...]] = []

        def once_refused(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
            if argv[:2] == ("worktree", "add") and "-b" in argv and not seen:
                seen.append(argv)
                real(root, "branch", "--no-track", "slice/S1", "origin/main")
                return subprocess.CompletedProcess(list(argv), 128, "", "error: could not lock config file\n"
                                                   "hint:   git branch --set-upstream-to=origin/refs/heads/main\n")
            return real(root, *argv)

        with mock.patch.object(self.module, "git", once_refused), mock.patch.object(self.module.time, "sleep"):
            made = self.module.add_worktree(self.root, self.home / "project-S1", "slice/S1", "origin/main")
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertTrue((self.home / "project-S1" / "a.txt").is_file())


if __name__ == "__main__":
    unittest.main()
