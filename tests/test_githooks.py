"""Pointing a checkout at the hooks it carries, and never at somebody else's.

`core.hooksPath` is per-checkout config: no clone, worktree or cloud runner inherits it. So the one rule in
the method that holds whoever is driving would, left to itself, be installed nowhere — the same shape as
the bug it exists to catch. Generation sets it and `slipwai migrate` sets it again; both call this.

The cases run against real repositories, because what is being held is git's own config resolution.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from slipwai import githooks


def git(*argv: str, where: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                          cwd=where, capture_output=True, text=True, check=False)


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        git("init", "--quiet", "--initial-branch=main", where=self.root)
        (self.root / githooks.HOOKS).mkdir()

    def configured(self) -> str:
        return git("config", "--get", githooks.KEY, where=self.root).stdout.strip()

    def test_it_points_an_unconfigured_checkout_at_the_projects_own_hooks(self) -> None:
        done = githooks.install(self.root)
        self.assertTrue(done.set, done.why)
        self.assertEqual(self.configured(), githooks.HOOKS)

    def test_running_it_again_changes_nothing_and_says_nothing(self) -> None:
        """Generation, `migrate` and `make hooks` each call it without the other two having to know."""
        githooks.install(self.root)
        done = githooks.install(self.root)
        self.assertFalse(done.set)
        self.assertEqual(done.why, "")
        self.assertEqual(self.configured(), githooks.HOOKS)

    def test_somebody_elses_hook_path_is_reported_and_never_taken(self) -> None:
        """An adopted repository may already be pointed at husky or lefthook. Repointing it quietly would
        disable their hooks and tell them nothing."""
        git("config", githooks.KEY, ".husky", where=self.root)
        done = githooks.install(self.root)
        self.assertFalse(done.set)
        self.assertIn(".husky", done.why)
        self.assertIn("Chain", done.why)
        self.assertEqual(self.configured(), ".husky")

    def test_a_checkout_without_the_hooks_directory_is_not_pointed_at_nothing(self) -> None:
        (self.root / githooks.HOOKS).rmdir()
        done = githooks.install(self.root)
        self.assertFalse(done.set)
        self.assertIn("no hooks to point at", done.why)
        self.assertEqual(self.configured(), "")

    def test_a_directory_that_is_not_a_repository_is_not_an_error(self) -> None:
        """An export, a tarball, an sdist: nothing to configure, and no failure either."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as elsewhere:
            loose = Path(elsewhere)
            (loose / githooks.HOOKS).mkdir()
            done = githooks.install(loose)
            self.assertFalse(done.set)
            self.assertIn("not a git repository", done.why)

    def test_a_subdirectory_of_a_repository_is_not_its_root(self) -> None:
        """`core.hooksPath` resolves against the top level, so setting it from inside would point the
        enclosing repository at a path that is not there."""
        inside = self.root / "apps/service"
        (inside / githooks.HOOKS).mkdir(parents=True)
        done = githooks.install(inside)
        self.assertFalse(done.set)
        self.assertIn("not a git repository", done.why)
        self.assertEqual(self.configured(), "")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
