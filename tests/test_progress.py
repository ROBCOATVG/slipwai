"""The plan's ticks are the history's, not a person's.

A plan that records its own progress by hand is wrong by Friday, and a plan that overstates it is worse
than one that says nothing. `scripts/progress.py` writes the Status column from `git log`; this holds the
committed plan to what the script would write, and holds the script to the one rule that matters — a
slice is ticked when a commit says it landed, and not when a commit merely mentions it.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "scripts/progress.py"

_spec = importlib.util.spec_from_file_location("progress_script", SCRIPT)
assert _spec is not None and _spec.loader is not None
progress = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(progress)


class TickTest(unittest.TestCase):
    def test_the_committed_plan_is_what_the_history_would_write(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = progress.main(["--check"])
        self.assertEqual(code, 0, out.getvalue())

    def test_a_stale_total_is_not_what_the_gate_is_for(self) -> None:
        """A captain's branch computes a different total from trunk's, and that must not be a red gate.

        Found by running five fairways at once: each captain lands a slice, each branch's `**Progress:`
        line counts that one slice and no other's, and `--check` compared the whole page — so every
        captain was red on a line none of them was allowed to own. The ticks are the fact the plan is
        read for; the totals are rendered, like the drawio canvas the host regenerates after a merge.
        """
        page = progress.rendered()
        stale = page.replace(
            next(line for line in page.splitlines() if line.startswith("**Progress:")),
            "**Progress: 1 of 999 slices done** — phase 1 0/6. Written by `scripts/progress.py`.")
        self.assertNotEqual(stale, page, "the fixture did not change the line it meant to")
        self.assertEqual(progress.without_the_total(stale), progress.without_the_total(page))

    def test_a_tick_that_is_actually_wrong_is_still_caught(self) -> None:
        """The relaxation is the totals and only the totals: a Status cell still answers to the history."""
        page = progress.rendered()
        untick = page.replace("| done |\n", "|  |\n", 1)
        self.assertNotEqual(untick, page, "the fixture did not untick anything")
        self.assertNotEqual(progress.without_the_total(untick), progress.without_the_total(page))

    def test_writing_twice_changes_nothing_the_second_time(self) -> None:
        """The Status cell is rewritten, not appended, or the table grows a column per run."""
        once = progress.rendered()
        done = progress.shipped()
        self.assertEqual(progress.ticked(once, done), progress.ticked(progress.ticked(once, done), done))

    def test_every_separator_is_as_wide_as_its_header(self) -> None:
        """The first attempt stripped a real column off the separator, because `---` is what every cell of
        one holds and there is no telling this script's from the table's."""
        header = None
        for line in progress.rendered().splitlines():
            if line.startswith("| Slice |"):
                header = line.count("|")
            elif header and set(line) <= set("|-") and line.startswith("|"):
                self.assertEqual(line.count("|"), header, line)
                header = None

    def test_both_table_shapes_are_handled(self) -> None:
        """Phases 1 to 8 have a `From` column and phase 9 has not; both get one Status column."""
        widths = {line.count("|") for line in progress.rendered().splitlines() if line.startswith("| Slice |")}
        self.assertEqual(widths, {6, 7})

    def test_a_subject_that_mentions_a_slice_does_not_tick_it(self) -> None:
        """The commit that added slice 9.5 to the plan was written `Slice 9.5: …` and the first version of
        this script marked 9.5 done. Only the trailer counts now."""
        self.assertIsNone(progress.TRAILER.search("Slice 9.5: the three contributor skills\n\nbody\n"))
        self.assertEqual(progress.TRAILER.findall("did a thing\n\nSlice-done: 9.5\n"), ["9.5"])

    def counted(self, page: str) -> dict[str, str]:
        """Every row the script would tick: a trailer in the history, or one of the two derived cases."""
        ids = [m.group(1) for line in page.splitlines() if (m := progress.ROW.match(line))]
        return progress.with_headings(progress.shipped(), ids, page)

    def test_nothing_is_ticked_that_the_history_has_not_got(self) -> None:
        page = progress.rendered()
        done = self.counted(page)
        for line in page.splitlines():
            if (match := progress.ROW.match(line)) and line.rstrip().endswith("|"):
                ticked = line.rsplit("|", 2)[1].strip() == "done"
                with self.subTest(slice=match.group(1)):
                    self.assertEqual(ticked, match.group(1) in done)

    def test_every_derived_tick_is_derived_from_a_trailer_and_not_from_nothing(self) -> None:
        """The two rules add rows the history did not name. Each must still rest on a trailer that is
        in it — a derived tick that rested on another derived tick would be a tick resting on nothing."""
        page = progress.rendered()
        shipped = progress.shipped()
        for row, short in self.counted(page).items():
            with self.subTest(slice=row):
                self.assertIn(short, shipped.values())

    def test_a_heading_is_done_when_every_row_under_it_is_and_not_before(self) -> None:
        """`3.3`'s work is done by `3.3a` to `3.3h`; nothing will ever carry its trailer."""
        self.assertEqual(progress.headings(["3.3", "3.3a", "3.3b", "4.1"]), {"3.3": ["3.3a", "3.3b"]})
        whole = progress.with_headings({"3.3a": "aaa", "3.3b": "bbb"}, ["3.3", "3.3a", "3.3b"])
        self.assertIn("3.3", whole)
        self.assertNotIn("3.3", progress.with_headings({"3.3a": "aaa"}, ["3.3", "3.3a", "3.3b"]))

    def test_a_row_whose_work_moved_is_done_when_the_row_it_moved_to_is(self) -> None:
        page = "| 2.5 | *Moved to phase 3 as 3.9 — see below.* | | |  |\n"
        self.assertEqual(progress.moved(page), {"2.5": "3.9"})
        self.assertIn("2.5", progress.with_headings({"3.9": "ccc"}, ["2.5", "3.9"], page))
        self.assertNotIn("2.5", progress.with_headings({}, ["2.5", "3.9"], page))

    def test_a_tick_survives_the_commit_that_writes_it_being_amended(self) -> None:
        """The cell said `done <hash>` once, and folding the tick into the slice's own commit changed the
        hash it had just recorded, so the gate went red on the commit that made it green."""
        page = progress.rendered()
        self.assertNotRegex(page, r"\| done [0-9a-f]{7,} \|")
        # Not "a tick exists": whether one does depends on the history this checkout has, and a shallow
        # clone has none. What must hold is that a tick, where written, is the stable form.
        # Also catches a slice shipped with no row: its trailer counts and nothing ticks it, which is
        # work the plan cannot show anybody. `6.4b` was exactly that until this said so.
        self.assertEqual(page.count("| done |"), len(self.counted(page)),
                         "every shipped slice needs a row in the plan to be ticked in")

    def test_the_slices_that_predate_the_trailer_are_a_closed_list(self) -> None:
        """It was written once and is never added to; everything after carries its own trailer."""
        self.assertEqual(len(progress.BEFORE_THE_TRAILER), 8)

    def test_the_summary_counts_what_the_tables_hold(self) -> None:
        page = progress.rendered()
        rows = sum(1 for line in page.splitlines() if progress.ROW.match(line))
        self.assertIn(f"of {rows} slices done", page)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
