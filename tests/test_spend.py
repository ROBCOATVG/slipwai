"""What the harbour spent is read from the stages' own records, and the board says it.

*Tokens today* summed a `tokens` field on deck-log lines that nothing wrote, so the tile read 0 all day while
lean-coffee-club's three slices worked. Held here: a stage's work tokens are uncached input plus output; a
stage counts on the day it ended, once, wherever its record is found — trunk or a berth; and the board's
bunker reads it.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import fleet, spend


def stage(name: str, started: str, ended: str, host: dict, subagents: dict | None = None) -> dict:
    return {"stage": name, "started": started, "ended": ended,
            "usage": {"source": "claude", "host": host, "subagents": subagents or {}}}


class WorkTest(unittest.TestCase):
    def test_work_is_uncached_input_plus_output_over_host_and_subagents(self) -> None:
        entry = stage("plan", "a", "b", {"m": {"input": 100, "output": 2000, "cache_read": 900_000,
                                               "cache_creation": 50_000}},
                      {"m": {"input": 10, "output": 300}})
        self.assertEqual(spend.work(entry), 2410, "the context re-read every turn is not work")

    def test_an_older_codex_record_has_its_cache_reads_taken_out_of_input(self) -> None:
        entry = {"usage": {"source": "codex", "host": {"m": {"input": 1000, "output": 50, "cache_read": 800}}}}
        self.assertEqual(spend.work(entry), 250)

    def test_a_malformed_record_counts_nothing_and_never_raises(self) -> None:
        for broken in ({}, {"usage": "x"}, {"usage": {"host": {"m": "x"}}},
                       {"usage": {"host": {"m": {"input": True}}}}):
            self.assertEqual(spend.work(broken), 0)


class ProjectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        for argument in ("init -q -b main", "config user.email s@example.com", "config user.name s"):
            subprocess.run(["git", *argument.split()], cwd=self.root, check=True, capture_output=True)

    def record(self, checkout: Path, slice_id: str, stages: list[dict]) -> None:
        folder = checkout / "specs/001-f/slices" / slice_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "benchmark.json").write_text(json.dumps({"feature": "001-f", "slice": slice_id,
                                                           "stages": stages}), encoding="utf-8")

    def test_nothing_recorded_is_none_and_a_quiet_day_is_zero(self) -> None:
        self.assertIsNone(spend.spent(self.root, "2026-11-18"))
        self.record(self.root, "S1", [stage("plan", "2026-11-17T09:00:00Z", "2026-11-17T09:10:00Z",
                                            {"m": {"input": 0, "output": 5000}})])
        self.assertEqual(spend.spent(self.root, "2026-11-18"), 0)
        self.assertEqual(spend.spent(self.root, "2026-11-17"), 5)

    def test_a_berth_counts_and_a_stage_on_trunk_and_in_its_berth_counts_once(self) -> None:
        planned = stage("plan", "2026-11-18T09:00:00Z", "2026-11-18T09:10:00Z", {"m": {"input": 0, "output": 4000}})
        working = stage("implementation", "2026-11-18T10:00:00Z", "2026-11-18T11:00:00Z",
                        {"m": {"input": 1000, "output": 6000}})
        open_one = {"stage": "review", "started": "2026-11-18T11:00:00Z"}
        self.record(self.root, "S1", [planned])
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "trunk"], cwd=self.root, check=True)
        berth = self.root.parent / f"{self.root.name}-S1"
        subprocess.run(["git", "worktree", "add", "-q", "-b", "slice/S1", str(berth)], cwd=self.root, check=True)
        self.addCleanup(shutil.rmtree, berth, True)
        self.record(berth, "S1", [planned, working, open_one])
        self.assertEqual([path.name for path in spend.checkouts(self.root)], [self.root.name, berth.name])
        self.assertEqual(spend.spent(self.root, "2026-11-18"), 11, "4k on trunk and in the berth once, 7k more")

    def test_the_board_s_bunker_reads_the_records(self) -> None:
        self.record(self.root, "S1", [stage("plan", "2026-11-18T09:00:00Z", "2026-11-18T09:10:00Z",
                                            {"m": {"input": 500, "output": 2500}})])
        day = datetime(2026, 11, 18, 12, tzinfo=UTC)
        self.assertEqual(fleet.spent([], day, self.root), 3)
        self.assertIsNone(fleet.spent([], day), "with no project named, only the log is read")


class MadeOfTest(unittest.TestCase):
    """One number is a pace, not a cost: the tile names it, and says what the day was made of."""

    DAY = {"claude-x": {"input": 503, "output": 299_382, "cache_read": 57_104_707, "cache_creation": 2_748_991}}
    PRICES = {"claude-x": {"input": 3, "output": 15, "cache_read": 0.3, "cache_creation": 3.75}}

    def test_an_estimate_needs_a_price_for_every_model_that_ran(self) -> None:
        self.assertEqual(spend.cost(self.DAY, {}), (None, ["claude-x"]))
        estimate, unpriced = spend.cost(self.DAY, self.PRICES)
        self.assertEqual(unpriced, [])
        self.assertAlmostEqual(estimate or 0, 0.0015 + 4.49 + 17.13 + 10.31, places=1)
        both = {**self.DAY, "other": {"input": 1, "output": 1, "cache_read": 0, "cache_creation": 0}}
        self.assertEqual(spend.cost(both, self.PRICES), (None, ["other"]), "a part is never shown as the whole")

    def test_the_tile_says_work_tokens_and_what_they_were_made_of(self) -> None:
        from slipwai.fleet_tab import tokens_tile
        tile = tokens_tile({"bunker": {"today": 405, "allowed": 20000, "models": self.DAY, "cost": None,
                                       "unpriced": ["claude-x"]}})
        self.assertIn("Work tokens today", tile)
        self.assertIn("405k of 20,000k", tile)
        self.assertIn("claude-x: 299k out · 503 in · 57.1M read from cache · 2.7M written to cache", tile)
        self.assertIn("no estimate: harbour.json has no <code>prices</code> for claude-x", tile)
        priced = tokens_tile({"bunker": {"today": 405, "allowed": 20000, "models": self.DAY, "cost": 31.93,
                                         "unpriced": []}})
        self.assertIn("about $31.93 at the prices in harbour.json", priced)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
