"""Two smaller readers of a further feature's slice: the feedback ranking's uncertainty, and `check-try`.

Both took the chart's feature for every slice. The ranking read no decision of a later feature's observable,
and `check-try` found no chart for a later feature's story, so a story giving what its own slice sets passed.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from test_feedback_rank import modules

from slipwai.assets import TOOLKIT_ROOT

FIXTURE = Path(__file__).resolve().parent / "fixtures/recap-try"
CHART = {"feature": "001-first", "slices": {
    "V1": {"fairway": "f", "feature": "002-further", "pattern": "state-view", "sets": [], "steers_by": ["Made"]},
    "V2": {"fairway": "f", "pattern": "state-view", "sets": [], "steers_by": ["Made"]}}}
DECIDED = ("# Decisions\n\n## D{n} — Which total is shown?\n- **Stage:** plan · **Slice:** {piece} · "
           "**When:** 2026-11-20T09:00:00Z\n- **Decision:** the net\n- **Confidence:** low\n"
           "- **Decided by:** host (stage recommendation)\n")


class UncertaintyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        for feature, number, piece in (("001-first", 2, "V2"), ("002-further", 5, "V1")):
            (self.root / "specs" / feature).mkdir(parents=True)
            (self.root / "specs" / feature / "decisions.md").write_text(DECIDED.format(n=number, piece=piece),
                                                                        encoding="utf-8")
        _, self.feedback = modules(self.root)

    def test_a_further_feature_s_observable_is_scored_on_its_own_feature_s_decisions(self) -> None:
        score, sources = self.feedback.uncertainty("001-first", CHART, "V1")
        self.assertGreater(score, 0)
        self.assertTrue(sources[0].startswith("D5 (low, host)"), sources)

    def test_an_observable_of_the_chart_s_feature_is_scored_as_it_was(self) -> None:
        _, sources = self.feedback.uncertainty("001-first", CHART, "V2")
        self.assertTrue(sources[0].startswith("D2 (low, host)"), sources)


class CheckTryTest(unittest.TestCase):
    def test_a_further_feature_s_story_is_held_to_what_the_one_chart_says_its_slice_sets(self) -> None:
        root = Path(tempfile.mkdtemp()) / "recap"
        self.addCleanup(shutil.rmtree, root.parent, True)
        shutil.copytree(FIXTURE, root)
        (root / "scripts/agents").mkdir(parents=True)
        shutil.copy(TOOLKIT_ROOT / "scripts/check-try.py", root / "scripts/check-try.py")
        for name in ("try_it.py", "logs.py"):
            shutil.copy(TOOLKIT_ROOT / "scripts/agents" / name, root / "scripts/agents" / name)
        place = root / "specs/002-further/slices/CU5"
        place.mkdir(parents=True)
        (place / "try-it.json").write_text(json.dumps(
            {"as": "noor", "steps": [{"method": "GET", "path": "/api/books/cs-1/recap"}],
             "given": [{"stream": "x", "event": "RecapGenerated", "data": {}}]}), encoding="utf-8")
        done = subprocess.run([sys.executable, "-B", "scripts/check-try.py"], cwd=root, capture_output=True,
                              text=True, check=False)
        self.assertIn("002-further/CU5: given 1 is a RecapGenerated, which this slice itself sets", done.stderr)


if __name__ == "__main__":
    unittest.main()
