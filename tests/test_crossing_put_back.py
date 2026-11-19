"""A crossing says, as it moves version 1's run files, exactly how to put them back (#119).

The crossing moves them into `.slipwai/run/v1/` and seeds deck logs under `.slipwai/run/logs/`. `git merge
--abort` restores version 1's `.gitignore`, which ignores neither place, and git moves nothing back: the files
stayed where the crossing put them and nothing said so. No git here: the words, and that following them works.
"""
from __future__ import annotations

import shlex
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import migrate, run_folder
from slipwai.layout import layout_of
from slipwai.logs import entry
from slipwai.migration_crossing import catch_up, seeded
from slipwai.migration_flight import Flight
from slipwai.migration_result import Migration
from slipwai.replay import Replay

RUN_FILES = [".specify/cruise-run.log", "specs/cruise-checkpoint.md"]
DECKS = [".slipwai/run/logs/ordering/main.jsonl", ".slipwai/run/logs/ordering/ordering.jsonl"]
SAID = [
    "Version 1's run files are now under .slipwai/run/v1/, which this version ignores and version 1 does not. "
    "Walking away from this crossing — `git merge --abort` while it is in progress, `git reset --hard ORIG_HEAD` "
    "once it is committed — moves none of them back, and nothing here will guess that you did. To put each "
    "back where version 1 reads it:",
    "  mv .slipwai/run/v1/cruise-run.log .specify/cruise-run.log",
    "  mv .slipwai/run/v1/cruise-checkpoint.md specs/cruise-checkpoint.md",
    "The crossing also wrote version 1's history into 2 deck log(s), which stay as well. A crossing run again "
    "writes no line twice, so leave them if you will cross again. To leave none of it behind:",
    "  rm .slipwai/run/logs/ordering/main.jsonl .slipwai/run/logs/ordering/ordering.jsonl",
]


def flight() -> Flight:
    return Flight(logs=[
        ("ordering", "ordering", entry("merged", fairway="ordering", slice="ORD-01", commit="abc123")),
        ("ordering", "main", replace(entry("told", fairway="main", message="ship the gate first"),
                                     t="2026-01-01T09:00:00Z")),
        ("ordering", "main", entry("parked", fairway="main", why="the gate is red")),
    ])


class WordsTest(unittest.TestCase):
    def test_the_words_name_each_command_that_puts_a_file_back_and_the_deck_logs_that_stay(self) -> None:
        self.assertEqual(run_folder.walking_away(RUN_FILES, DECKS), SAID)

    def test_only_what_this_crossing_did_is_said(self) -> None:
        self.assertEqual(run_folder.walking_away([], []), [], "nothing moved and nothing seeded: nothing to put back")
        self.assertEqual(run_folder.walking_away(RUN_FILES, []), SAID[:3])
        only_decks = run_folder.walking_away([], DECKS[:1])
        self.assertEqual(only_decks[1], "  rm .slipwai/run/logs/ordering/main.jsonl")
        self.assertTrue(only_decks[0].startswith("This crossing wrote version 1's history into 1 deck log(s) under "
                                                 ".slipwai/run/logs/, which this version ignores and version 1 "
                                                 "does not. Walking away from this crossing"), only_decks[0])

    def test_the_catch_up_page_says_the_same_in_a_section_of_its_own(self) -> None:
        document = {"name": "orders", "layout": {"delivery": "."}}
        page = catch_up("orders", "1.5.1", "1.5.1", Flight(), layout_of(document), {}, [], run_files=RUN_FILES,
                        decks=DECKS)
        self.assertIn("## If you walk away from this crossing", page)
        for line in SAID:
            self.assertIn(line.strip(), page)
        self.assertLess(page.index("## Version 1's run files, moved"),
                        page.index("## If you walk away from this crossing"))
        bare = catch_up("orders", "1.5.1", "1.5.1", Flight(), layout_of(document), {}, [])
        self.assertNotIn("## If you walk away from this crossing", bare)

    def test_migrates_own_report_ends_with_them_whether_the_merge_committed_or_stopped(self) -> None:
        offered = Replay(Path("."), Path("."), "orders", 2, "1.5.1", "0" * 40, True)
        for conflicts in ((), ("README.md",)):
            done = Migration(offered, "1.5.1", conflicts, "crossed from installed 1.5.1; 3 files",
                             put_back=tuple(SAID))
            self.assertEqual(migrate.report(done).splitlines()[-len(SAID):], SAID, conflicts)
        quiet = Migration(offered, "1.5.1", (), "crossed from installed 1.5.1; 3 files")
        self.assertNotIn("put each back", migrate.report(quiet))


class FollowedTest(unittest.TestCase):
    """The commands, run as written, leave the files where version 1's cruise reads them."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        for name in RUN_FILES:
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(f"what version 1 wrote to {name}\n", encoding="utf-8")

    def test_each_file_the_crossing_moved_goes_back_by_the_line_it_printed(self) -> None:
        moved, left = run_folder.move_version_1(self.root)
        self.assertEqual((len(moved), left), (2, []))
        self.assertFalse((self.root / RUN_FILES[0]).exists())
        commands = [line.strip() for line in run_folder.walking_away(RUN_FILES, []) if line.startswith("  mv ")]
        self.assertEqual(len(commands), 2)
        for command in commands:
            _, source, target = shlex.split(command)
            shutil.move(self.root / source, self.root / target)
        for name in RUN_FILES:
            self.assertEqual((self.root / name).read_text(encoding="utf-8"), f"what version 1 wrote to {name}\n")
        self.assertEqual(list((self.root / run_folder.V1).iterdir()), [])

    def test_the_deck_logs_a_crossing_seeds_are_named_in_one_order_and_are_the_files_it_wrote(self) -> None:
        from slipwai.migration_crossing import seed
        (self.root / ".gitignore").write_text(".slipwai/run/\n", encoding="utf-8")
        seed(self.root, flight())
        names = seeded(self.root, flight())
        self.assertEqual(names, DECKS)
        for name in names:
            self.assertTrue((self.root / name).is_file(), name)
        self.assertEqual(seeded(self.root, Flight()), [])


if __name__ == "__main__":
    unittest.main()
