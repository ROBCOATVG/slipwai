"""`clearance.py --feedback`: the observables ranked by what delaying a person's judgement costs — slice 20.7.

The ranking is written down once here against recap's second day and held: the fixture's numbers are the
first guesses the plan's open point 4 says will be argued with, and a change to a weight is a change to this
file, said out loud.
"""
from __future__ import annotations

import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/recap-try"
FEATURE = "001-audiobook-recap"


def modules(root: Path) -> tuple[Any, Any]:
    sys.path.insert(0, str(ROOT / "assets/toolkit/scripts/agents"))
    for name in ("clearance", "feedback"):
        sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location("clearance", ROOT / "assets/toolkit/scripts/agents/clearance.py")
    assert spec is not None and spec.loader is not None
    clearance: Any = importlib.util.module_from_spec(spec)
    sys.modules["clearance"] = clearance
    spec.loader.exec_module(clearance)
    clearance.ROOT, clearance.SPECS = root, root / "specs"
    clearance.LOGS, clearance.HARBOUR_LOGS = root / ".slipwai/logs", root / ".slipwai/logs/harbour"
    spec = importlib.util.spec_from_file_location("feedback", ROOT / "assets/toolkit/scripts/agents/feedback.py")
    assert spec is not None and spec.loader is not None
    feedback: Any = importlib.util.module_from_spec(spec)
    sys.modules["feedback"] = feedback
    spec.loader.exec_module(feedback)
    return clearance, feedback


class RankTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()) / "recap"
        shutil.copytree(FIXTURE, self.root)
        self.clearance, self.feedback = modules(self.root)
        self.charted, _ = self.clearance.chart()
        found = self.clearance.lines(FEATURE)
        self.folded = self.clearance.with_evidence(self.charted, self.clearance.folded(found))
        self.settled = self.folded.marks | self.clearance.already_set(self.charted)
        self.rows = self.feedback.rank(FEATURE, self.charted, self.folded, self.settled)
        self.by = {row["slice"]: row for row in self.rows}

    def test_the_observables_are_the_views_the_automations_and_no_inbound_translation(self) -> None:
        named = self.feedback.observables(self.charted)
        self.assertIn("LB12", named)
        self.assertIn("CU5", named)
        self.assertNotIn("LB9", named, "an inbound sync faces no actor")
        self.assertNotIn("LB3", named, "a state-change is seen through its readers")
        self.assertEqual(self.feedback.seen_through(self.charted, "LB3"), "PR1")
        self.assertEqual(self.feedback.seen_through(self.charted, "CU15"), "")

    def test_the_day_s_ranking_as_written_down_once(self) -> None:
        order = [row["slice"] for row in self.rows if not row["merged"]]
        self.assertEqual(order[:4], ["CU5", "PR2", "CU11", "LB12"])
        self.assertEqual([row["slice"] for row in self.rows if row["merged"]], ["LB5", "PR1"],
                         "surfaced observables come last, with no score")
        self.assertEqual(self.by["CU5"]["score"], 252.0)
        self.assertEqual(self.by["LB12"]["score"], 84.0)

    def test_lb12_names_its_decisions_and_the_unmerged_slices_that_steer_by_its_marks(self) -> None:
        row = self.by["LB12"]
        self.assertEqual([one.split(" ")[0] for one in row["uncertainty"]["sources"]], ["D10", "D11", "D23", "D38"])
        self.assertEqual(row["blast_radius"]["score"], 11)
        self.assertIn("CU5", row["blast_radius"]["slices"])
        self.assertEqual(row["cost_to_surface"]["parts"], ["LB12 itself", "a screen to style (1)"])
        self.assertTrue(any("claimed" in point for point in row["urgency"]["points"]))

    def test_cu5_s_decisions_are_the_most_at_medium_confidence_and_it_is_one_slice_from_a_person(self) -> None:
        row = self.by["CU5"]
        self.assertEqual(row["uncertainty"]["score"], 6.0)
        self.assertEqual(row["cost_to_surface"]["parts"], ["CU5 itself"])
        self.assertEqual(row["blast_radius"]["score"], 13)

    def test_a_term_read_from_nothing_says_so_rather_than_printing_zero_silently(self) -> None:
        self.assertEqual(self.by["CU9"]["uncertainty"], {"score": 0, "sources": []})
        with redirect_stdout(io.StringIO()) as out:
            self.feedback.say(FEATURE, self.rows, self.charted, self.folded)
        said = out.getvalue()
        self.assertIn("CU9", said)
        self.assertIn("uncertainty 0 — read from nothing", said)
        self.assertIn("weights {", said)

    def test_a_human_s_decision_counts_nothing(self) -> None:
        entry = {"Decided by": "human", "Confidence": "low"}
        self.assertEqual(self.feedback.weight_of(entry), 0)
        host = {"Decided by": "host (stage recommendation)", "Confidence": "medium"}
        self.assertEqual(self.feedback.weight_of(host), 2)
        self.assertEqual(self.feedback.weight_of({"Decided by": "host", "Status": "overridden by D31"}), 0)

    def test_the_order_names_what_each_row_is_seen_through_and_its_score(self) -> None:
        with redirect_stdout(io.StringIO()) as out:
            self.clearance.main(["--order"])
        said = out.getvalue()
        self.assertIn("steers by nothing; sets BookImported, which 9 slices steers by; first of prepare-a-book; "
                      "seen through PR1", said)
        self.assertIn("seen through LB5", said)
        self.assertIn("SpoilerReported, which nothing steers by; first of report-a-spoiler; seen through nothing — no "
                      "observable reads what it sets", said)
        self.assertIn("feedback score 84", said)
        self.assertNotIn("add nothing a person can judge", said,
                         "on the 22nd every row above the views had merged; nothing could still go first")

    def test_before_the_voyage_the_order_says_where_an_observable_sits_below_rows_that_add_nothing(self) -> None:
        """Day one, nothing merged and nothing set: LB12 at row 17 sits under twelve writes nothing reads."""
        empty = self.clearance.Folded()
        rows = self.feedback.rank(FEATURE, self.charted, empty, set())
        with redirect_stdout(io.StringIO()) as out:
            self.clearance.say_order(self.charted, FEATURE, rows, empty)
        said = out.getvalue()
        self.assertIn("feedback: LB12 scores", said)
        self.assertIn("at row 17; 9 unmerged rows above it", said)
        self.assertIn("add nothing a person can judge before it", said)

    def test_the_json_query_carries_the_next_three_feedback_points(self) -> None:
        with redirect_stdout(io.StringIO()) as out:
            self.clearance.main(["--json", "--feature", FEATURE])
        answer = json.loads(out.getvalue())
        self.assertEqual([row["slice"] for row in answer["feedback"]], ["CU5", "PR2", "CU11"])


if __name__ == "__main__":
    unittest.main()
