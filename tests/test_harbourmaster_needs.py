"""The receipts the harbourmaster writes by itself: a pause whose time has come, a need trunk now meets.

Split from `test_harbourmaster.py` at its budget. Both are the fleet-status plan's: on the recap voyage a
session limit's reset came and went with nobody to lift the parks, and three slices waited on one change to
trunk written as three paragraphs.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from harbourmaster_fixture import Fixture, MergeFixture

from slipwai import logs


class PausedTest(Fixture):
    """A park with a time on it is cleared when the time comes, by the one process that watches the clock.

    recap, 2026-10-21: the limit reset at 21:40 and eight parks stood until 09:00 the next day.
    """

    def test_a_pause_whose_time_has_come_is_cleared_once_with_the_time_as_the_answer(self) -> None:
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", slice="ORD-01", why="refused",
                                                cause="limit", until="2026-10-21T20:40:00Z",
                                                t="2026-10-21T16:40:00Z"))
        for _ in range(2):
            done = self.run_once()
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        receipts = [entry.fields for entry in self.harbour() if entry.kind == "cleared"]
        self.assertEqual(receipts, [{"fairway": "ORD", "parked": "2026-10-21T16:40:00Z",
                                     "what": "its time came: 2026-10-21T20:40:00Z"}])

    def test_a_pause_whose_time_is_ahead_stands(self) -> None:
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", slice="ORD-01", why="refused",
                                                cause="limit", until="2999-01-01T00:00:00Z",
                                                t="2026-10-21T16:40:00Z"))
        self.run_once()
        self.assertEqual([entry for entry in self.harbour() if entry.kind == "cleared"], [])

    def test_a_person_s_word_clears_a_pause_early_and_the_time_does_not_clear_it_again(self) -> None:
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", why="refused", cause="limit",
                                                until="2026-10-21T20:40:00Z", t="2026-10-21T16:40:00Z"),
                  logs.entry("told", fairway="ORD", message="resume now", t="2026-10-21T17:00:00Z", by="person"))
        self.run_once()
        self.run_once()
        receipts = [entry.fields["what"] for entry in self.harbour() if entry.kind == "cleared"]
        self.assertEqual(receipts, ["resume now"])


class NeedsTest(MergeFixture):
    """A park's needs are ticked against trunk, or by a person, and the park clears when the last one is.

    recap's LB6, LB7 and LB8 each parked on the same five changes to trunk, written three times as prose.
    """

    PARKED = "2026-10-21T16:03:00Z"

    def park(self, *needs: dict, slice_id: str = "LB6") -> None:
        self.deck("ordering", "ORD", logs.entry("parked", fairway="ORD", slice=slice_id, why=f"{slice_id}: D32",
                                                cause="host", needs=list(needs), then="re-dispatch in catch-up",
                                                t=self.PARKED))

    def receipts(self, kind: str) -> list[dict]:
        return [dict(e.fields) for e in self.harbour() if e.kind == kind]

    def test_a_text_need_trunk_satisfies_is_met_at_trunk_s_commit_and_the_park_clears(self) -> None:
        self.park({"what": "service.txt says one", "by": "fleet",
                   "check": {"kind": "text", "path": "service.txt", "has": "one"}})
        done = self.run_once()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        met = self.receipts("need-met")
        self.assertEqual([(m["parked"], m["need"]) for m in met], [(self.PARKED, 0)])
        self.assertIn(f"trunk at {self.trunk_was[:8]}", met[0]["how"])
        self.assertEqual([c["what"] for c in self.receipts("cleared")], ["needs met: 1 of 1"])

    def test_a_need_trunk_does_not_satisfy_yet_stands_and_a_berth_s_edit_does_not_tick_it(self) -> None:
        self.park({"what": "service.txt says two", "by": "fleet",
                   "check": {"kind": "text", "path": "service.txt", "has": "two"}})
        (self.root / "service.txt").write_text("two\n", encoding="utf-8")  # edited, not on trunk
        self.run_once()
        self.assertEqual(self.receipts("need-met"), [])
        self.assertEqual(self.receipts("cleared"), [])

    def test_a_make_need_runs_a_check_target_on_trunk_and_no_other_target(self) -> None:
        (self.root / "Makefile").write_text(self.GATE + "check-thing:\n\t@test -f service.txt\n"
                                            "deploy:\n\t@echo deployed\n", encoding="utf-8")
        self.commit("targets")
        self.park({"what": "check-thing passes", "by": "fleet", "check": {"kind": "make", "target": "check-thing"}},
                  {"what": "deploy passes", "by": "fleet", "check": {"kind": "make", "target": "deploy"}})
        self.run_once()
        self.assertEqual([m["need"] for m in self.receipts("need-met")], [0])
        self.assertEqual(self.receipts("cleared"), [])
        self.assertFalse((self.root / ".slipwai/needs").exists())

    def test_a_person_s_tick_is_a_need_done_line_and_the_last_tick_clears_the_park(self) -> None:
        self.park({"what": "decide whether LB13 follows", "by": "person"},
                  {"what": "service.txt says one", "by": "fleet",
                   "check": {"kind": "text", "path": "service.txt", "has": "one"}})
        self.run_once()
        self.assertEqual([m["need"] for m in self.receipts("need-met")], [1])
        self.assertEqual(self.receipts("cleared"), [])
        self.deck("ordering", "ORD", logs.entry("need-done", fairway="ORD", parked=self.PARKED, need=0))
        self.run_once()
        self.run_once()
        met = sorted((m["need"], m["how"]) for m in self.receipts("need-met"))
        self.assertEqual(met[0], (0, "a person ticked it on the board"))
        self.assertEqual(len(met), 2)
        self.assertEqual(len(self.receipts("cleared")), 1)


if __name__ == "__main__":
    unittest.main()
