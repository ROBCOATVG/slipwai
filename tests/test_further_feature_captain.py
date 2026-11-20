"""A further feature's slice, as its captain reads it: its files are under its own feature.

One chart, under the first feature, and a later feature's slices are rows on it naming theirs. The captain
took the chart's feature for every slice, so a later feature's stage record and story were looked for where
they are not: a hand-over closed nothing it could see and cost an attempt, and a story was never owed its seed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

import checkout_packages  # noqa: F401
from captain_fixture import CHART, WORKS, Fixture

from slipwai import logs

#: The fixture's chart with ORD-01 a row of a later feature; every other row is the chart's own.
FURTHER = CHART.replace("  ORD-01:\n", "  ORD-01:\n    feature: later\n", 1)
#: A `/sail` that ends its first run at a hand-over — one stage closed in the slice's own folder and no
#: line — and closes the gate on its second.
HANDS_OVER = """import sys, json, pathlib
record = pathlib.Path("specs/FEATURE/slices") / sys.argv[1] / "benchmark.json"
if not record.is_file():
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"stages": [{"stage": "tasks", "started": "a", "ended": "b"}]}))
    sys.exit(0)
""" + WORKS


class FurtherFeatureTest(Fixture):
    def further(self) -> None:
        (self.root / "specs/ordering/chart.yaml").write_text(FURTHER, encoding="utf-8")

    def dispatched(self) -> list[str]:
        return [str(e.fields.get("free", "")) for e in self.read("ORD") if e.kind == "dispatched"]

    def test_a_hand_over_recorded_under_the_slice_s_own_feature_costs_no_attempt(self) -> None:
        self.further()
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(HANDS_OVER.replace("FEATURE", "later")))
        self.assertEqual(self.dispatched()[:2], ["it ended at a handover", ""], done.stdout + done.stderr)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "parked"], [], done.stdout)

    def test_a_slice_of_the_chart_s_own_feature_hands_over_as_it_did(self) -> None:
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(HANDS_OVER.replace("FEATURE", "ordering")))
        self.assertEqual(self.dispatched()[:2], ["it ended at a handover", ""], done.stdout + done.stderr)

    def test_a_story_under_the_slice_s_own_feature_is_owed_its_seed(self) -> None:
        self.further()
        place = self.root / "specs/later/slices/ORD-01"
        place.mkdir(parents=True)
        (place / "try-it.json").write_text(json.dumps({"as": "ada", "steps": [{"method": "GET", "path": "/x"}]}),
                                           encoding="utf-8")
        done = self.captain("ORD", self.sail(WORKS))
        parks = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parks), 1, done.stdout + done.stderr)
        self.assertIn("no `seeded` line", str(parks[0].fields["why"]))
        self.assertIn("specs/later/slices/ORD-01/try-it.json", parks[0].fields["needs"][0]["what"])

    def test_the_session_is_told_the_stream_s_one_log_whichever_feature_its_slice_is_of(self) -> None:
        self.further()
        done = self.captain("ORD", self.sail(
            "import os, pathlib\npathlib.Path('told.txt').write_text(os.environ.get('SLIPWAI_DECK', ''))\n"))
        self.assertEqual((self.root / "told.txt").read_text(encoding="utf-8"), ".slipwai/logs/ordering/ORD.jsonl",
                         done.stdout + done.stderr)

    def stray(self, *entries: logs.Entry) -> None:
        path = logs.deck_path(self.root, "later", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(entry.line() for entry in entries), encoding="utf-8")

    def test_a_question_a_session_wrote_under_its_slice_s_feature_is_asked_all_the_same(self) -> None:
        self.further()
        self.stray(logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="which carrier?"))
        done = self.captain("ORD", self.sail("import sys\nsys.exit(0)\n"))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1, done.stdout + done.stderr)
        self.assertIn("ORD-01 is awaiting a decision — Q1: which carrier?", parked[0])

    def test_and_a_decision_in_the_stream_s_log_answers_it(self) -> None:
        self.further()
        self.stray(logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="which carrier?"))
        self.deck("ORD", logs.entry("decision", fairway="ORD", id="Q1", what="D4: the cheap one"))
        self.captain("ORD", self.sail("import sys\nsys.exit(0)\n"))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertNotIn("awaiting a decision", parked[0])

    def test_a_word_to_the_stream_goes_to_its_one_log(self) -> None:
        self.stray(logs.entry("mark-set", fairway="ORD", slice="ORD-01", mark="Placed"))
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        done = subprocess.run([sys.executable, "scripts/agents/fleet.py", "tell", "ORD", "carry", "on"],
                              cwd=self.root, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual([e.kind for e in self.read("ORD")], ["claimed", "told"])


if __name__ == "__main__":
    unittest.main()
