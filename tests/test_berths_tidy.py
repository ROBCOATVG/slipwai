"""A merged slice's worktree is cleared away, and one that has not merged is listed and left.

A berth was removed only in the moment its slice merged, and only where git agreed: a build's output lying
in it kept it, and so did a captain stopped a moment early. They stayed beside the project for good.
"""
from __future__ import annotations

import importlib.util
import json
import os
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


class Harbour(unittest.TestCase):
    """A project with one commit on `main`, and the moorings module under test. Holds no tests itself."""

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


class TidyTest(Harbour):
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

    def test_a_folder_of_that_name_that_is_a_repository_of_its_own_is_never_taken_for_a_berth(self) -> None:
        impostor = self.root.parent / "project-S9"
        impostor.mkdir()
        subprocess.run(["git", "init", "--quiet"], cwd=impostor, check=True)
        self.assertEqual(self.moorings.tidy(self.root, {"S9"}, set()), [])
        self.assertTrue(impostor.is_dir())

    def test_the_folder_of_a_slice_that_has_not_merged_is_never_swept(self) -> None:
        folder = self.root.parent / "project-S8"
        (folder / "apps/web/.vite").mkdir(parents=True)
        self.assertEqual(self.moorings.tidy(self.root, set(), set()), [])
        self.assertEqual(self.moorings.tidy(self.root, {"S8"}, {"S8"}), [], "nor one in flight")
        self.assertTrue(folder.is_dir())


def ended(child: subprocess.Popen[bytes]) -> None:
    if child.poll() is None:
        child.kill()
    child.wait()


def can_see_working_directories() -> bool:
    return os.name != "nt" and (Path("/proc/self/cwd").exists() or shutil.which("lsof") is not None)


