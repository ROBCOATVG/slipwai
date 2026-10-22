"""The park record on the board, and the processes beside it.

Split from `test_fleet.py` at its budget: these are the rows the fleet-status plan added — a park's cause,
its needs with their ticks, the groups the parks fold into, and each process with its own word on why it
left. The fixture is `test_fleet`'s, because the board under test is the same board.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from test_fleet import Fixture, when

from slipwai import fleet, logs
from slipwai.cli_fleet import lines


class RecordTest(Fixture):
    """A park's record reaches the board: its cause, its needs with their ticks, and whether it lifts by itself.

    recap, 2026-10-21: eleven parks under *Waiting on you* were one session limit and one change to trunk.
    """

    NEEDS = [{"what": "context: catch-up in docs/event-model/model.yaml", "by": "fleet",
              "check": {"kind": "text", "path": "docs/event-model/model.yaml", "has": "context: catch-up"}},
             {"what": "decide whether LB13 follows", "by": "person"}]

    def host_park(self, slice_id: str, at: float) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice=slice_id, t=when(at + 1)),
                  logs.entry("parked", fairway="ORD", slice=slice_id, why=f"{slice_id}: D32", cause="host",
                             needs=self.NEEDS, then="re-dispatch in catch-up at T001", t=when(at)))

    def test_a_park_row_carries_its_record_and_the_ticks_the_harbourmaster_wrote(self) -> None:
        self.host_park("LB6", 30)
        self.harbour(logs.entry("need-met", harbour=True, fairway="ORD", parked=when(30), need=0,
                                how="trunk at abc12345"))
        row = self.board()["inbox"][0]
        self.assertEqual((row["cause"], row["then"]), ("host", "re-dispatch in catch-up at T001"))
        self.assertEqual([need["met"] for need in row["needs"]], ["yes", "no"])
        self.assertIn("model.yaml holds", row["needs"][0]["how"])
        self.assertEqual(row["paused"], "no")

    def test_a_person_s_tick_in_the_deck_log_counts_before_the_harbourmaster_carries_it(self) -> None:
        self.host_park("LB6", 30)
        self.deck("ORD", logs.entry("need-done", fairway="ORD", parked=when(30), need=1))
        self.assertEqual([need["met"] for need in self.board()["inbox"][0]["needs"]], ["no", "yes"])

    def test_three_parks_on_one_change_to_trunk_are_one_group_with_the_slices_on_it(self) -> None:
        for slice_id, at in (("LB6", 30), ("LB7", 20), ("LB8", 10)):
            self.host_park(slice_id, at)
        found = self.board()["groups"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["slices"], ["LB6", "LB7", "LB8"])
        self.assertEqual(found[0]["cause"], "host")
        self.assertEqual(len(found[0]["needs"]), 2)
        self.assertEqual(found[0]["then"], "re-dispatch in catch-up at T001")

    def test_limit_parks_are_one_group_however_many_slices_and_it_is_paused_not_waiting(self) -> None:
        for slice_id, at in (("LB3", 30), ("LB1", 20)):
            self.deck("ORD", logs.entry("claimed", fairway="ORD", slice=slice_id, t=when(at + 1)),
                      logs.entry("parked", fairway="ORD", slice=slice_id, why=f"{slice_id}: refused",
                                 cause="limit", until="2999-01-01T20:40:00Z", t=when(at)))
        self.deck("CU", logs.entry("claimed", fairway="CU", slice="CU1", t=when(60)),
                  logs.entry("parked", fairway="CU", why="CU1: refused", cause="limit",
                             until="2999-01-01T15:40:00Z", t=when(50)), feature="ordering")
        board = self.board()
        found = board["groups"]
        self.assertEqual(len(found), 1)
        self.assertEqual(sorted(found[0]["slices"]), ["CU", "LB1", "LB3"])
        self.assertEqual(found[0]["paused"], "yes")
        self.assertEqual(found[0]["until"], "2999-01-01T20:40:00Z")
        self.assertEqual(board["counts"]["paused"], 3)
        self.assertEqual(board["counts"]["parked"], 0)
        states = {row["fairway"]: row["state"] for row in board["berths"]}
        self.assertEqual(states["CU"], "paused")
        self.assertIn("paused until", fleet.inbox_detail(board["inbox"][0]))

    def test_a_park_with_no_cause_is_other_and_groups_with_nothing(self) -> None:
        for slice_id, at in (("LB3", 30), ("LB1", 20)):
            self.deck("ORD", logs.entry("claimed", fairway="ORD", slice=slice_id, t=when(at + 1)),
                      logs.entry("parked", fairway="ORD", slice=slice_id, why=f"{slice_id}: exited 1", t=when(at)))
        found = self.board()["groups"]
        self.assertEqual([one["cause"] for one in found], ["other", "other"])
        self.assertEqual(self.board()["counts"]["parked"], 2)


class ProcessTest(Fixture):
    """Each process the fleet has, what it is doing and what would start it: the question a restart that
    lit two captains for one second each left unanswered on recap."""

    def pid_file(self, name: str, pid: int, exit_why: str = "") -> None:
        import json as json_

        place = self.root / fleet.RUNNING
        place.mkdir(parents=True, exist_ok=True)
        (place / f"{name}.pid").write_text(f"{pid}\n", encoding="utf-8")
        if exit_why:
            (place / f"{name}.exit").write_text(json_.dumps({"at": when(5), "why": exit_why, "code": 0}),
                                                encoding="utf-8")

    def gone(self) -> int:
        """A pid nothing is using: a child that has already exited."""
        import subprocess
        import sys

        done = subprocess.run([sys.executable, "-c", "pass"], check=False)
        return done.pid if hasattr(done, "pid") else 2**22 - 7

    def test_a_live_pid_is_running_and_says_nothing_else(self) -> None:
        import os

        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(10)))
        self.pid_file("harbourmaster", os.getpid())
        self.pid_file("captain-ORD", os.getpid())
        rows = {row["name"]: row for row in self.board()["processes"]}
        self.assertEqual(rows["harbourmaster"]["state"], "running")
        self.assertEqual(rows["captain-ORD"]["state"], "running")
        self.assertEqual(rows["captain-ORD"]["starts_when"], "")

    def test_an_exited_captain_carries_its_own_word_and_what_starts_it(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(10)),
                  logs.entry("parked", fairway="ORD", why="ORD-01: decide", cause="question", t=when(8)))
        self.pid_file("captain-ORD", 2**22 - 7, "ORD is parked — ORD-01: decide")
        row = next(one for one in self.board()["processes"] if one["name"] == "captain-ORD")
        self.assertEqual(row["state"], "exited")
        self.assertEqual(row["why"], "ORD is parked — ORD-01: decide")
        self.assertEqual(row["starts_when"], "a park is cleared")

    def test_a_captain_never_lit_for_a_paused_stream_says_when_the_pause_ends(self) -> None:
        self.deck("CU", logs.entry("claimed", fairway="CU", slice="CU1", t=when(10)),
                  logs.entry("parked", fairway="CU", why="CU1: refused", cause="limit",
                             until="2999-01-01T20:40:00Z", t=when(8)))
        row = next(one for one in self.board()["processes"] if one["name"] == "captain-CU")
        self.assertEqual(row["state"], "not lit")
        self.assertRegex(row["starts_when"], r"^the pause ends at \d\d:\d\d$")

    def test_a_captain_that_found_nothing_to_start_says_what_it_waits_on(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(10)),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc", t=when(8)))
        self.pid_file("captain-ORD", 2**22 - 7, "nothing to start in ORD — ORD-02 steers by Placed")
        row = next(one for one in self.board()["processes"] if one["name"] == "captain-ORD")
        self.assertEqual(row["starts_when"], "a slice may start; now ORD-02 steers by Placed")
        self.assertIn("processes", "\n".join(lines(self.root)))


if __name__ == "__main__":
    unittest.main()
