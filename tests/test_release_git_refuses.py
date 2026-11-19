"""A release says when git cannot answer, rather than packing the working directory without a word (#126).

`release_tracked` reads the tree at `HEAD` in a repository and walks the directory outside one. Where git was absent,
or refused the directory — a `safe.directory` ownership error is the common one, in a container or on a runner with a
mounted checkout — it walked and said nothing: the fault of #117 back again, on the machines a release is cut on.
"""
from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401
from test_release_tracked import CORE, GitCase, members, repository

from slipwai import package_new, package_release, release_tracked
from slipwai.errors import GenerationError
from slipwai.language_release import pack

DUBIOUS = ("fatal: detected dubious ownership in repository at '{top}'\nTo add an exception for this directory, "
           "call:\n\n\tgit config --global --add safe.directory {top}\n")


def refusing(said: str, only: str = ""):
    """A stand-in for git that fails as git does: 128, and its reason on stderr. `only` names the one verb it
    refuses, the rest answered by the real one."""
    real = release_tracked.ran

    def ran(root: Path, argv: tuple[str, ...]) -> subprocess.CompletedProcess:
        if only and argv[0] != only:
            return real(root, argv)
        return subprocess.CompletedProcess(["git", *argv], 128, b"", said.encode())
    return mock.patch.object(release_tracked, "ran", ran)


def not_installed():
    return mock.patch.object(release_tracked, "ran", mock.Mock(side_effect=FileNotFoundError(2, "No such file", "git")))


class Case(GitCase):
    def refused(self, root: Path, verb: str = "release") -> str:
        with self.assertRaises(GenerationError) as refused:
            if verb == "release":
                package_release.release(root, self.area / "dist")
            elif verb == "register":
                package_release.register(root, self.area / "channel")
            else:
                pack(root, self.area / "dist")
        self.assertFalse((self.area / "dist").exists() or (self.area / "channel").exists(), "something was built")
        return str(refused.exception)


class StandInTest(Case):
    def test_a_checkout_git_refuses_as_not_the_user_s_is_refused_with_git_s_line_and_the_fix(self) -> None:
        root = repository(self.area)
        with refusing(DUBIOUS.format(top=root.as_posix())):
            for verb in ("release", "register", "pack"):
                said = self.refused(root, verb)
                self.assertIn(f"fatal: detected dubious ownership in repository at '{root.as_posix()}'", said)
                self.assertIn(f"`git config --global --add safe.directory {root.as_posix()}`", said)
                self.assertNotIn("To add an exception", said, "git's line, not its paragraph")

    def test_the_fix_names_the_checkout_where_git_s_words_do_not(self) -> None:
        """Git's message is translated; the setting's name is not, and the path is where `.git` is."""
        root = repository(self.area, inside="packages")
        with refusing("fatal: zweifelhafter Besitz, siehe safe.directory\n"):
            said = self.refused(root)
        self.assertIn("fatal: zweifelhafter Besitz", said)
        self.assertIn(f"safe.directory {root.parents[1].as_posix()}`", said)

    def test_a_checkout_on_a_machine_without_git_is_refused_with_install_git(self) -> None:
        root = repository(self.area)
        with not_installed():
            for verb in ("release", "register", "pack"):
                said = self.refused(root, verb)
                self.assertIn("git could not be run", said)
                self.assertIn("Install git", said)

    def test_any_other_refusal_is_quoted_and_is_not_a_walk(self) -> None:
        root = repository(self.area)
        (root / "untracked.txt").write_text("\n", encoding="utf-8")
        with refusing("warning: something first\nfatal: index file corrupt\n"):
            said = self.refused(root)
        self.assertIn("fatal: index file corrupt", said)
        self.assertIn("status", said)

    def test_a_dot_git_that_is_a_file_is_a_checkout_too(self) -> None:
        """A worktree and a submodule have a file there, naming where the repository is."""
        package_new.write("extension", "lens", self.area / "worktree", CORE)
        (self.area / "worktree/.git").write_text("gitdir: /somewhere/else\n", encoding="utf-8")
        with not_installed():
            self.assertIn("Install git", self.refused(self.area / "worktree/lens"))

    def test_a_directory_plainly_in_no_repository_is_walked_whatever_git_says(self) -> None:
        package_new.write("extension", "lens", self.area, CORE)
        (self.area / "lens/left-empty").mkdir()
        for stand_in in (not_installed(), refusing("fatal: not a git repository (or any of the parent "
                                                   "directories): .git\n")):
            with stand_in:
                archive, _, _ = package_release.release(self.area / "lens", self.area / "out")
            self.assertIn("lens/left-empty", members(archive))

    def test_a_git_that_answers_and_then_will_not_say_what_differs_is_refused(self) -> None:
        root = repository(self.area)
        (root / "README.md").write_text("edited and not committed\n", encoding="utf-8")
        with refusing("fatal: unable to read the index\n", only="status"):
            said = self.refused(root)
        self.assertIn("fatal: unable to read the index", said)


class RealGitTest(Case):
    """Git itself, made to refuse by the environment of the case alone: no setting of the person running the suite
    is read (`GIT_CONFIG_GLOBAL` is the null device here) and none is written."""

    def test_git_refusing_a_checkout_it_takes_for_another_user_s_refuses_the_release(self) -> None:
        root = repository(self.area)
        (root / "untracked.txt").write_text("in no release\n", encoding="utf-8")
        # Git's own test switch for exactly this refusal, read by every platform's build: it answers as though
        # the checkout were another user's, which no test can arrange without being root.
        with mock.patch.dict(os.environ, {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}):
            probe = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, env={**os.environ},
                                   capture_output=True, text=True, check=False)
            if probe.returncode == 0:
                self.skipTest("this git does not refuse under GIT_TEST_ASSUME_DIFFERENT_OWNER, so there is no "
                              "way to make it refuse a checkout the suite itself made")
            for verb in ("release", "register"):
                said = self.refused(root, verb)
                self.assertIn(probe.stderr.splitlines()[0], said)
                self.assertIn("git config --global --add safe.directory ", said)

    def test_a_worktree_whose_repository_is_gone_is_refused_rather_than_walked(self) -> None:
        package_new.write("extension", "lens", self.area / "worktree", CORE)
        (self.area / "worktree/.git").write_text(f"gitdir: {(self.area / 'gone').as_posix()}\n", encoding="utf-8")
        said = self.refused(self.area / "worktree/lens")
        # git's own words differ by version ("not a git repository", "gitfile does not point to a valid
        # repository"); what is held is that it refused, and quoted git rather than guessing for it.
        self.assertIn("git would not answer for it: fatal:", said)
        self.assertIn(f"({self.area / 'worktree'})", said)


if __name__ == "__main__":
    unittest.main()
