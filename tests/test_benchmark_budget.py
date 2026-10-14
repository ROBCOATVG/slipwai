"""`scripts/agents/benchmark.py` as a gate on the loop's cadence and its budgets, not only a record of cost.

The script ships inside a generated project and is loaded here by path, the way `clearance.py` is in
`test_observed_slices.py`: it has no slipwai to import and this module has no project to run it in, so what
is held is the pure part — what the record says about a slice, read from the record alone.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

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


def entry(source: str, seconds: int = 60, counts: str | None = None, **tokens: int) -> dict:
    usage = {"source": source, "host": {"m": {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0, **tokens}},
             "subagents": {}}
    if counts:
        usage["counts"] = counts
    return {"stage": "implement", "started": "2026-10-14T10:00:00Z", "ended": "2026-10-14T10:01:00Z",
            "seconds": seconds, "usage": usage}


class WorkTokensTest(unittest.TestCase):
    """`input` means uncached input whichever harness wrote the record: Codex counts its cache reads inside
    `input_tokens` and Claude Code does not, and a sum over both used to count a Codex token twice."""

    def setUp(self) -> None:
        self.benchmark = load()

    def test_a_codex_read_is_normalised_to_uncached_input(self) -> None:
        normalised = self.benchmark.uncached({"m": {"input": 15_443_061, "output": 69_109, "cache_read": 15_298_560,
                                                    "cache_creation": 0}})
        self.assertEqual(normalised["m"]["input"], 144_501)
        self.assertEqual(normalised["m"]["cache_read"], 15_298_560)

    def test_a_legacy_codex_record_is_read_as_if_it_had_been(self) -> None:
        legacy = entry("codex", input=15_443_061, output=69_109, cache_read=15_298_560)
        self.assertEqual(self.benchmark.totals(legacy)["input"], 144_501)
        self.assertEqual(self.benchmark.work(legacy), 144_501 + 69_109)

    def test_a_normalised_codex_record_is_not_subtracted_twice(self) -> None:
        fresh = entry("codex", counts="uncached", input=144_501, output=69_109, cache_read=15_298_560)
        self.assertEqual(self.benchmark.totals(fresh)["input"], 144_501)

    def test_a_claude_record_is_already_uncached(self) -> None:
        claude = entry("claude", input=120_000, output=9_000, cache_read=3_000_000)
        self.assertEqual(self.benchmark.totals(claude)["input"], 120_000)
        self.assertEqual(self.benchmark.work(claude), 129_000)

    def test_the_summary_line_says_the_work_beside_the_input(self) -> None:
        self.assertIn("work 129k", self.benchmark.summary_line(entry("claude", input=120_000, output=9_000)))


class BudgetTest(unittest.TestCase):
    """The budget is read at every bracket: `start` prints what is left, `end` says over budget."""

    def setUp(self) -> None:
        self.benchmark = load()
        self.config = Path(tempfile.mkdtemp()) / "harbour.json"
        self.config.write_text(json.dumps({"stage_scale": 1.0, "bunker_per_slice": 1000, "stages": {
            "default": {"minutes": 30, "tokens": 400}, "implement-shipwright": {"minutes": 90, "tokens": 1200}}}),
            encoding="utf-8")

    def test_a_stage_is_read_under_the_name_the_table_has(self) -> None:
        budget = self.benchmark.budget_for("implement", self.config)
        self.assertEqual((budget["minutes"], budget["tokens"], budget["bunker"]), (90, 1_200_000, 1_000_000))
        self.assertEqual(self.benchmark.budget_for("review", self.config)["minutes"], 30)

    def test_the_telegraph_scales_every_stage(self) -> None:
        held = json.loads(self.config.read_text(encoding="utf-8"))
        held["stage_scale"] = 0.5
        self.config.write_text(json.dumps(held), encoding="utf-8")
        budget = self.benchmark.budget_for("implement", self.config)
        self.assertEqual((budget["minutes"], budget["tokens"]), (45, 600_000))

    def test_no_harbour_means_no_budget_and_says_so(self) -> None:
        self.assertIsNone(self.benchmark.budget_for("implement", self.config.with_name("none.json")))
        self.assertIn("none", self.benchmark.budget_line("implement", None, {"seconds": 0, "work": 0}))

    def test_over_budget_names_the_number_that_was_passed(self) -> None:
        budget = self.benchmark.budget_for("implement", self.config)
        long_ = entry("claude", seconds=81 * 60 + 12, input=140_000, output=69_000)
        self.assertEqual(self.benchmark.over_budget(long_, budget), {})
        late = entry("claude", seconds=91 * 60, input=140_000, output=69_000)
        self.assertEqual(list(self.benchmark.over_budget(late, budget)), ["minutes"])
        heavy = entry("claude", seconds=60, input=1_300_000, output=69_000)
        self.assertEqual(self.benchmark.over_budget(heavy, budget)["tokens"], [1_369_000, 1_200_000])
        self.assertIn("1.4M of 1.2M work tokens",
                      self.benchmark.over_budget_line("implement", {"tokens": [1_369_000, 1_200_000]}))

    def test_the_context_re_read_is_not_the_work(self) -> None:
        """The SB1 record: 19.67M input of which 19.43M cached, against a 1.2M budget. Read as work it is
        well inside the token budget and over the wall budget — which is the one that measured the stage."""
        budget = self.benchmark.budget_for("implement", self.config)
        sb1 = entry("codex", seconds=81 * 60 + 12, input=19_670_084, output=81_837, cache_read=19_427_072)
        self.assertEqual(self.benchmark.over_budget(sb1, budget), {})

    def test_the_start_line_says_what_the_slice_has_spent(self) -> None:
        budget = self.benchmark.budget_for("implement", self.config)
        used = self.benchmark.spent({"stages": [entry("claude", seconds=723, input=300_000, output=40_000),
                                                entry("claude", seconds=0, input=999, output=999)]})
        self.assertEqual(used, {"seconds": 723, "work": 340_000})
        line_ = self.benchmark.budget_line("implement", budget, used)
        self.assertIn("implement-shipwright 90m / 1.2M work tokens", line_)
        self.assertIn("spent 12m03s / 340k work tokens of its 1M bunker", line_)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
