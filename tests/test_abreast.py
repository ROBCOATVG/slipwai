"""How `boilers` is shared between fairways, how wide one fairway may run, and where the slice graph is read.

The fleet ran a fairway's ready slices one at a time while a person typing `/sail` had them fanned out —
twenty-two slices behind a walking skeleton, one after another. Running them abreast spends `boilers`
differently: it counts slice sessions now, not captains, and one rule shares them out — breadth first,
then depth by priority, `abreast` the cap, a pending merge holding its fairway, nothing preempted. These
cases hold that rule as a function; `test_captain_abreast.py` holds the captain that obeys it.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

import checkout_packages  # noqa: F401

from slipwai import telegraph
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"


def carried(root: Path) -> ModuleType:
    """`abreast.py` and what it imports, loaded from a project at `root` — the toolkit's own scripts
    resolve the project from where they sit, so they are copied there rather than imported in place."""
    place = root / "scripts/agents"
    place.mkdir(parents=True, exist_ok=True)
    for name in ("abreast.py", "clearance.py", "logs.py"):
        shutil.copy(AGENTS / name, place / name)
    (root / "project.json").write_text("{}", encoding="utf-8")
    for name in ("abreast", "clearance", "logs"):
        sys.modules.pop(name, None)
    sys.path.insert(0, str(place))
    try:
        spec = importlib.util.spec_from_file_location("abreast", place / "abreast.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(place))


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.abreast = carried(self.root)

    def share(self, wants: dict[str, int], boilers: int | None, cap: int = 3, running: dict[str, int] | None = None,
              preferred: list[str] | None = None, held: set[str] | None = None,
              weight: dict[str, int] | None = None) -> dict[str, int]:
        planned = self.abreast.allocate(list(wants), preferred or [], wants, running or {}, held or set(),
                                        weight or {}, boilers, cap)
        return {fairway: count for fairway, (count, _) in planned.items()}


class AllocateTest(Fixture):
    def test_breadth_before_depth_across_two_fairways(self) -> None:
        """A stream with nothing running is worth more than a second slice of one that has one."""
        self.assertEqual(self.share({"ORD": 3, "BIL": 3}, boilers=2), {"ORD": 1, "BIL": 1})

    def test_depth_goes_to_the_higher_priority_fairway(self) -> None:
        self.assertEqual(self.share({"ORD": 3, "BIL": 3}, boilers=4, preferred=["BIL"]), {"ORD": 1, "BIL": 3})

    def test_with_no_preference_the_critical_path_decides_then_the_most_ready(self) -> None:
        self.assertEqual(self.share({"ORD": 3, "BIL": 3}, boilers=3, weight={"BIL": 5}), {"ORD": 1, "BIL": 2})
        self.assertEqual(self.share({"ORD": 2, "BIL": 5}, boilers=3), {"ORD": 1, "BIL": 2})

    def test_a_fairway_waiting_on_a_merge_answer_is_given_nothing_more(self) -> None:
        shared = self.share({"ORD": 3, "BIL": 3}, boilers=5, running={"ORD": 1}, held={"ORD"})
        self.assertEqual(shared, {"ORD": 1, "BIL": 3})

    def test_abreast_caps_depth(self) -> None:
        self.assertEqual(self.share({"ORD": 9}, boilers=8, cap=3), {"ORD": 3})

    def test_a_running_session_is_never_taken_back(self) -> None:
        """The telegraph rung down mid-run gives the smaller number at the next boundaries, not a killed stage."""
        self.assertEqual(self.share({"ORD": 3, "BIL": 3}, boilers=2, running={"ORD": 3}), {"ORD": 3, "BIL": 0})

    def test_the_fairway_given_nothing_names_where_its_slot_went(self) -> None:
        planned = self.abreast.allocate(["ORD", "BIL"], [], {"ORD": 1, "BIL": 1}, {}, set(), {}, 1, 3)
        self.assertEqual(planned, {"ORD": (1, ""), "BIL": (0, "ORD")})

    def test_new_sessions_never_take_the_total_past_boilers(self) -> None:
        for boilers, a, b, ra, rb in itertools.product(range(0, 6), range(0, 5), range(0, 5), range(0, 3), range(0, 3)):
            shared = self.share({"ORD": a, "BIL": b}, boilers=boilers, running={"ORD": ra, "BIL": rb})
            with self.subTest(boilers=boilers, wants=(a, b), running=(ra, rb)):
                self.assertLessEqual(sum(shared.values()), max(boilers, ra + rb))
                self.assertGreaterEqual(shared["ORD"], ra)
                self.assertGreaterEqual(shared["BIL"], rb)

    def test_abreast_one_or_one_boiler_per_fairway_is_the_fleet_as_it_was(self) -> None:
        self.assertEqual(self.share({"ORD": 3, "BIL": 3}, boilers=5, cap=1), {"ORD": 1, "BIL": 1})
        self.assertEqual(self.share({"ORD": 3, "BIL": 3}, boilers=2, cap=3), {"ORD": 1, "BIL": 1})


class WidthTest(Fixture):
    def test_the_default_is_three_and_boilers_bounds_it(self) -> None:
        self.assertEqual(self.abreast.width({}), 3)
        self.assertEqual(self.abreast.width({"boilers": 2}), 2)
        self.assertEqual(self.abreast.width({"abreast": 5, "boilers": 4}), 4)
        self.assertEqual(self.abreast.width({"abreast": 1, "boilers": 5}), 1)
        self.assertEqual(self.abreast.width({"boilers": 0}), 3)  # `stop` lights no captain; it does not narrow one

    def test_the_telegraph_sets_it_and_refuses_zero(self) -> None:
        self.assertEqual(telegraph.parse_setting("abreast=2"), ("abreast", 2))
        with self.assertRaises(telegraph.Refused):
            telegraph.parse_setting("abreast=0")
        self.assertNotIn("abreast", telegraph.settings("half-ahead"))  # a shape, not a pace: no position rings it


class SliceGraphTest(Fixture):
    """Read where *Ready-set selection* says the graph is, and nowhere else."""

    def chart(self) -> dict:
        return {"feature": "f", "slices": {name: {"fairway": "LVR"} for name in ("L01", "L02", "L03", "L04")}}

    def split(self, rows: str) -> None:
        path = self.root / "specs/f/story-split.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("## Slice graph\n\n| Slice | depends_on | parallel_ok_with | Notes |\n|---|---|---|---|\n"
                        + rows + "\n## Parking Lot\n", encoding="utf-8")

    def test_a_run_of_slices_and_each_other(self) -> None:
        self.split("| L01 | — | — | skeleton |\n| L02–L04 (all others) | L01 | each other | |\n")
        depends, parallel = self.abreast.clearance.slice_graph(self.chart())
        self.assertEqual(depends, {"L01": [], "L02": ["L01"], "L03": ["L01"], "L04": ["L01"]})
        self.assertEqual(parallel["L03"], {"L02", "L04"})
        self.assertEqual(parallel["L01"], set())
        self.assertTrue(self.abreast.clearance.independent(parallel, "L02", "L04"))
        self.assertFalse(self.abreast.clearance.independent(parallel, "L01", "L02"))

    def test_the_model_s_depends_on_wins_for_a_slice_it_lists(self) -> None:
        self.split("| L02 | — | L03 | |\n")
        model = self.root / "docs/event-model/model.yaml"
        model.parent.mkdir(parents=True)
        model.write_text("slices:\n  - id: L02\n    depends_on: [L01]\n", encoding="utf-8")
        depends, parallel = self.abreast.clearance.slice_graph(self.chart())
        self.assertEqual(depends["L02"], ["L01"])
        self.assertEqual(parallel["L02"], {"L03"})
        self.assertIsNone(parallel.get("L04"))  # undeclared: the page's own independence rule answers

    def test_a_split_with_no_graph_is_no_dependency_and_no_restriction(self) -> None:
        self.assertEqual(self.abreast.clearance.slice_graph(self.chart()), ({}, {}))


class PlanTest(Fixture):
    """The harbourmaster's pass, from the files it reads: the chart, the deck logs and `harbour.json`."""

    def setUp(self) -> None:
        super().setUp()
        chart = self.root / "specs/f/chart.yaml"
        chart.parent.mkdir(parents=True)
        chart.write_text("feature: f\nfairways: {ORD: {}, BIL: {}}\nslices:\n"
                         + "".join(f"  {name}: {{fairway: {name[:3]}, sets: [], steers_by: []}}\n"
                                   for name in ("ORD-01", "ORD-02", "ORD-03", "BIL-01", "BIL-02")),
                         encoding="utf-8")
        self.config = self.root / "harbour.json"

    def plan(self, lit: set[str], **held: object) -> dict[str, tuple[int, int, str]]:
        self.config.write_text(json.dumps(held), encoding="utf-8")
        return self.abreast.harbour_plan(lit, self.config)

    def deck(self, fairway: str, *entries: object) -> None:
        path = self.root / ".slipwai/logs/f" / f"{fairway}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())  # type: ignore[attr-defined]

    def test_breadth_then_depth_in_the_chart_s_order(self) -> None:
        self.assertEqual(self.plan(set(), boilers=3), {"ORD": (2, 0, ""), "BIL": (1, 0, "")})

    def test_what_a_live_captain_is_running_holds_its_slots(self) -> None:
        logs = self.abreast.logs
        self.deck("BIL", logs.entry("claimed", fairway="BIL", slice="BIL-01"),
                  logs.entry("claimed", fairway="BIL", slice="BIL-02"))
        self.assertEqual(self.plan({"BIL"}, boilers=3), {"ORD": (1, 0, ""), "BIL": (2, 2, "")})

    def test_a_pending_merge_holds_its_fairway_back(self) -> None:
        logs = self.abreast.logs
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("request", fairway="ORD", id="merge-ORD-01", what="merge", slice="ORD-01", detail="d"))
        self.assertEqual(self.plan({"ORD"}, boilers=5)["ORD"], (1, 1, ""))

    def test_a_fix_owed_to_trunk_is_work_with_nothing_ready(self) -> None:
        logs = self.abreast.logs
        self.deck("BIL", *(logs.entry(kind, fairway="BIL", slice=one, **({"commit": "bad00001"} if kind == "merged"
                                                                          else {}))
                           for one in ("BIL-01", "BIL-02") for kind in ("claimed", "merged")))
        harbour = self.root / ".slipwai/logs/harbour.jsonl"
        harbour.write_text(logs.entry("fix-trunk", harbour=True, fairway="BIL", slice="BIL-02", commit="bad00001",
                                      job="ci").line(), encoding="utf-8")
        self.assertEqual(self.plan(set(), boilers=2)["BIL"][0], 1)


if __name__ == "__main__":
    unittest.main()
