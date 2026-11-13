"""A slice's chip says what the slice is doing now.

Three ways it did not, all from one afternoon of game-club-manager. Every task count went `0/13` to `13/13`
in one step, because the session ticks `tasks.md` a batch at a time while the branch takes a commit a minute
naming its task. TB1 said `Merging` for three hours after the harbour refused its request on a red trunk. And
AC2 said `Implementing · 13/13` while it mended a gate refusal, as TB1's stage stood open through its demo.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs, slice_rungs
from slipwai.logs import Entry
from slipwai.slice_rungs import rung

FEATURE = "001-demo"
FOLDER = f"specs/{FEATURE}/slices/S01"
LONG_AGO, LATER, FAR_AHEAD = "2020-01-01T00:00:00Z", "2020-01-01T00:05:00Z", "2099-01-01T00:00:00Z"


def line(kind: str, at: str, harbour: bool = False, **fields: object) -> Entry:
    made = logs.entry(kind, harbour=harbour, **fields)
    return Entry(kind=made.kind, t=at, fields=made.fields)


def ask(at: str, name: str = "S01-merge-1") -> Entry:
    return line("request", at, fairway="F", slice="S01", id=name, what="merge", detail="merge it")


def refused(at: str, why: str, name: str = "S01-merge-1") -> Entry:
    return line("refused", at, harbour=True, fairway="F", request=name, why=why)


class Slice(unittest.TestCase):
    """One slice branch with a task list of four, none ticked, and the session back on `main`."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()) / "project"
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root.parent, True)
        self.addCleanup(slice_rungs.SEEN.clear)
        self.git("init", "-q", "-b", "main")
        self.commit("scaffold", "README.md", "x\n")
        self.git("checkout", "-q", "-b", "slice/S01")
        self.commit("S01 tasks T001-T004", f"{FOLDER}/tasks.md",
                    "- [ ] T001 one\n- [ ] T002 two\n- [ ] T003 three\n- [ ] T004 four\n")

    def git(self, *argv: str) -> None:
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv], cwd=self.root, check=True,
                       capture_output=True)

    def commit(self, subject: str, name: str = "work.txt", text: str = "") -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text or subject, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject)

    def chip(self, entries: list[Entry] | None = None, harbour: list[Entry] | None = None) -> str:
        return rung(self.root, FEATURE, "S01", entries or [], harbour or [])["chip"]

    def stages(self, *stages: dict[str, str]) -> None:
        record = self.root.parent / "project-S01" / FOLDER / "benchmark.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"stages": list(stages)}), encoding="utf-8")


class TaskCountTest(Slice):
    def test_a_task_is_counted_from_the_commit_that_names_it(self) -> None:
        self.assertEqual(self.chip(), "Implementing · 0/4", "the commit that wrote the list names them all")
        self.commit("S01 T001: one")
        self.assertEqual(self.chip(), "Implementing · 1/4")
        self.commit("S01: T002–T003 two and three")
        self.assertEqual(self.chip(), "Implementing · 3/4")

    def test_a_task_both_ticked_and_named_is_one_task(self) -> None:
        self.commit("S01 T001: one")
        self.commit("S01: T001 ticked", f"{FOLDER}/tasks.md",
                    "- [x] T001 one\n- [ ] T002 two\n- [ ] T003 three\n- [ ] T004 four\n")
        self.assertEqual(self.chip(), "Implementing · 1/4")

    def test_another_slice_s_commit_and_a_task_not_on_the_list_count_for_nothing(self) -> None:
        self.commit("S02 T002: a sibling's, merged in from trunk")
        self.commit("S01 T009: not on this list")
        self.assertEqual(self.chip(), "Implementing · 0/4")

    def test_a_list_done_with_no_stage_open_is_not_being_implemented(self) -> None:
        self.commit("S01: T001-T004 done")
        self.assertEqual(self.chip(), "Tasks done · 4/4")


