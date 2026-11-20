"""A merged slice's worktree is cleared away, and one that has not merged is listed and left.

A berth was removed only in the moment its slice merged, and only where git agreed: a build's output lying
in it kept it, and so did a captain stopped a moment early. They stayed beside the project for good.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"


def moorings() -> Any:
    sys.path.insert(0, str(AGENTS))
    found = importlib.util.spec_from_file_location("toolkit_moorings", AGENTS / "moorings.py")
    assert found is not None and found.loader is not None
    made = importlib.util.module_from_spec(found)
    found.loader.exec_module(made)
    return made


class TidyTest(unittest.TestCase):
    moorings: Any = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.moorings = moorings()

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()) / "project"
        self.root.mkdir()
        self.git("init", "--quiet", "--initial-branch=main")
        (self.root / "service.txt").write_text("one\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "the skeleton")

    def git(self, *argv: str, where: Path | None = None) -> str:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                              cwd=where or self.root, capture_output=True, text=True, check=True).stdout

    def berth(self, slice_id: str) -> Path:
        where = self.root.parent / f"project-{slice_id}"
        self.git("worktree", "add", "--quiet", "-b", f"slice/{slice_id}", str(where), "main")
        return where

    def test_a_merged_slice_s_berth_goes_with_whatever_a_build_left_in_it(self) -> None:
        where = self.berth("S1")
        (where / "build.log").write_text("output nobody tracks\n", encoding="utf-8")
        said = self.moorings.tidy(self.root, {"S1"}, set())
        self.assertFalse(where.exists(), said)
        self.assertEqual(said, ["project-S1: S1 is merged; removed"])

    def test_a_merged_slice_s_berth_with_tracked_edits_nobody_committed_is_kept_and_says_so(self) -> None:
        where = self.berth("S1")
        (where / "service.txt").write_text("two, and never committed\n", encoding="utf-8")
        said = self.moorings.tidy(self.root, {"S1"}, set())
        self.assertTrue(where.is_dir())
        self.assertIn("1 tracked file(s) there are edited and not committed (service.txt)", said[0])

    def test_a_slice_that_has_not_merged_is_listed_and_left(self) -> None:
        where = self.berth("S2")
        said = self.moorings.tidy(self.root, set(), set())
        self.assertTrue(where.is_dir())
        self.assertIn("S2 has not merged, so it stays", said[0])
        self.assertEqual(self.moorings.tidy(self.root, set(), set(), say=False), [], "cast-off says nothing of it")

    def test_a_slice_in_flight_is_not_touched_or_spoken_of(self) -> None:
        where = self.berth("S3")
        self.assertEqual(self.moorings.tidy(self.root, {"S3"}, {"S3"}), [])
        self.assertTrue(where.is_dir())

    def test_git_s_record_of_a_berth_somebody_deleted_by_hand_is_dropped(self) -> None:
        where = self.berth("S4")
        shutil.rmtree(where)
        self.moorings.tidy(self.root, set(), set())
        self.assertNotIn("project-S4", self.git("worktree", "list"))

    def test_a_folder_that_only_has_the_name_is_never_taken_for_a_berth(self) -> None:
        impostor = self.root.parent / "project-S9"
        impostor.mkdir()
        self.assertEqual(self.moorings.tidy(self.root, {"S9"}, set()), [])
        self.assertTrue(impostor.is_dir())


if __name__ == "__main__":
    unittest.main()
