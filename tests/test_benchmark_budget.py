"""`scripts/agents/benchmark.py` as a gate on the loop's cadence and its budgets, not only a record of cost.

The script ships inside a generated project and is loaded here by path, the way `clearance.py` is in
`test_observed_slices.py`: it has no slipwai to import and this module has no project to run it in, so what
is held is the pure part — what the record says about a slice, read from the record alone.
"""
from __future__ import annotations

import importlib.util
import unittest

from slipwai.assets import TOOLKIT_ROOT


def load():
    spec = importlib.util.spec_from_file_location("benchmark_under_test", TOOLKIT_ROOT / "scripts/agents/benchmark.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(*stages: str) -> dict:
    return {"slice": "S1", "stages": [
        {"stage": stage, "started": "2026-10-14T10:00:00Z", "ended": "2026-10-14T10:05:00Z"} for stage in stages]}


class ReviewCadenceTest(unittest.TestCase):
    """The rung reads the whole diff once and allows one earlier reading of a pinned story; a third `review`
    bracket is a return that was sent to a reviewer instead of being spot-checked."""

    def setUp(self) -> None:
        self.benchmark = load()

    def test_two_reviews_are_the_rung_s_own(self) -> None:
        self.assertEqual(self.benchmark.over_reviewed(record("implement", "review", "implement", "review")), 0)

    def test_a_third_is_counted(self) -> None:
        self.assertEqual(self.benchmark.over_reviewed(record("review", "review", "review", "review")), 2)

    def test_the_old_spelling_of_the_stage_counts_too(self) -> None:
        """`review-mate` is the stage's name since the rename; a record written under either spelling is one record."""
        self.assertEqual(self.benchmark.over_reviewed(record("review-mate", "review", "review-mate")), 1)

    def test_the_bound_is_the_two_readings_the_rung_names(self) -> None:
        self.assertEqual(self.benchmark.REVIEWS, 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
