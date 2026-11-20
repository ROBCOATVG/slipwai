"""A further feature's slice, as its captain reads it: its files are under its own feature.

One chart, under the first feature, and a later feature's slices are rows on it naming theirs. The captain
took the chart's feature for every slice, so a later feature's stage record and story were looked for where
they are not: a hand-over closed nothing it could see and cost an attempt, and a story was never owed its seed.
"""
from __future__ import annotations

import json
import unittest

import checkout_packages  # noqa: F401
from captain_fixture import CHART, WORKS, Fixture

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


if __name__ == "__main__":
    unittest.main()