class MergeTest(Slice):
    def test_a_request_the_harbour_has_not_answered_is_requested_and_a_granted_one_is_merging(self) -> None:
        self.assertEqual(self.chip([ask(FAR_AHEAD)]), "Merge requested")
        granted = line("granted", FAR_AHEAD, harbour=True, fairway="F", request="S01-merge-1", what="merge")
        self.assertEqual(self.chip([ask(FAR_AHEAD)], [granted]), "Merging")

    def test_an_answer_to_an_earlier_request_of_the_same_name_is_not_this_one_s(self) -> None:
        self.assertEqual(self.chip([ask(FAR_AHEAD)], [refused(LONG_AGO, "conflicts")]), "Merge requested")

    def test_a_refusal_says_so_and_the_card_says_why(self) -> None:
        found = rung(self.root, FEATURE, "S01", [ask(FAR_AHEAD)], [refused(FAR_AHEAD, "slice/S01 conflicts")])
        self.assertEqual((found["chip"], found["refused"], found["rank"]),
                         ("Merge refused", "slice/S01 conflicts", "8"))

    def test_a_refusal_on_a_red_trunk_is_held_while_the_trunk_is_red(self) -> None:
        red = line("trunk-red", FAR_AHEAD, harbour=True, commit="abc", job="gate", why="failed")
        no = refused(FAR_AHEAD, "trunk is red, and nothing merges onto a red trunk.")
        self.assertEqual(self.chip([ask(FAR_AHEAD)], [red, no]), "Held · trunk red")
        green = line("trunk-green", FAR_AHEAD, harbour=True, commit="abd")
        self.assertEqual(self.chip([ask(FAR_AHEAD)], [red, no, green]), "Merge refused")

    def test_a_slice_that_has_committed_since_its_refusal_is_back_at_work(self) -> None:
        """TB1: refused at 12:37, at work until 15:47, and `Merging` on the board throughout."""
        found = rung(self.root, FEATURE, "S01", [ask(LONG_AGO)], [refused(LATER, "trunk is red")])
        self.assertEqual((found["chip"], found["rank"]), ("Implementing · 0/4", "8"),
                         "the captain still ranks it by the furthest it reached")

    def test_asking_again_after_the_fix_is_a_request_again(self) -> None:
        asked = [ask(LONG_AGO), ask(FAR_AHEAD, "S01-merge-2")]
        self.assertEqual(self.chip(asked, [refused(LATER, "conflicts")]), "Merge requested")


class StageTest(Slice):
    def test_a_stage_left_open_is_not_believed_past_a_later_line(self) -> None:
        """TB1's `implement-shipwright` stood open through its demo and a gate park."""
        self.stages({"stage": "implement-shipwright", "started": LONG_AGO})
        self.assertEqual(self.chip(), "Implementing · 0/4")
        demo = line("demo", LATER, fairway="F", slice="S01", verdict="accepted")
        self.assertEqual(self.chip([demo]), "Demo")

    def test_a_gate_refusal_newer_than_anything_reached_is_what_the_slice_is_mending(self) -> None:
        """AC2 said `Implementing · 13/13` while it found out why its turn had set no mark."""
        park = line("parked", LATER, fairway="F", why="S01: this turn wrote no `mark-set`", cause="gate")
        self.assertEqual(self.chip([park]), "Fixing gate refusal")
        self.stages({"stage": "implement", "started": FAR_AHEAD})
        self.assertEqual(self.chip([park]), "Implementing · 0/4", "a stage opened since is the newer word")
        self.stages()
        mark = line("mark-set", FAR_AHEAD, fairway="F", slice="S01", mark="M1")
        self.assertEqual(self.chip([park, mark]), "Implementing · 0/4", "mended")

    def test_a_sibling_s_gate_refusal_is_not_this_slice_s(self) -> None:
        park = line("parked", LATER, fairway="F", why="S02: this turn wrote no `mark-set`", cause="gate")
        self.assertEqual(self.chip([park]), "Implementing · 0/4")

    def test_implementing_after_the_review_is_the_review_s_fixes(self) -> None:
        self.commit("S01 review: findings recorded", f"{FOLDER}/review.md", "# review\n")
        self.assertEqual(self.chip(), "Review")
        self.stages({"stage": "implement-shipwright", "started": FAR_AHEAD})
        self.assertEqual(self.chip(), "Review fixes")


if __name__ == "__main__":
    unittest.main()
