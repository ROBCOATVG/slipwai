"""`.slipwai/run/`: which layout a project has, the one ignore line, and the move `slipwai migrate` makes.

Shells out to git (the move leaves anything git tracks where it is), so it is in the Makefile's SLOW list.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from slipwai import logs, migrate, run_folder
from slipwai.errors import GenerationError
from slipwai.project.gitignore import RUN_STATE, build_artifacts

#: What a 2.0 project's `.gitignore` said about its run state, a name at a time.
OLD_IGNORE = """node_modules/
.slipwai/catch-up.md
.slipwai/logs/
.slipwai/run-state.json
.slipwai/running/
.slipwai/berths/
.slipwai/activity/
.specify-tools/
"""


def dead_pid() -> int:
    """A pid that was a process a moment ago and is not one now."""
    child = subprocess.Popen(["git", "--version"], stdout=subprocess.DEVNULL)
    child.wait()
    return child.pid


class LayoutTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_a_project_whose_ignore_file_names_the_folder_keeps_its_state_there(self) -> None:
        (self.root / ".gitignore").write_text("node_modules/\n.slipwai/run/\n", encoding="utf-8")
        self.assertEqual(logs.run_dir(self.root), self.root / ".slipwai/run")
        self.assertEqual(logs.deck_path(self.root, "ordering", "ORD"),
                         self.root / ".slipwai/run/logs/ordering/ORD.jsonl")

    def test_a_project_not_migrated_yet_is_read_where_it_always_was(self) -> None:
        """The board on 2.1 against a toolkit still on 2.0: the old places, not a folder nothing there reads."""
        (self.root / ".gitignore").write_text(OLD_IGNORE, encoding="utf-8")
        self.assertEqual(logs.run_dir(self.root), self.root / ".slipwai")
        self.assertEqual(logs.harbour_path(self.root, "m1"), self.root / ".slipwai/logs/harbour/m1.jsonl")

    def test_no_ignore_file_at_all_is_the_old_layout(self) -> None:
        self.assertEqual(logs.run_dir(self.root), self.root / ".slipwai")


class IgnoreBlockTest(unittest.TestCase):
    def test_a_generated_project_ignores_the_run_in_one_line(self) -> None:
        written = build_artifacts(False, [])
        lines = written.splitlines()
        self.assertEqual(RUN_STATE, ".slipwai/run/")
        self.assertEqual(lines.count(".slipwai/run/"), 1)
        under = [line for line in lines if line.startswith(".slipwai/")]
        self.assertEqual(under, [".slipwai/run/"], "nothing else under .slipwai/ is ignored: the rest is committed")

    def test_the_old_lines_become_the_one_line_where_the_first_of_them_was(self) -> None:
        rewritten = run_folder.ignore_lines(OLD_IGNORE)
        self.assertEqual(rewritten, "node_modules/\n.slipwai/run/\n.specify-tools/\n")
        self.assertEqual(run_folder.ignore_lines(rewritten), rewritten, "a second pass changes nothing")

    def test_a_committed_name_is_never_ignored_by_the_rewrite(self) -> None:
        kept = "/.slipwai/dispatch/\n.slipwai/hooks.json\n"
        self.assertEqual(run_folder.ignore_lines(kept), kept + "\n# Everything a run writes about itself, and "
                         "never a record of it (slipwai 2.1).\n.slipwai/run/\n")

    def test_an_adopted_block_is_respelled_inside_its_markers(self) -> None:
        block = ("own/\n# slipwai:delivery:begin — what the delivery material under delivery/ writes\n"
                 ".slipwai/logs/\n.slipwai/running/\ndelivery/.specify-tools/\n# slipwai:delivery:end\n")
        self.assertEqual(run_folder.ignore_lines(block),
                         "own/\n# slipwai:delivery:begin — what the delivery material under delivery/ writes\n"
                         ".slipwai/run/\ndelivery/.specify-tools/\n# slipwai:delivery:end\n")


class MoveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        subprocess.run(["git", "init", "--quiet", str(self.root)], check=True)
        (self.root / ".gitignore").write_text(OLD_IGNORE, encoding="utf-8")
        old = self.root / ".slipwai"
        (old / "logs/ordering").mkdir(parents=True)
        (old / "logs/ordering/ORD.jsonl").write_text('{"v": 1}\n', encoding="utf-8")
        (old / "acp/ORD-01").mkdir(parents=True)
        (old / "surfaces.pid").write_text("1\n", encoding="utf-8")
        (old / "catch-up.md").write_text("# notes\n", encoding="utf-8")
        (old / "dispatch").mkdir()
        (old / "dispatch/ordering.jsonl").write_text("{}\n", encoding="utf-8")
        (old / "hooks.json").write_text("{}\n", encoding="utf-8")
        (old / "tracked-note.txt").write_text("a record\n", encoding="utf-8")
        subprocess.run(["git", "add", "-f", ".slipwai/tracked-note.txt", ".slipwai/dispatch", ".slipwai/hooks.json"],
                       cwd=self.root, check=True)

    def test_the_run_state_moves_in_and_the_record_stays(self) -> None:
        moved, left, changed = run_folder.move_in(self.root)
        self.assertTrue(changed)
        self.assertEqual(left, ())
        self.assertIn(".slipwai/logs -> .slipwai/run/logs", moved)
        run = logs.run_dir(self.root)
        self.assertEqual(run, self.root / ".slipwai/run")
        self.assertEqual(logs.deck_logs(self.root), [run / "logs/ordering/ORD.jsonl"])
        for name in ("acp/ORD-01", "surfaces.pid", "catch-up.md"):
            self.assertTrue((run / name).exists(), name)
        for name in ("dispatch/ordering.jsonl", "hooks.json", "tracked-note.txt"):
            self.assertTrue((self.root / ".slipwai" / name).exists(), f"{name} is the record and stays")
        self.assertFalse((self.root / ".slipwai/logs").exists())

    def test_a_second_move_is_a_no_op(self) -> None:
        run_folder.move_in(self.root)
        before = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertEqual(run_folder.move_in(self.root), ((), (), False))
        self.assertEqual((self.root / ".gitignore").read_text(encoding="utf-8"), before)

    def test_a_file_already_at_the_new_place_is_never_written_over(self) -> None:
        (self.root / ".slipwai/run/logs/ordering").mkdir(parents=True)
        (self.root / ".slipwai/run/logs/ordering/ORD.jsonl").write_text('{"v": 1, "newer": true}\n', encoding="utf-8")
        (self.root / ".slipwai/logs/ordering/PAY.jsonl").write_text("{}\n", encoding="utf-8")
        _, left, _ = run_folder.move_in(self.root)
        self.assertEqual(len(left), 1)
        self.assertIn(".slipwai/logs/ordering/ORD.jsonl", left[0])
        self.assertIn("newer", (self.root / ".slipwai/run/logs/ordering/ORD.jsonl").read_text(encoding="utf-8"))
        self.assertTrue((self.root / ".slipwai/run/logs/ordering/PAY.jsonl").is_file(), "the rest still moves")

    def test_a_conflicted_ignore_file_is_left_to_the_person(self) -> None:
        moved, _, changed = run_folder.move_in(self.root, ignore=False)
        self.assertFalse(changed)
        self.assertTrue(moved)
        self.assertEqual((self.root / ".gitignore").read_text(encoding="utf-8"), OLD_IGNORE)


class RefusalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def running(self, place: str, pid: int) -> None:
        folder = self.root / place / "running"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "harbourmaster.pid").write_text(f"{pid}\n", encoding="utf-8")

    def test_a_live_process_under_running_stops_the_migration_with_the_command_that_fixes_it(self) -> None:
        self.running(".slipwai", os.getpid())
        with self.assertRaises(GenerationError) as refused:
            run_folder.refuse_while_out(self.root)
        said = str(refused.exception)
        self.assertIn(f"harbourmaster (pid {os.getpid()})", said)
        self.assertTrue(said.endswith(run_folder.STOP), said)

    def test_a_live_process_at_the_new_place_stops_it_too(self) -> None:
        self.running(".slipwai/run", os.getpid())
        with self.assertRaises(GenerationError):
            run_folder.refuse_while_out(self.root)

    def test_a_process_that_has_gone_is_no_fleet(self) -> None:
        self.running(".slipwai", dead_pid())
        run_folder.refuse_while_out(self.root)

    def test_migrate_refuses_before_it_merges_anything(self) -> None:
        self.running(".slipwai", os.getpid())
        with mock.patch.object(migrate, "checked", return_value={"name": "demo"}), \
                mock.patch.object(migrate, "replay") as replayed, self.assertRaises(GenerationError):
            migrate.migrate(self.root)
        replayed.assert_not_called()



class DirtTest(unittest.TestCase):
    """Untracked run state is `move_in`'s to carry, so it never stops `migrate` as uncommitted. game-club-manager
    was refused over `.slipwai/console/` and `.slipwai/stages/`, the very folders the migration moves."""

    def test_untracked_run_state_is_not_dirt(self) -> None:
        said = "?? .slipwai/console/\n?? .slipwai/stages/\n?? .slipwai/surfaces.pid"
        self.assertEqual(run_folder.dirt(said), [])

    def test_a_change_of_the_person_s_own_still_is(self) -> None:
        said = " M .specify/cruise.json\n?? .slipwai/console/\n?? notes.md"
        self.assertEqual(run_folder.dirt(said), [" M .specify/cruise.json", "?? notes.md"])

    def test_an_untracked_record_or_an_edited_tracked_file_under_slipwai_still_is(self) -> None:
        """A new hooks file or ledger is the record, and a changed tracked one is the person's change."""
        said = "?? .slipwai/hooks.json\n?? .slipwai/dispatch/\n M .slipwai/extensions.json"
        self.assertEqual(len(run_folder.dirt(said)), 3)


if __name__ == "__main__":
    unittest.main()
