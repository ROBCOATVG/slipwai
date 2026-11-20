"""Lines a session wrote to a file of its stream's name under a further feature are still the stream's.

Until a session was told where its stream's log is, one working a further feature's slice wrote under that
feature. Those lines are read with the stream's own — a question there is answered by a decision in the
stream's log — and they travel, on a ref of their own, without the stream's ref ever being rewritten.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401
import harbourmaster_fixture
from test_travel import Fixture as TwoMachines
from test_travel import claims, line, travel

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"


class DecisionsTest(harbourmaster_fixture.Fixture):
    def test_a_question_in_a_further_feature_s_file_is_answered_by_the_stream_s_decision(self) -> None:
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text("slices: {}\n", encoding="utf-8")
        self.deck("later", "ORD", logs.entry("question", fairway="ORD", slice="ORD-01", id="Q1", what="?",
                                             t="2026-11-20T08:15:00Z"))
        self.deck("ordering", "ORD",
                  logs.entry("parked", fairway="ORD", slice="ORD-01", why="one question", t="2026-11-20T08:16:00Z"),
                  logs.entry("decision", fairway="ORD", id="Q1", what="D3: a", t="2026-11-20T08:20:00Z",
                             decided_by="sail-decide-skipper"))
        self.run_once()
        self.assertEqual([(str(e.fields["parked"]), str(e.fields["what"])) for e in self.harbour()
                          if e.kind == "cleared"], [("2026-11-20T08:16:00Z", "answered by decisions Q1")])


class TravelTest(TwoMachines):
    def setUp(self) -> None:
        super().setUp()
        for where in (self.one, self.two):
            (where / "specs/model").mkdir(parents=True)
            (where / "specs/model/chart.yaml").write_text("slices: {}\n", encoding="utf-8")
        self.here = logs.machine()

    def stray(self, root: Path, *lines: str) -> Path:
        path = root / ".slipwai/logs/later/ordering.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.writelines(lines)
        return path

    def test_two_files_of_one_stream_travel_on_two_refs_and_both_land(self) -> None:
        own = self.deck(self.one, "ordering", line("heartbeat", "2026-11-20T09:00:00Z", fairway="ordering"))
        stray = self.stray(self.one, line("mark-set", "2026-11-20T09:01:00Z", fairway="ordering", slice="S45",
                                          mark="Made"))
        claims.take(self.one, "ordering", self.here)
        went, refused = travel.depart(self.one)
        self.assertEqual(refused, [])
        self.assertEqual([ref for ref in went if "harbour" not in ref],
                         [travel.deck_ref("ordering"), travel.deck_ref("ordering", "later")])
        self.assertEqual(sorted(travel.arrive(self.two)),
                         [".slipwai/logs/later/ordering.jsonl", ".slipwai/logs/model/ordering.jsonl"])
        self.assertEqual((self.two / ".slipwai/logs/later/ordering.jsonl").read_text(encoding="utf-8"),
                         stray.read_text(encoding="utf-8"))
        self.assertEqual((self.two / ".slipwai/logs/model/ordering.jsonl").read_text(encoding="utf-8"),
                         own.read_text(encoding="utf-8"))

    def test_a_ref_that_already_carries_one_file_is_never_handed_to_the_other(self) -> None:
        stray = self.stray(self.one, line("mark-set", "2026-11-20T09:01:00Z", fairway="ordering", slice="S45",
                                          mark="Made"))
        claims.take(self.one, "ordering", self.here)
        travel.depart(self.one)
        self.assertEqual(travel.carried(self.one, travel.deck_ref("ordering")),
                         (".slipwai/logs/later/ordering.jsonl", stray.read_text(encoding="utf-8")))
        own = self.deck(self.one, "ordering", line("heartbeat", "2026-11-20T09:02:00Z", fairway="ordering"))
        went, refused = travel.depart(self.one)
        self.assertEqual(refused, [])
        self.assertIn(travel.deck_ref("ordering", "model"), went)
        self.assertEqual(travel.carried(self.one, travel.deck_ref("ordering")),
                         (".slipwai/logs/later/ordering.jsonl", stray.read_text(encoding="utf-8")),
                         "a log ref only ever appends")
        self.assertEqual(travel.held(self.one, travel.deck_ref("ordering", "model")), own.read_text(encoding="utf-8"))

    def test_a_stream_with_one_file_travels_on_its_own_ref_as_it_did(self) -> None:
        self.deck(self.one, "ordering", line("heartbeat", "2026-11-20T09:00:00Z", fairway="ordering"))
        claims.take(self.one, "ordering", self.here)
        went, refused = travel.depart(self.one)
        self.assertEqual((refused, [ref for ref in went if "harbour" not in ref]), ([], [travel.deck_ref("ordering")]))


def try_it_in(root: Path) -> Any:
    """`try_it.py` as it is inside a project: loaded from there, since it reads everything from where it is."""
    place = root / "scripts/agents"
    place.mkdir(parents=True)
    for name in ("try_it.py", "logs.py", "clearance.py"):
        shutil.copy(AGENTS / name, place / name)
    (root / "project.json").write_text("{}", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("try_it_strays", place / "try_it.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SeededTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.try_it = try_it_in(self.root)
        (self.root / "specs/001-first").mkdir(parents=True)
        (self.root / "specs/001-first/chart.yaml").write_text(
            "slices:\n  S45: {fairway: intake, feature: 002-further, sets: [], steers_by: []}\n", encoding="utf-8")

    def seeded(self, **told: str) -> list[logs.Entry]:
        clean = {key: value for key, value in os.environ.items() if not key.startswith("SLIPWAI_")}
        with mock.patch.dict(os.environ, {**clean, **told}, clear=True):
            said = self.try_it.write_seeded("002-further/S45", 2, 0, "")
        self.assertIn("the line is in .slipwai/logs/001-first/intake.jsonl", said)
        self.assertFalse(logs.deck_path(self.root, "002-further", "intake").exists())
        return logs.fold(logs.deck_path(self.root, "001-first", "intake").read_text(encoding="utf-8").splitlines())

    def test_run_by_hand_the_line_goes_to_the_stream_the_chart_names_under_the_chart_s_feature(self) -> None:
        found = self.seeded()
        self.assertEqual([(e.kind, e.fields["fairway"], e.fields["story"]) for e in found],
                         [("seeded", "intake", "specs/002-further/slices/S45/try-it.json")])

    def test_dispatched_the_line_goes_where_the_captain_said_the_log_is(self) -> None:
        found = self.seeded(SLIPWAI_FAIRWAY="intake", SLIPWAI_DECK=".slipwai/logs/001-first/intake.jsonl")
        self.assertEqual([e.kind for e in found], ["seeded"])


if __name__ == "__main__":
    unittest.main()
