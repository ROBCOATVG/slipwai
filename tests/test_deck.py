"""One stream's log, as a person reads it.

The board answers *is anything stuck*, and the moment the answer is yes the next question is always the
same one: what has this stream actually been doing? The board cannot answer it — the answer is forty lines
of one file and the board is one row.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.deck import entries, feature_of, recent, said, streams


class SaidTest(unittest.TestCase):
    """A line is said, not printed: `set OrderPlaced`, not `{"kind": "mark-set", "mark": …}`."""

    def test_the_lines_a_captain_writes_each_read_as_a_sentence(self) -> None:
        for entry, expected in (
            (logs.entry("claimed", fairway="ORD", slice="ORD-01"), "claimed ORD-01"),
            (logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"), "set Placed"),
            (logs.entry("demo", fairway="ORD", slice="ORD-01", verdict="accepted"), "accepted"),
            (logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc123def"), "merged ORD-01"),
            (logs.entry("parked", fairway="ORD", why="the gate stayed red"), "the gate stayed red"),
            (logs.entry("told", fairway="ORD", message="look at this"), "a person said: look at this"),
        ):
            with self.subTest(kind=entry.kind):
                self.assertIn(expected, said(entry))

    def test_a_heartbeat_says_what_it_has_spent_where_it_says_anything(self) -> None:
        self.assertIn("42k", said(logs.entry("heartbeat", fairway="ORD", tokens=42)))
        self.assertEqual(said(logs.entry("heartbeat", fairway="ORD")), "still going")

    def test_a_commit_is_shortened_because_nobody_reads_forty_characters(self) -> None:
        line = said(logs.entry("merged", fairway="ORD", slice="ORD-01", commit="a" * 40))
        self.assertIn("a" * 8, line)
        self.assertNotIn("a" * 9, line)

    def test_a_kind_it_has_no_sentence_for_is_shown_rather_than_skipped(self) -> None:
        """The log grows. A reader meeting an unfamiliar line should see that there was one."""
        entry = logs.Entry(kind="invented", fields={"fairway": "ORD", "thing": "value"})
        found = said(entry)
        self.assertIn("invented", found)
        self.assertIn("thing=value", found)

    def test_every_kind_a_deck_log_has_says_something_other_than_its_own_name(self) -> None:
        """A sentence that is just the kind again is the raw line with extra steps."""
        for kind, fields in logs.DECK_KINDS.items():
            with self.subTest(kind=kind):
                # A field with a closed set gets one of its values: a placeholder is refused on the way in,
                # which is the point of `logs.CLOSED` and not a thing to work around here.
                allowed = logs.CLOSED.get(kind, {})
                said_fields: dict[str, object] = {
                    name: (allowed[name][0] if name in allowed else f"<{name}>") for name in fields}
                entry = logs.entry(kind, False, **said_fields)
                self.assertNotEqual(said(entry).strip(), kind)


class ReadingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def deck(self, fairway: str, *written: logs.Entry, feature: str = "ordering") -> Path:
        path = logs.deck_path(self.root, feature, fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in written:
                handle.write(entry.line())
        return path

    def test_every_stream_with_a_log_is_found_and_the_harbour_is_not_one(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD"))
        self.deck("BIL", logs.entry("heartbeat", fairway="BIL"), feature="billing")
        (logs.older_harbour(self.root)).write_text("", encoding="utf-8")
        self.assertEqual(sorted(name for _, name in streams(self.root)), ["BIL", "ORD"])

    def test_a_stream_knows_which_feature_it_is_under(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD"))
        self.assertEqual(feature_of(self.root, "ORD"), "ordering")
        self.assertEqual(feature_of(self.root, "nothing"), "")

    def test_a_stream_with_no_log_is_said_rather_than_empty(self) -> None:
        found, fault = entries(self.root, "nothing")
        self.assertEqual(found, [])
        self.assertIn("no log here", fault)

    def test_a_log_that_goes_bad_part_way_keeps_what_came_before_it(self) -> None:
        """A log that breaks at line 90 has 89 lines somebody still wants, and the whole reason for
        looking at one stream is that something has gone wrong with it."""
        path = self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        with path.open("a", encoding="utf-8") as handle:
            handle.write("not json\n")
        found, fault = entries(self.root, "ORD")
        self.assertEqual(len(found), 1)
        self.assertIn("line 2", fault)

    def test_the_last_lines_are_the_ones_shown(self) -> None:
        self.deck("ORD", *(logs.entry("claimed", fairway="ORD", slice=f"ORD-{n:02}") for n in range(20)))
        found, _ = recent(self.root, "ORD", limit=5)
        self.assertEqual(len(found), 5)
        self.assertIn("ORD-19", found[-1][1])

    def test_each_line_carries_when_it_happened(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        when, _ = recent(self.root, "ORD")[0][0]
        self.assertRegex(when, r"^\d{4}-\d{2}-\d{2}T")


if __name__ == "__main__":
    unittest.main()
