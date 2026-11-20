"""Casting off publishes the plan first: the chart a captain reads is on the trunk its slices are cut from.

A launch committed the chart and the split in the project's checkout and pushed nothing; the fleet cast off
after it claimed three slices whose worktrees, cut from `origin/main`, held nothing of them.
"""
from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

CHART = "slices:\n  S1: {fairway: a}\n"


def module() -> Any:
    found = importlib.util.spec_from_file_location("toolkit_published", TOOLKIT_ROOT / "scripts/agents/published.py")
    assert found is not None and found.loader is not None
    made = importlib.util.module_from_spec(found)
    found.loader.exec_module(made)
    return made


published = module()


def git(where: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *arguments], cwd=where,
                          capture_output=True, text=True, check=True).stdout.strip()


class PublishTest(unittest.TestCase):
    def setUp(self) -> None:
        home = Path(tempfile.mkdtemp())
        self.origin, self.root, self.other = home / "origin.git", home / "project", home / "other"
        git(home, "init", "--quiet", "--bare", "--initial-branch=main", str(self.origin))
        git(home, "clone", "--quiet", str(self.origin), str(self.root))
        git(self.root, "checkout", "--quiet", "-b", "main")
        self.commit(self.root, "README.md", "a project\n")
        git(self.root, "push", "--quiet", "-u", "origin", "main")
        git(home, "clone", "--quiet", str(self.origin), str(self.other))

    def commit(self, where: Path, name: str, text: str) -> None:
        (where / name).parent.mkdir(parents=True, exist_ok=True)
        (where / name).write_text(text, encoding="utf-8")
        git(where, "add", "-A")
        git(where, "commit", "--quiet", "-m", f"write {name}")

    def on_trunk(self) -> str:
        return git(self.origin, "rev-parse", "main")

    def test_a_checkout_at_the_remote_s_commit_has_nothing_to_publish(self) -> None:
        self.assertEqual(published.publish(self.root), (True, ""))

    def test_a_plan_committed_here_and_not_pushed_is_pushed_before_anything_is_lit(self) -> None:
        self.commit(self.root, "specs/002-more/chart.yaml", CHART)
        self.assertNotEqual(self.on_trunk(), git(self.root, "rev-parse", "HEAD"))
        fine, said = published.publish(self.root)
        self.assertTrue(fine, said)
        self.assertIn("pushed 1 commit(s)", said)
        self.assertEqual(self.on_trunk(), git(self.root, "rev-parse", "HEAD"), "a slice cut from the remote holds it")

    def test_a_checkout_that_is_only_behind_is_left_alone(self) -> None:
        """The fleet's own merges land on the remote all day; the checkout it was cast off from lags them."""
        self.commit(self.other, "apps/a.txt", "merged work\n")
        git(self.other, "push", "--quiet", "origin", "main")
        self.assertEqual(published.publish(self.root), (True, ""))

    def test_a_plan_only_here_while_the_remote_has_moved_refuses_and_says_what_to_do(self) -> None:
        self.commit(self.other, "apps/a.txt", "merged work\n")
        git(self.other, "push", "--quiet", "origin", "main")
        self.commit(self.root, "docs/event-model/model.yaml", "slices:\n  - id: S2\n")
        fine, said = published.publish(self.root)
        self.assertFalse(fine)
        self.assertIn("change the chart or the model and are not on origin/main", said)
        self.assertIn("cast off again", said)

    def test_commits_only_here_that_leave_the_plan_alone_do_not_hold_a_diverged_checkout(self) -> None:
        self.commit(self.other, "apps/a.txt", "merged work\n")
        git(self.other, "push", "--quiet", "origin", "main")
        self.commit(self.root, "notes.md", "a note\n")
        self.assertEqual(published.publish(self.root), (True, ""))

    def test_a_plan_on_a_branch_that_is_not_trunk_is_not_pushed_as_trunk(self) -> None:
        git(self.root, "checkout", "--quiet", "-b", "trying")
        self.commit(self.root, "specs/002-more/chart.yaml", CHART)
        before = self.on_trunk()
        fine, said = published.publish(self.root)
        self.assertFalse(fine)
        self.assertIn("on trying, which is not main", said)
        self.assertEqual(self.on_trunk(), before)

    def test_a_project_with_no_remote_has_nothing_to_publish_to(self) -> None:
        alone = Path(tempfile.mkdtemp())
        git(alone, "init", "--quiet", "--initial-branch=main")
        self.commit(alone, "specs/001-x/chart.yaml", CHART)
        self.assertEqual(published.publish(alone), (True, ""))


if __name__ == "__main__":
    unittest.main()
