"""The log line: the only thing that says what happened, and the rules that keep it trustworthy.

The first attempt's runner was the single source of status and died at iteration two; seventeen of nineteen
iterations afterwards wrote nothing at all, so the checkpoint said "iteration 2" while twenty slices merged.
In MANDA the same shape failed the other way round: `model.yaml` said `planned` for eight slices that were
built and merged, because the field was written at plan time and never reconciled.

Both are state kept somewhere other than where the work happened. A line is written by the thing that did
the work, at the moment it did it, which is what makes the rule the rest of version 2 rests on true: a slice
that wrote no line made no progress.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT as TOOLKIT


class ShapeTest(unittest.TestCase):
    def test_a_line_is_one_json_object_on_one_line(self) -> None:
        """Appended with O_APPEND and one write() per line, so two processes never tear one."""
        written = logs.entry("heartbeat", fairway="ORD").line()
        self.assertTrue(written.endswith("\n"))
        self.assertEqual(written.count("\n"), 1)
        self.assertIsInstance(json.loads(written), dict)

    def test_every_line_carries_the_format_it_was_written_in(self) -> None:
        self.assertEqual(json.loads(logs.entry("heartbeat", fairway="ORD").line())["v"], logs.V)

    def test_a_timestamp_is_utc_to_the_second_so_two_logs_sort_into_one_order(self) -> None:
        written = json.loads(logs.entry("heartbeat", fairway="ORD").line())["t"]
        self.assertRegex(written, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class DeclarationTest(unittest.TestCase):
    def test_the_deck_log_has_the_kinds_the_glossary_names(self) -> None:
        for kind in ("claimed", "mark-set", "demo", "accepted", "merged", "decision", "question",
                     "told", "read", "heartbeat", "stowed", "parked"):
            with self.subTest(kind=kind):
                self.assertIn(kind, logs.DECK_KINDS)

    def test_a_mark_set_line_names_the_slice_that_set_it(self) -> None:
        """It is written at that slice's first stage, and it is what clears a sibling."""
        self.assertEqual(logs.DECK_KINDS["mark-set"], ("fairway", "slice", "mark"))

    def test_acceptance_is_against_a_capability_and_not_a_slice(self) -> None:
        """A person's demo is of a whole chunk of work, which is theme B item 10."""
        self.assertIn("capability", logs.DECK_KINDS["accepted"])
        self.assertNotIn("slice", logs.DECK_KINDS["accepted"])

    def test_a_question_names_its_slice_and_the_id_a_decision_answers_it_by(self) -> None:
        """Per slice, so clearance can say which slice waits on a person; by id, so a reader tells an open
        question from an answered one with no status field — open until a `decision` carries the same id."""
        self.assertEqual(logs.DECK_KINDS["question"], ("fairway", "slice", "id", "what"))
        self.assertIn("id", logs.DECK_KINDS["decision"])

    def test_a_read_carries_the_timestamp_of_what_it_answers(self) -> None:
        """Which is what makes it a receipt rather than an assertion that somebody looked."""
        self.assertEqual(logs.DECK_KINDS["read"], ("fairway", "told"))

    def test_the_harbour_log_holds_only_what_other_fairways_need(self) -> None:
        """Plus the two answers the harbourmaster owes a captain that asked it for something (7.1), and the
        three about trunk, which is harbour-wide rather than any one fairway's (7.10)."""
        self.assertEqual(set(logs.HARBOUR_KINDS),
                         {"mark-set", "flag-hoisted", "flag-struck", "berth-allocated",
                          "fires-banked", "park", "telegraph", "granted", "refused",
                          "trunk-red", "trunk-green", "fix-trunk", "cleared",
                          "merge-taken-over", "slots", "need-met"})

    def test_a_request_is_a_deck_line_and_both_its_answers_are_harbour_lines(self) -> None:
        """A captain holds no credential, so it asks; and a request that was refused and left no line is
        one the captain waits on for ever and nobody can explain afterwards."""
        self.assertIn("request", logs.DECK_KINDS)
        self.assertIn("berth-request", logs.DECK_KINDS)
        self.assertEqual(logs.declared("granted", harbour=True), ("fairway", "request", "what"))
        self.assertEqual(logs.declared("refused", harbour=True), ("fairway", "request", "why"))

    def test_a_kind_one_log_has_and_the_other_has_not_is_refused_by_name(self) -> None:
        with self.assertRaises(logs.Unreadable) as refused:
            logs.declared("heartbeat", harbour=True)
        self.assertIn("not a kind the harbour log has", str(refused.exception))
        self.assertIn("flag-hoisted", str(refused.exception))


class WritingTest(unittest.TestCase):
    def test_a_line_written_short_is_refused_on_the_way_in(self) -> None:
        """A line written short is one some reader weeks later cannot use, and by then nobody knows
        what the missing value was."""
        with self.assertRaises(logs.Unreadable) as refused:
            logs.entry("mark-set", fairway="ORD", slice="ORD-01")
        self.assertIn("has no mark", str(refused.exception))

    def test_extra_fields_are_allowed_because_a_line_may_say_more(self) -> None:
        written = json.loads(logs.entry("heartbeat", fairway="ORD", berth="orca", tokens=412).line())
        self.assertEqual(written["berth"], "orca")
        self.assertEqual(written["tokens"], 412)


