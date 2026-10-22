"""The recap voyage of 2026-10-21, replayed against the board.

`tests/fixtures/recap-day/` is that day's three logs as the captains and the harbourmaster wrote them: two
session-limit refusals, eleven parks, two clears by hand, and a reset nobody acted on. The fleet-status
plan (`docs/fleet-status-plan.md`) was drawn from this day, and every slice of it adds an assertion here —
first against the logs as they were, then against the same logs with the park record the later slices
write, so the board is held to the day it was designed for.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import fleet, logs

FIXTURE = Path(__file__).resolve().parent / "fixtures/recap-day"
#: 09:02 London on 2026-10-22, when the person restarted the fleet and nothing happened.
MORNING = datetime(2026, 10, 22, 8, 2, tzinfo=UTC)
#: The five things LB6, LB7 and LB8 each asked for on trunk, as the record they would write now.
MOVE = [{"what": "context: catch-up on LB6, LB7, LB8, LB9, LB10 in docs/event-model/model.yaml", "by": "fleet",
         "check": {"kind": "text", "path": "docs/event-model/model.yaml", "has": "context: catch-up"}},
        {"what": "make chart and make decisions put the five in the catch-up fairway", "by": "fleet",
         "check": {"kind": "make", "target": "check-chart"}},
        {"what": "docs/architecture.md and the recap-api purpose name the move", "by": "person"},
        {"what": "D33's clock-skew sentence in streams.listening.because", "by": "fleet",
         "check": {"kind": "text", "path": "docs/event-model/model.yaml", "has": "clock-ahead"}},
        {"what": "LB13 follows (recommended), LB12 stays (recommended)", "by": "person"}]


def copied() -> Path:
    root = Path(tempfile.mkdtemp())
    shutil.copytree(FIXTURE / ".slipwai", root / ".slipwai")
    return root


def recorded() -> Path:
    """The same day, with the park record the later slices write: every `exited 1` park a limit lifting at
    21:40 London, every host-change park a `host` with the five needs."""
    root = copied()
    for path in (root / ".slipwai/logs/001-audiobook-recap").glob("*.jsonl"):
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            body = json.loads(line)
            if body.get("kind") == "parked":
                why = str(body.get("why", ""))
                if "`/sail` exited 1" in why:
                    body.update(cause="limit", until="2026-10-21T20:40:00Z")
                elif "host change" in why or "(D32)" in why:
                    body.update(cause="host", needs=MOVE, then="re-dispatch in the catch-up fairway at T001")
            lines.append(json.dumps(body, ensure_ascii=False))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


class AsItWasTest(unittest.TestCase):
    """The logs as the captains wrote them: eleven parks, none with a cause, all read as waiting on you."""

    def setUp(self) -> None:
        self.found = fleet.board(copied(), {"boilers": 3}, now=MORNING)

    def test_the_fixture_reads_whole(self) -> None:
        self.assertEqual(self.found["unreadable"], {})
        self.assertEqual({row["fairway"] for row in self.found["berths"]}, {"library", "catch-up"})

    def test_eleven_parks_stand_and_every_one_is_other(self) -> None:
        parks = [row for row in self.found["inbox"] if row["kind"] == "parked"]
        self.assertEqual(len(parks), 11)
        self.assertEqual({row["cause"] for row in parks}, {"other"})
        self.assertEqual(self.found["counts"]["parked"], 11)
        self.assertEqual(self.found["counts"]["paused"], 0)

    def test_nothing_is_running_and_both_streams_are_parked(self) -> None:
        self.assertEqual(self.found["counts"]["running"], 0)
        self.assertEqual({row["state"] for row in self.found["berths"]}, {"parked"})

    def test_other_parks_group_with_nothing_so_the_board_lists_all_eleven(self) -> None:
        self.assertEqual(len(self.found["groups"]), 11)


class WithTheRecordTest(unittest.TestCase):
    """The same day with the record: two groups, eight paused on the limit, three parked on one change."""

    def setUp(self) -> None:
        self.found = fleet.board(recorded(), {"boilers": 3}, now=MORNING)

    def test_two_groups_where_there_were_eleven_rows(self) -> None:
        found = self.found["groups"]
        self.assertEqual([one["cause"] for one in found], ["host", "limit"])

    def test_the_limit_group_is_eight_slices_paused_until_the_reset(self) -> None:
        limit = next(one for one in self.found["groups"] if one["cause"] == "limit")
        self.assertEqual(sorted(limit["slices"]), ["LB1", "LB11", "LB15", "LB2", "LB3", "LB4", "LB9", "catch-up"])
        self.assertEqual(limit["until"], "2026-10-21T20:40:00Z")
        self.assertEqual(limit["paused"], "yes")
        self.assertEqual(self.found["counts"]["paused"], 8)

    def test_the_host_group_is_three_slices_on_five_needs_none_met(self) -> None:
        host = next(one for one in self.found["groups"] if one["cause"] == "host")
        self.assertEqual(host["slices"], ["LB6", "LB7", "LB8"])
        self.assertEqual(len(host["needs"]), 5)
        self.assertEqual(host["met"], 0)
        self.assertEqual(host["then"], "re-dispatch in the catch-up fairway at T001")
        self.assertEqual(self.found["counts"]["parked"], 3)

    def test_catch_up_is_paused_and_library_is_parked_because_three_slices_wait_on_a_person(self) -> None:
        states = {row["fairway"]: row["state"] for row in self.found["berths"]}
        self.assertEqual(states, {"catch-up": "paused", "library": "parked"})

    def test_the_old_lines_still_read_beside_the_new(self) -> None:
        held = [row for row in self.found["inbox"] if row["kind"] == "parked" and row["cause"] == "other"]
        self.assertEqual(held, [])
        self.assertEqual(self.found["unreadable"], {})

    def test_the_fleet_tab_opens_on_the_sentence_and_the_processes(self) -> None:
        from slipwai.bridge_page import page, read_only
        from slipwai.fleet_page import headline

        colour, sentence, under = headline(self.found, now=MORNING)
        self.assertEqual(colour, "brass")
        # One change on trunk, and four notes sessions left for the host that nobody has read.
        self.assertEqual(sentence, "Stopped. 3 slices wait on you for 5 things.")
        self.assertIn("8 slices more are paused until", under)
        said = page(self.found, {"boilers": 3})
        self.assertIn("library captain", said)
        self.assertIn("catch-up captain", said)
        self.assertIn("not lit", said)
        self.assertIn("0 of 5 done", said)
        self.assertIn("Landed, carry on", said)
        self.assertIn("re-dispatch in the catch-up fairway at T001", said)
        self.assertLess(said.index("Waiting on you"), said.index("Streams"))
        still = read_only(self.found, {"boilers": 3})
        self.assertNotIn("<button", still)
        self.assertIn("Each park, in one line", still)

    def test_the_reasons_for_the_day_are_in_the_logs(self) -> None:
        """What the plan says happened is what the fixture says happened."""
        deck = logs.fold((recorded() / ".slipwai/logs/001-audiobook-recap/library.jsonl")
                         .read_text(encoding="utf-8").splitlines())
        cleared_by_hand = [e for e in logs.harbour_fold(recorded()) if e.kind == "cleared"]
        self.assertEqual(len(cleared_by_hand), 13)
        self.assertEqual(sum(1 for e in deck if e.kind == "parked"), 23)


if __name__ == "__main__":
    unittest.main()