class LeftBehindTest(Harbour):
    """What a merged slice's berth leaves on the machine goes with it: its processes, its folder, its delegates.

    manda held twelve merged slices' folders git had forgotten, 52 delegate worktrees holding 36 GB, and an
    API server running an hour after its slice merged, from a folder that no longer existed.
    """

    def sleeper(self, where: Path) -> subprocess.Popen[bytes]:
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], cwd=where,
                                 start_new_session=True, stdin=subprocess.DEVNULL)
        self.addCleanup(ended, child)
        return child

    @unittest.skipUnless(can_see_working_directories(), "needs /proc or lsof to say a process's directory")
    def test_a_process_working_in_the_berth_is_stopped_before_the_berth_is_removed(self) -> None:
        where = self.berth("S1")
        (where / "apps").mkdir()
        child = self.sleeper(where / "apps")
        said = self.moorings.tidy(self.root, {"S1"}, set())
        self.assertIsNotNone(child.poll(), "the process in the berth was still running")
        self.assertFalse(where.exists(), said)

    @unittest.skipIf(os.name == "nt", "process groups are POSIX's")
    def test_the_try_it_processes_the_berth_recorded_are_stopped_wherever_they_run(self) -> None:
        where = self.berth("S1")
        elsewhere = Path(tempfile.mkdtemp())
        child = self.sleeper(elsewhere)
        home = where / ".slipwai/try-it"
        home.mkdir(parents=True)
        (home / "state.json").write_text(json.dumps({"state": "ready", "pids": {"api": child.pid}}),
                                         encoding="utf-8")
        self.assertEqual(self.moorings.leave(self.root, where).count("process(es)"), 1)
        self.assertIsNotNone(child.poll(), "the Try it process the berth recorded was still running")
        self.assertFalse(where.exists())

    @unittest.skipIf(os.name == "nt", "process groups are POSIX's")
    def test_a_recorded_pid_that_leads_no_group_is_somebody_else_s_and_is_left(self) -> None:
        where = self.berth("S1")
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], cwd=tempfile.mkdtemp(),
                                 stdin=subprocess.DEVNULL)  # no session of its own: not one Try it started
        self.addCleanup(ended, child)
        home = where / ".slipwai/try-it"
        home.mkdir(parents=True)
        (home / "state.json").write_text(json.dumps({"pids": {"api": child.pid}}), encoding="utf-8")
        self.moorings.leave(self.root, where)
        self.assertIsNone(child.poll(), "a process that only reuses a recorded pid was ended")

    def test_a_folder_git_forgot_halfway_through_removing_is_removed_outright(self) -> None:
        where = self.berth("S1")
        real = self.moorings.git

        def raced(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
            done = real(root, *argv)
            if argv[:2] == ("worktree", "remove"):
                # A writer put a file back while git deleted: git forgets the worktree and fails.
                (where / "apps/web/.vite").mkdir(parents=True, exist_ok=True)
                (where / "apps/web/.vite/deps.json").write_text("{}", encoding="utf-8")
                return subprocess.CompletedProcess(argv, 255, "", f"error: failed to delete '{where}': "
                                                                  "Directory not empty")
            return done

        self.moorings.git = raced
        try:
            said = self.moorings.leave(self.root, where)
        finally:
            self.moorings.git = real
        self.assertEqual(said, "")
        self.assertFalse(where.exists())

    def test_a_merged_slice_s_folder_that_is_no_longer_a_worktree_is_swept_and_its_id_works_again(self) -> None:
        folder = self.root.parent / "project-S5"
        (folder / "apps/web/.vite").mkdir(parents=True)
        (folder / "CLAUDE.md").write_text("projected\n", encoding="utf-8")
        (folder / ".codegraph").mkdir()
        logs = self.root / ".slipwai/logs"
        logs.mkdir(parents=True)
        (logs / "kept.jsonl").write_text("{}\n", encoding="utf-8")
        (folder / ".slipwai").mkdir()
        self.moorings.link_folder(logs, folder / ".slipwai/logs")  # a junction on Windows, as a berth's is
        said = self.moorings.tidy(self.root, {"S5"}, set())
        self.assertFalse(folder.exists(), said)
        self.assertEqual(said, ["project-S5: S5 is merged and its folder was no longer a worktree; removed"])
        self.assertTrue((logs / "kept.jsonl").is_file(), "the link was followed into the project's deck logs")
        made, why = self.moorings.berth(self.root, "S5", "slice/S5", "main")
        self.assertIsNotNone(made, why)

    def delegate(self, name: str, landed: bool) -> Path:
        where = self.root / ".claude/worktrees" / name
        self.git("worktree", "add", "--quiet", "-b", f"worktree-{name}", str(where), "main")
        (where / f"{name}.txt").write_text("a delegate's work\n", encoding="utf-8")
        self.git("add", "-A", where=where)
        self.git("commit", "--quiet", "-m", f"{name}'s work", where=where)
        if landed:
            self.git("merge", "--quiet", "--ff-only", f"worktree-{name}")
        return where

    def test_a_delegate_s_worktree_whose_work_trunk_holds_is_removed_with_its_branch(self) -> None:
        where = self.delegate("agent-a1", landed=True)
        said = self.moorings.tidy(self.root, set(), set())
        self.assertFalse(where.exists(), said)
        self.assertEqual(said, ["agent-a1: a delegate's worktree whose work trunk holds; removed"])
        self.assertEqual(self.git("branch", "--list", "worktree-agent-a1"), "")

    def test_a_detached_delegate_worktree_on_a_commit_trunk_holds_is_removed(self) -> None:
        where = self.root / ".claude/worktrees/agent-d1"
        self.git("worktree", "add", "--quiet", "--detach", str(where), "main")
        self.moorings.tidy(self.root, set(), set())
        self.assertFalse(where.exists())

    def test_a_delegate_s_worktree_with_work_trunk_has_not_got_stays(self) -> None:
        where = self.delegate("agent-a2", landed=False)
        said = self.moorings.tidy(self.root, set(), set())
        self.assertTrue(where.is_dir())
        self.assertIn("1 delegate worktree(s) under .claude/worktrees/ hold work trunk does not", said[-1])
        self.assertEqual(self.moorings.tidy(self.root, set(), set(), say=False), [])

    def test_a_landed_delegate_worktree_with_edits_nobody_committed_stays(self) -> None:
        where = self.delegate("agent-a3", landed=True)
        (where / "service.txt").write_text("edited, never committed\n", encoding="utf-8")
        self.moorings.tidy(self.root, set(), set())
        self.assertTrue(where.is_dir())

    def test_a_folder_under_claude_worktrees_that_git_does_not_list_is_never_touched(self) -> None:
        stray = self.root / ".claude/worktrees/agent-x"
        stray.mkdir(parents=True)
        self.moorings.tidy(self.root, set(), set())
        self.assertTrue(stray.is_dir())


if __name__ == "__main__":
    unittest.main()