class ReadingTest(unittest.TestCase):
    def test_a_line_round_trips(self) -> None:
        written = logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="OrderPlaced").line()
        back = logs.read(written)
        self.assertEqual(back.kind, "mark-set")
        self.assertEqual(back.fields["mark"], "OrderPlaced")

    def test_a_newer_format_is_refused_and_names_what_reads_it(self) -> None:
        """Guessing which fields moved is how a reader reports a run that did not happen."""
        line = json.dumps({"v": logs.V + 1, "t": logs.now(), "kind": "heartbeat", "fairway": "ORD"})
        with self.assertRaises(logs.Unreadable) as refused:
            logs.read(line)
        self.assertIn(f"v{logs.V + 1}", str(refused.exception))
        self.assertIn("slipwai upgrade", str(refused.exception))

    def test_a_line_that_is_not_json_is_refused_rather_than_skipped(self) -> None:
        with self.assertRaises(logs.Unreadable):
            logs.read("claimed ORD-01\n")

    def test_a_fold_stops_at_a_line_it_cannot_read(self) -> None:
        """A board folded from a log with holes is a board that is confidently wrong, which is the whole
        problem the first attempt had."""
        good = logs.entry("heartbeat", fairway="ORD").line()
        with self.assertRaises(logs.Unreadable):
            logs.fold([good, "{not json}", good])

    def test_a_fold_keeps_the_order_the_lines_were_written_in(self) -> None:
        written = [logs.entry("claimed", fairway="ORD", slice=f"ORD-0{n}").line() for n in (1, 2, 3)]
        self.assertEqual([entry.fields["slice"] for entry in logs.fold(written)],
                         ["ORD-01", "ORD-02", "ORD-03"])


class PathTest(unittest.TestCase):
    def test_a_fairway_writes_its_own_file_and_nothing_else(self) -> None:
        """One writer per file is why two fairways never conflict on a log."""
        self.assertEqual(logs.deck_path("ordering", "ORD"), ".slipwai/logs/ordering/ORD.jsonl")

    def test_a_harbour_log_is_one_machine_s_and_is_not_in_a_feature(self) -> None:
        self.assertEqual(logs.harbour_path("harbour_one"), ".slipwai/logs/harbour/harbour_one.jsonl")

    def test_the_one_harbour_log_a_project_already_has_is_still_read(self) -> None:
        """The single-writer file from before there were three writers. Left where it is and folded in with
        the rest, because a migration that moved somebody's log is a migration that can lose one."""
        self.assertEqual(logs.HARBOUR, ".slipwai/logs/harbour.jsonl")

    def test_the_logs_are_under_a_path_git_ignores(self) -> None:
        """Heartbeat and token lines arrive every few seconds and have no place in trunk's history."""
        self.assertTrue(logs.LOGS.startswith(".slipwai/"))


class ClosedTest(unittest.TestCase):
    """A field whose values are a closed set, checked on the way in and on the way out.

    `verdict` is the one, and it is read rather than displayed: the captain retries a slice whose demo came
    back and closes one whose demo was accepted. A free-form verdict makes that a guess about somebody's
    wording, and the three here are the ones `check-decisions.py` already holds the demo log to.
    """

    def test_a_verdict_outside_the_set_is_refused_on_the_way_in(self) -> None:
        with self.assertRaises(logs.Unreadable) as refused:
            logs.entry("demo", fairway="ORD", slice="ORD-01", verdict="looks fine to me")
        self.assertIn("accepted, behaviour, implementation", str(refused.exception))

    def test_a_verdict_outside_the_set_is_refused_on_the_way_out(self) -> None:
        """A log is read by things that did not write it, so the rule has to hold at the reader too."""
        line = json.dumps({"v": logs.V, "t": logs.now(), "kind": "demo", "fairway": "ORD",
                           "slice": "ORD-01", "verdict": "ok"})
        with self.assertRaises(logs.Unreadable):
            logs.read(line)

    def test_every_verdict_in_the_set_is_taken(self) -> None:
        for verdict in logs.VERDICTS:
            with self.subTest(verdict=verdict):
                entry = logs.entry("demo", fairway="ORD", slice="ORD-01", verdict=verdict)
                self.assertEqual(logs.read(entry.line()).fields["verdict"], verdict)

    def test_the_set_is_the_one_the_demo_log_is_already_held_to(self) -> None:
        """Two copies of a vocabulary drift. This one is named in `check-decisions.py`, which holds the
        markdown the hand writes, and the log line has to mean the same thing as the heading above it."""
        source = (TOOLKIT / "scripts/check-decisions.py").read_text(encoding="utf-8")
        found = re.search(r"^VERDICTS = \((.*?)\)$", source, re.M)
        if found is None:
            self.fail("check-decisions.py no longer declares VERDICTS as a literal tuple")
        self.assertEqual(tuple(re.findall(r'"([^"]+)"', found.group(1))), logs.VERDICTS)


