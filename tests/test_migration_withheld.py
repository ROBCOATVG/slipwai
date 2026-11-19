"""The migration that stops giving a project a package's repository files removes them, and keeps a changed one (#119).

A project's `scripts/extensions/<key>/` held each package's workflows, tests and changelog. The first migration
after that stopped has the factory's side deleting them, over a real repository here, through the merge every
ordinary migration makes — so it runs git and is in the Makefile's SLOW list.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import migrate
from slipwai.replay import Replay

COPY = "scripts/extensions/indexer"
#: The copy as a project was given it before: what it runs, and the package's repository beside it.
BEFORE = {f"{COPY}/init.py": "GUIDANCE = 'one'\n", f"{COPY}/README.md": "# Indexer\n",
          f"{COPY}/CHANGELOG.md": "## 1.0.0\n", f"{COPY}/tests/test_package.py": "assert True\n",
          f"{COPY}/.github/workflows/verify.yml": "on: push\n", f"{COPY}/.gitignore": "__pycache__/\n",
          "README.md": "# pir\n"}
#: And as it is given now.
AFTER = {name: text for name, text in BEFORE.items()
         if name in (f"{COPY}/init.py", f"{COPY}/README.md", "README.md")}
#: Git as a test runs it: an identity of its own, and nothing read from the person's or the machine's config.
ALONE = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t",
         "GIT_AUTHOR_EMAIL": "t@local", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@local"}


class MigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(scratch.cleanup)
        environment = mock.patch.dict(os.environ, ALONE)
        environment.start()
        self.addCleanup(environment.stop)
        self.root = Path(scratch.name) / "pir"
        self.root.mkdir()
        self.git("init", "--quiet", "--initial-branch=main")
        self.commit(BEFORE)
        self.base = self.git("rev-parse", "HEAD")

    def git(self, *argv: str) -> str:
        return subprocess.run(["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0", "-c", "core.autocrlf=false",
                               *argv], cwd=self.root, capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, files: dict[str, str]) -> None:
        for name, text in files.items():
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(text, encoding="utf-8", newline="")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "t")

    def offer(self, files: dict[str, str]) -> Replay:
        """What a replay leaves in the project's object store: the factory's tree on the base, as FETCH_HEAD."""
        self.git("switch", "--quiet", "--detach", self.base)
        self.git("rm", "-r", "--quiet", ".")
        self.commit(files)
        self.git("branch", "--force", "offered", "HEAD")
        self.git("switch", "--quiet", "main")
        self.git("fetch", "--quiet", ".", "offered")
        return Replay(self.root, self.root, "pir", 2, "2.1.0", self.base, True)

    def tracked(self) -> list[str]:
        return sorted(self.git("ls-files", COPY).splitlines())

    def test_a_copy_left_as_it_was_given_loses_the_repositorys_files_and_nothing_else(self) -> None:
        self.commit({"README.md": "# pir\n\nThe project's own.\n"})
        _, conflicts, _ = migrate.merge_offered(self.root, self.offer(AFTER), "Migrate pir")
        self.assertEqual(conflicts, ())
        self.assertEqual(self.tracked(), [f"{COPY}/README.md", f"{COPY}/init.py"])
        self.assertFalse((self.root / COPY / "tests").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_one_somebody_changed_is_kept_as_it_is_and_the_merge_is_concluded(self) -> None:
        self.commit({f"{COPY}/CHANGELOG.md": "## 1.0.0\n\nA note somebody wrote here.\n"})
        _, conflicts, _ = migrate.merge_offered(self.root, self.offer(AFTER), "Migrate pir")
        self.assertEqual(conflicts, (), "a file nothing reads is not a question for a person")
        self.assertEqual(self.tracked(), [f"{COPY}/CHANGELOG.md", f"{COPY}/README.md", f"{COPY}/init.py"])
        self.assertIn("somebody wrote here", (self.root / COPY / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertEqual(self.git("status", "--porcelain"), "", "concluded, not left in progress")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "Migrate pir")
        self.assertEqual(len(self.git("rev-list", "--parents", "-1", "HEAD").split()), 3, "one merge commit")

    def test_a_real_conflict_beside_it_is_still_the_projects_to_decide(self) -> None:
        self.commit({f"{COPY}/CHANGELOG.md": "changed here\n", f"{COPY}/init.py": "GUIDANCE = 'mine'\n"})
        offered = self.offer({**AFTER, f"{COPY}/init.py": "GUIDANCE = 'two'\n"})
        _, conflicts, _ = migrate.merge_offered(self.root, offered, "Migrate pir")
        self.assertEqual(conflicts, (f"{COPY}/init.py",))
        self.assertEqual(self.git("diff", "--name-only", "--diff-filter=U"), f"{COPY}/init.py")
        self.assertTrue((self.root / COPY / "CHANGELOG.md").is_file())

    def test_a_script_the_package_dropped_that_was_changed_here_is_a_conflict_as_before(self) -> None:
        """Only what a project is no longer *given* has a known answer; `init.py` is not on that list."""
        self.commit({f"{COPY}/init.py": "GUIDANCE = 'mine'\n"})
        gone = {name: text for name, text in AFTER.items() if not name.endswith("init.py")}
        _, conflicts, _ = migrate.merge_offered(self.root, self.offer(gone), "Migrate pir")
        self.assertEqual(conflicts, (f"{COPY}/init.py",))


if __name__ == "__main__":
    unittest.main()
