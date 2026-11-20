"""A slice's card reads the slice's files where its feature keeps them, not where the chart is written.

One chart per project, under the first feature, and a further feature's slices on it: their example maps,
plans and stage records are under their own feature, so a card that looked under the chart's sat on its
first rung — `Examples` — while the slice planned, built and was reviewed.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import slice_rungs
from slipwai.slice_rungs import slice_home, stage_now

FIRST, FURTHER = "001-first", "002-further"


class SliceHomeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()) / "project"
        (self.root / "specs" / FIRST / "slices" / "S1").mkdir(parents=True)
        (self.root / "specs" / FURTHER).mkdir(parents=True)
        slice_rungs.HOMES.clear()
        self.addCleanup(slice_rungs.HOMES.clear)

    def test_a_slice_under_the_chart_s_feature_is_read_there_as_it_always_was(self) -> None:
        self.assertEqual(slice_home(self.root, FIRST, "S1"), FIRST)

    def test_a_further_feature_s_slice_is_read_under_its_own_feature_in_its_berth(self) -> None:
        berth = self.root.parent / "project-S45" / "specs" / FURTHER / "slices" / "S45"
        berth.mkdir(parents=True)
        (berth / "benchmark.json").write_text(json.dumps({"stages": [{"stage": "implement", "started": "now"}]}),
                                              encoding="utf-8")
        home = slice_home(self.root, FIRST, "S45")
        self.assertEqual(home, FURTHER)
        self.assertEqual(stage_now(self.root, FIRST, "S45"), ("", ""), "which is what the card was reading")
        self.assertNotEqual(stage_now(self.root, home, "S45"), ("", ""), "and the stage it has open is read now")

    def test_a_slice_with_no_files_anywhere_yet_is_asked_about_under_the_chart_s_feature(self) -> None:
        self.assertEqual(slice_home(self.root, FIRST, "S99"), FIRST)


if __name__ == "__main__":
    unittest.main()