class HarbourFoldTest(unittest.TestCase):
    """Three machines write three harbour logs and a reader sees one.

    The harbour log had exactly one writer, which on one machine is unambiguous and on three is not. One
    elected writer needs an election; three writers on one file breaks the rule the whole log design rests
    on. So the file becomes one per machine, folded on read exactly like the deck logs — which costs
    nothing at read time and removes the single writer rather than electing one.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)

    def write(self, where: str, *written: tuple[str, str]) -> None:
        path = self.root / where
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for when, flag in written:
                handle.write(replace(logs.entry("flag-hoisted", harbour=True, flag=flag, where=where),
                                     t=when).line())

    def test_three_machines_fold_into_one_history(self) -> None:
        for machine in ("one", "two", "three"):
            self.write(logs.harbour_path(machine), ("2026-10-12T09:00:00Z", machine))
        self.assertEqual(len(logs.harbour_fold(self.root)), 3)

    def test_the_fold_is_by_instant_and_not_by_machine(self) -> None:
        """Interleaved by time is what makes three files read as one harbour rather than three lists
        stapled together — the same rule `render-fairways.py` folds the decisions by."""
        self.write(logs.harbour_path("two"), ("2026-10-12T09:00:00Z", "second"))
        self.write(logs.harbour_path("one"), ("2026-10-12T09:00:01Z", "third"))
        self.write(logs.harbour_path("three"), ("2026-10-12T08:59:59Z", "first"))
        self.assertEqual([str(e.fields["flag"]) for e in logs.harbour_fold(self.root)],
                         ["first", "second", "third"])

    def test_the_log_a_project_already_had_folds_in_with_them(self) -> None:
        self.write(logs.HARBOUR, ("2026-10-12T08:00:00Z", "from before"))
        self.write(logs.harbour_path("one"), ("2026-10-12T09:00:00Z", "and after"))
        self.assertEqual([str(e.fields["flag"]) for e in logs.harbour_fold(self.root)],
                         ["from before", "and after"])

    def test_a_harbour_log_is_not_a_deck_log(self) -> None:
        """Every reader of the deck logs globs the whole tree, so the directory the harbour logs are in has
        to be excluded by rule rather than by one resolved path — which is what it was when there was one."""
        self.write(logs.harbour_path("one"), ("2026-10-12T09:00:00Z", "a flag"))
        self.write(logs.HARBOUR, ("2026-10-12T09:00:00Z", "an older flag"))
        (self.root / logs.LOGS / "ordering").mkdir(parents=True)
        (self.root / logs.deck_path("ordering", "ORD")).write_text("", encoding="utf-8")
        self.assertEqual([path.stem for path in logs.deck_logs(self.root)], ["ORD"])

    def test_a_machine_with_nothing_to_say_yet_is_not_an_error(self) -> None:
        self.assertEqual(logs.harbour_fold(self.root), [])


class MachineTest(unittest.TestCase):
    """Which machine wrote this. One identity, used by the claim refs, the per-machine harbour log and a
    berth's database name — because three answers to *which machine* is three ways for two of them to
    disagree about whether a collision is one."""

    def setUp(self) -> None:
        self.was = os.environ.get("SLIPWAI_MACHINE")
        self.addCleanup(self.restore)

    def restore(self) -> None:
        if self.was is None:
            os.environ.pop("SLIPWAI_MACHINE", None)
        else:
            os.environ["SLIPWAI_MACHINE"] = self.was

    def test_it_is_derived_and_not_chosen(self) -> None:
        """Nobody picks it, which is the berth rule: a name somebody types is a name somebody retypes."""
        os.environ.pop("SLIPWAI_MACHINE", None)
        self.assertEqual(logs.machine(), logs.machine())
        self.assertTrue(logs.machine())

    def test_it_is_safe_in_a_git_ref_a_filename_and_a_database_name(self) -> None:
        """It is spent in all three places, and the one that would break quietly is the database name:
        `bookings_<machine>_booking` reaching a server with a hyphen in it is a refused connection."""
        for given in ("Lukes-MacBook-Pro.local", "ci runner #3", "  ", "WIN-DESKTOP", "ação"):
            with self.subTest(given=given):
                os.environ["SLIPWAI_MACHINE"] = given
                self.assertRegex(logs.machine(), r"^[a-z][a-z0-9_]*$")
                self.assertLessEqual(len(logs.machine()), logs.MACHINE_WIDTH)

    def test_a_person_may_say_which_machine_this_is(self) -> None:
        """Two containers off one image share a hostname, and a shared database is where that is found
        out. The override is the one place a name is typed, and it is typed once."""
        os.environ["SLIPWAI_MACHINE"] = "harbour-two"
        self.assertEqual(logs.machine(), "harbour_two")

    def test_a_name_with_nothing_usable_in_it_is_still_a_machine(self) -> None:
        """Never the empty string: it is spent as a path component and a ref component, and an empty one
        makes `refs/slipwai/claims//ordering`, which git refuses in a sentence about nothing."""
        os.environ["SLIPWAI_MACHINE"] = "???"
        self.assertRegex(logs.machine(), r"^[a-z][a-z0-9_]*$")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
