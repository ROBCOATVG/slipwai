"""A stream has one log, under the chart's feature, and one row on the board, whatever files hold its lines.

A session working a further feature's slice took the stream's log to be under that feature, so a stream had
a second file of its name. The board drew the file as a second stream — "intake | 002-further | not started"
— and read neither file's lines beside the other's.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import deck, fleet, logs
from slipwai.slice_rungs import slice_home

FIRST, FURTHER, THIRD = "001-first", "002-further", "003-third"


class OneLogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "specs" / FIRST).mkdir(parents=True)
        (self.root / "specs" / FIRST / "chart.yaml").write_text("slices: {}\n", encoding="utf-8")

    def write(self, feature: str, fairway: str, *entries: logs.Entry) -> Path:
        path = logs.deck_path(self.root, feature, fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.writelines(entry.line() for entry in entries)
        return path

    def two_files(self) -> None:
        self.write(FURTHER, "intake", logs.entry("question", fairway="intake", slice="S45", id="Q1",
                                                 what="which?", t="2026-11-20T09:05:00Z"))
        self.write(THIRD, "intake", logs.entry("mark-set", fairway="intake", slice="S60", mark="Made",
                                               t="2026-11-20T09:07:00Z"))
        self.write(FIRST, "intake",
                   logs.entry("claimed", fairway="intake", slice="S45", t="2026-11-20T09:00:00Z"),
                   logs.entry("decision", fairway="intake", id="Q1", what="D7: that one", t="2026-11-20T09:10:00Z"))

    def test_the_chart_feature_s_file_is_the_stream_s_log_and_the_rest_follow_it(self) -> None:
        self.two_files()
        self.assertEqual([path.parent.name for path in logs.streams(self.root)["intake"]], [FIRST, FURTHER, THIRD])
        self.assertEqual(deck.feature_of(self.root, "intake"), FIRST, "which is where the board writes")
        self.assertEqual(deck.streams(self.root), [(FIRST, "intake")])

    def test_the_board_has_one_row_a_stream_with_every_file_s_lines_in_the_order_written(self) -> None:
        self.two_files()
        found, faults = fleet.fairways(self.root, [])
        self.assertEqual(faults, {})
        self.assertEqual([(one.name, one.feature) for one in found], [("intake", FIRST)])
        self.assertEqual([e.kind for e in found[0].entries], ["claimed", "question", "mark-set", "decision"])
        self.assertEqual(found[0].claimed, ["S45"])
        self.assertEqual([e.kind for e in deck.entries(self.root, "intake")[0]],
                         ["claimed", "question", "mark-set", "decision"])

    def test_a_stream_with_one_file_is_read_exactly_as_it_is(self) -> None:
        path = self.write(FIRST, "intake",
                          logs.entry("merged", fairway="intake", slice="S1", commit="c0ffee", t="2026-11-20T09:10:00Z"),
                          logs.entry("claimed", fairway="intake", slice="S2", t="2026-11-20T09:00:00Z"))
        self.assertEqual(logs.stream_lines([path]), path.read_text(encoding="utf-8").splitlines())
        found, _ = fleet.fairways(self.root, [])
        self.assertEqual([e.kind for e in found[0].entries], ["merged", "claimed"], "file order, never re-sorted")

    def test_with_no_chart_a_stream_is_under_the_feature_its_file_is(self) -> None:
        (self.root / "specs" / FIRST / "chart.yaml").unlink()
        self.write(FURTHER, "intake", logs.entry("claimed", fairway="intake", slice="S1"))
        self.assertEqual(deck.feature_of(self.root, "intake"), FURTHER)

    def test_the_card_takes_the_feature_the_chart_row_names_before_it_searches(self) -> None:
        (self.root / "specs" / FURTHER / "slices" / "S45").mkdir(parents=True)
        self.assertEqual(slice_home(self.root, FIRST, "S45", THIRD), THIRD)
        self.assertEqual(slice_home(self.root, FIRST, "S45"), FURTHER, "an older project's answer names none")


if __name__ == "__main__":
    unittest.main()
