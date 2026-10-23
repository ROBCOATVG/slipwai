"""Clearance for a view or an automation is any-of, and a mark its story gives is not waited on — slice 20.6.

Against recap's chart as `make chart` now renders it, with each slice's `pattern`: LB12 *See the library*
steered by fifteen marks and sat at row 17 of 34; PR1 *Start preparation* read `BookImported` *or*
`AudioFetched` and the captain read it as *and*, and exited four times with *nothing to start*.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/recap-try"
FEATURE = "001-audiobook-recap"


def clearance_at(root: Path) -> Any:
    path = ROOT / "assets/toolkit/scripts/agents/clearance.py"
    spec = importlib.util.spec_from_file_location("clearance_fold", path)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    module.ROOT, module.SPECS = root, root / "specs"
    module.LOGS, module.HARBOUR_LOGS = root / ".slipwai/logs", root / ".slipwai/logs/harbour"
    return module


class FoldTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()) / "recap"
        shutil.copytree(FIXTURE, self.root)
        self.module = clearance_at(self.root)
        self.charted, feature = self.module.chart()
        self.assertEqual(feature, FEATURE)
        self.settled = self.module.marks_set(FEATURE)

    def story(self, slice_id: str, given: list[str]) -> None:
        place = self.root / f"specs/{FEATURE}/slices/{slice_id}"
        place.mkdir(parents=True, exist_ok=True)
        (place / "try-it.json").write_text(json.dumps(
            {"as": "ada", "given": [{"stream": "s", "event": event, "data": {}} for event in given],
             "steps": [{"method": "GET", "path": "/api/x"}]}), encoding="utf-8")

    def test_the_chart_carries_each_slice_s_pattern(self) -> None:
        self.assertEqual(self.charted["slices"]["LB12"]["pattern"], "state-view")
        self.assertEqual(self.charted["slices"]["PR1"]["pattern"], "automation")
        self.assertEqual(self.charted["slices"]["LB9"]["pattern"], "translation")
        self.assertEqual(self.charted["slices"]["LB12"]["actor"], "Listener")

    def test_lb12_is_cleared_on_the_marks_the_21st_set_and_the_sentence_says_what_it_folds(self) -> None:
        self.assertIn("BookImported", self.settled)
        self.assertIs(self.module.cleared(self.charted, self.settled, "LB12"), True)
        found = self.module.lines(FEATURE)
        folded = self.module.folded(found)
        state, why = self.module.position(self.charted, folded, "LB12")
        self.assertEqual(state, "implementation-ready", why)
        # Every one of the fifteen was set on the 21st and 22nd — the siblings planned — and LB12 still sat at
        # row 17: clearance was never what held it, which is what 20.7's ranking is for.
        self.assertIn("a state-view folding 15 marks: 15 set", why)
        self.assertIn("unset and folded once they exist",
                      self.module.fold_note(self.charted, {"BookImported"}, "LB12"))

    def test_pr1_is_cleared_on_book_imported_alone(self) -> None:
        self.assertIs(self.module.cleared(self.charted, {"BookImported"}, "PR1"), True)
        self.assertIs(self.module.cleared(self.charted, {"AudioFetched"}, "PR1"), True)
        why = self.module.cleared(self.charted, set(), "PR1")
        self.assertIsInstance(why, str)
        self.assertIn("PR1 is an automation steering by", why)
        self.assertIn("gives none of them", why)

    def test_cu5_is_cleared_when_its_story_gives_every_unset_mark_and_not_before(self) -> None:
        marks = self.module.steered_by(self.charted, "CU5")
        self.assertEqual(len(marks), 10)
        self.assertIsInstance(self.module.cleared(self.charted, set(), "CU5"), str)
        self.story("CU5", ["ChapterTranscribed", "ChapterIndexed"])
        self.module.CHECKOUTS.clear()
        why = self.module.cleared(self.charted, set(), "CU5")
        self.assertIsInstance(why, str)
        self.assertIn("its story gives ChapterIndexed and ChapterTranscribed", why)
        self.story("CU5", marks)
        self.assertIs(self.module.cleared(self.charted, set(), "CU5"), True)
        self.assertIn("10 given by its story", self.module.fold_note(self.charted, set(), "CU5"))

    def test_a_translation_and_a_state_change_still_wait_for_every_mark(self) -> None:
        charted = {"feature": FEATURE, "slices": {
            "T1": {"fairway": "library", "pattern": "translation", "sets": [], "steers_by": ["A", "B"]},
            "S1": {"fairway": "library", "pattern": "state-change", "sets": ["C"], "steers_by": ["A", "B"]},
            "A1": {"fairway": "library", "sets": ["A"], "steers_by": []},
            "B1": {"fairway": "library", "sets": ["B"], "steers_by": []}}}
        self.assertIsInstance(self.module.cleared(charted, {"A"}, "T1"), str)
        self.assertIsInstance(self.module.cleared(charted, {"A"}, "S1"), str)
        self.assertIs(self.module.cleared(charted, {"A", "B"}, "T1"), True)

    def test_the_order_says_which_rows_fold(self) -> None:
        reasons = dict(self.module.order_reasons(self.charted))
        self.assertIn("a state-view folding 15: cleared when one is set or its story gives the rest", reasons["LB12"])
        self.assertIn("an automation folding 2", reasons["PR1"])
        self.assertTrue(reasons["LB3"].startswith("steers by nothing"))


if __name__ == "__main__":
    unittest.main()
