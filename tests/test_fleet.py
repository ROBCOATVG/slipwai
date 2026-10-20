"""The fleet board: every column folded from the logs, and nothing kept anywhere else.

The two states it matters most to tell apart are `stalled` and `finished`, because in a status field they
look identical — neither is writing anything. The log tells them apart for nothing, which is the whole
reason `heartbeat` is a line.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import fleet, logs
from slipwai.cli_fleet import lines
from slipwai.project.harbour import harbour_config

NOW = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)


def when(minutes: float) -> str:
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")

    def deck(self, fairway: str, *entries: logs.Entry, feature: str = "ordering") -> None:
        path = self.root / logs.deck_path(feature, fairway)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def harbour(self, *entries: logs.Entry, machine: str = "") -> None:
        """One machine's harbour log — the one a project already had, where none is named."""
        path = self.root / (logs.harbour_path(machine) if machine else logs.HARBOUR)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(entry.line())

    def board(self) -> dict:
        return fleet.board(self.root, json.loads((self.root / "harbour.json").read_text()), now=NOW)


class AbreastTest(Fixture):
    """A stream runs several slices at once now, and the board names them all."""

    def test_every_slice_in_flight_is_in_the_slice_column(self) -> None:
        self.deck("LVR", *(logs.entry("claimed", fairway="LVR", slice=one, t=when(1)) for one in ("L02", "L03")))
        row = self.board()["berths"][0]
        self.assertEqual((row["slice"], row["state"]), ("L02, L03", "working"))

    def test_a_slice_parked_on_its_own_leaves_the_stream_working(self) -> None:
        self.deck("LVR", *(logs.entry("claimed", fairway="LVR", slice=one, t=when(1)) for one in ("L02", "L03")),
                  logs.entry("parked", fairway="LVR", slice="L03", why="which notice lengths?", t=when(1)))
        row = self.board()["berths"][0]
        self.assertEqual((row["slice"], row["state"]), ("L02", "working"))
        self.assertEqual([one["kind"] for one in self.board()["inbox"]], ["parked"])


class StateTest(Fixture):
    def test_a_fairway_with_a_log_and_no_lines_is_not_started(self) -> None:
        """Not `0%` and not `working`: a fairway nobody has begun is a fact, and the board says it."""
        path = self.root / logs.deck_path("ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        self.assertEqual(self.board()["berths"][0]["state"], "not started")
        self.assertEqual(self.board()["berths"][0]["slice"], fleet.NOTHING)

    def test_a_fairway_writing_lines_is_working(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD", t=when(1)))
        self.assertEqual(self.board()["berths"][0]["state"], "working")

    def test_a_fairway_that_has_stopped_writing_is_stalled_and_not_finished(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(500)))
        self.assertEqual(self.board()["berths"][0]["state"], "stalled")

    def test_a_fairway_whose_last_line_is_a_merge_is_finished_and_not_stalled(self) -> None:
        """The pair that look identical in a status field, told apart by the last line for nothing."""
        self.deck("ORD",
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(600)),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc123", t=when(500)))
        self.assertEqual(self.board()["berths"][0]["state"], "finished")

    def test_a_parked_fairway_says_parked_whatever_its_heartbeat(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD", t=when(1)),
                  logs.entry("parked", fairway="ORD", why="a person has to look", t=when(1)))
        self.assertEqual(self.board()["berths"][0]["state"], "parked")

    def test_the_slice_shown_is_the_one_claimed_and_not_yet_merged(self) -> None:
        self.deck("ORD",
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(9)),
                  logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc", t=when(8)),
                  logs.entry("claimed", fairway="ORD", slice="ORD-02", t=when(7)))
        self.assertEqual(self.board()["berths"][0]["slice"], "ORD-02")


class QueuedTest(Fixture):
    def test_a_claimed_slice_no_session_is_on_is_queued_not_working(self) -> None:
        """hr-test-2 drew seven slices as working with three abreast: four were claimed and waiting for a slot,
        writing nothing, and the board could not tell them from the three a session was on."""
        self.deck("LVR", logs.entry("claimed", fairway="LVR", slice="L04", t=when(90)),
                  logs.entry("stopped", fairway="LVR", slice="L04", t=when(80)),
                  logs.entry("claimed", fairway="LVR", slice="L02", t=when(10)),
                  logs.entry("heartbeat", fairway="LVR", slice="L02", t=when(1)))
        stream = fleet.fairways(self.root)[0][0]
        self.assertEqual(stream.at_work(now=NOW), ["L02"])
        self.assertEqual(stream.queued(now=NOW), ["L04"])
        row = self.board()["berths"][0]
        self.assertEqual((row["slice"], row["queued"]), ("L02", "L04"))
        self.assertIn("queued", "\n".join(lines(self.root)))


class NumbersTest(Fixture):
    def test_a_number_nobody_wrote_is_a_dash_and_not_a_zero(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD", t=when(1)))
        self.assertEqual(self.board()["berths"][0]["tokens"], fleet.NOTHING)
        self.assertIsNone(self.board()["bunker"]["spent"])

    def test_tokens_are_summed_from_the_lines_that_record_them(self) -> None:
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD", tokens=120, t=when(2)),
                  logs.entry("heartbeat", fairway="ORD", tokens=80, t=when(1)))
        self.assertEqual(self.board()["berths"][0]["tokens"], 200)
        self.assertEqual(self.board()["bunker"]["spent"], 200)

    def test_the_telegraph_is_read_from_the_file_and_what_banked_it_from_the_log(self) -> None:
        self.harbour(logs.entry("fires-banked", harbour=True, step="slow-ahead",
                                why="the day's bunker is spent", t=when(3)))
        pressure = self.board()["pressure"]
        self.assertEqual(pressure["position"], "half-ahead")
        self.assertIn("bunker is spent", pressure["banked"])


class InboxTest(Fixture):
    def test_an_unanswered_message_is_what_the_board_leads_with(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="look at this", t=when(5)))
        waiting = self.board()["inbox"]
        self.assertEqual(len(waiting), 1)
        self.assertEqual(waiting[0]["what"], "look at this")
        self.assertIn("waiting on you: 1", "\n".join(lines(self.root)))

    def test_an_answered_message_is_not_waiting_on_anybody(self) -> None:
        """A `read` carries the `t` of the `told` it answers, which is what makes it a receipt."""
        self.deck("ORD", logs.entry("told", fairway="ORD", message="look at this", t=when(5)),
                  logs.entry("read", fairway="ORD", told=when(5), t=when(4)))
        self.assertEqual(self.board()["inbox"], [])

    def test_an_answer_to_a_park_the_captain_took_up_is_not_waiting(self) -> None:
        """Nothing wrote the `read`, so every `go` a person sent stayed under *Waiting on you* for ever and
        turned the Slices step red while the fleet ran and nothing was parked."""
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="open questions", t=when(9)),
                  logs.entry("told", fairway="ORD", message="go", t=when(8)),
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(7)))
        self.assertEqual([one for one in self.board()["inbox"] if one["kind"] == "told"], [])

    def test_a_message_a_decision_followed_is_not_waiting(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="decide for me", t=when(8)),
                  logs.entry("decision", fairway="ORD", id="ORD-Q1", what="D3", t=when(7),
                             decided_by="human"))
        self.assertEqual(self.board()["inbox"], [])

    def test_a_note_written_while_the_fairway_worked_is_still_waiting(self) -> None:
        """A session's note for the host is a task for a person, and the next claim does not answer it."""
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(9)),
                  logs.entry("told", fairway="ORD", message="For the host: ignore preflight.json", t=when(8)),
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(7)))
        self.assertEqual([one["what"] for one in self.board()["inbox"]], ["For the host: ignore preflight.json"])

    def test_a_note_one_session_left_another_is_not_waiting_on_you(self) -> None:
        """Three slices abreast talk through the one log they share. hr-test-2's Slices step went red on
        `For L02's captain, from L06's: …` while all three ran with nothing blocked."""
        self.deck("ORD", logs.entry("told", fairway="ORD", message="For L02's captain, from L06's: L06 merges first",
                                    t=when(8)),
                  logs.entry("told", fairway="ORD", message="For the captain: slice/L06 is done", t=when(7)),
                  logs.entry("told", fairway="ORD", message="For the host, from L03's captain: copy .env", t=when(6)),
                  logs.entry("told", fairway="ORD", message="For the team: go", t=when(5), by="person"))
        self.assertEqual([one["what"] for one in self.board()["inbox"]],
                         ["For the host, from L03's captain: copy .env", "For the team: go"])

    def test_unread_decisions_block_only_past_the_ceiling(self) -> None:
        decided = [logs.entry("decision", fairway="ORD", id=f"ORD-Q{n}", what=f"D{n}", t=when(9 - n))
                   for n in range(3)]
        self.deck("ORD", *decided)
        below: list[dict] = fleet.board(self.root, {"decision_ceiling": 5}, now=NOW)["inbox"]  # type: ignore[assignment]
        self.assertEqual([(row["kind"], row["blocking"]) for row in below], [("decisions", "no")])
        over: list[dict] = fleet.board(self.root, {"decision_ceiling": 2}, now=NOW)["inbox"]  # type: ignore[assignment]
        self.assertEqual(over[0]["blocking"], "yes")
        self.assertIn("over the ceiling of 2", over[0]["what"])

    def test_a_park_is_waiting_on_a_person_too(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="the gate stayed red", t=when(2)))
        self.assertEqual(self.board()["inbox"][0]["kind"], "parked")

    def test_an_open_question_is_waiting_on_a_person(self) -> None:
        """The chart's context question, posted by a headless `/launch` that proceeded on its proposal.
        The board drew only `told` and `parked`, so a question nobody had to answer before the run went on
        was a question nobody saw."""
        self.deck("leaver", logs.entry("question", fairway="leaver", slice="chart", id="D25",
                                       what="one context, leaver?", t=when(3)))
        waiting = self.board()["inbox"]
        self.assertEqual([row["kind"] for row in waiting], ["question"])
        self.assertEqual(waiting[0]["what"], "D25 (chart): one context, leaver?")

    def test_a_question_a_decision_answered_is_not(self) -> None:
        self.deck("leaver", logs.entry("question", fairway="leaver", slice="chart", id="D25", what="?", t=when(3)),
                  logs.entry("decision", fairway="leaver", id="D25", what="confirmed", t=when(1),
                             decided_by="human"))
        self.assertEqual(self.board()["inbox"], [])


class ParkReceiptTest(Fixture):
    def test_a_park_clock_is_the_original_park_and_later_life_never_resets_it(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="choose the storage", t=when(120)),
                  logs.entry("heartbeat", fairway="ORD", t=when(1)))
        row = self.board()["inbox"][0]
        self.assertEqual((row["t"], row["waited"], row["waiting_on"], row["overdue"]),
                         (when(120), "120m", "harbourmaster", "yes"))
        self.assertIn("waiting on harbourmaster for 120m", fleet.inbox_detail(row))
        self.assertIn("waiting on harbourmaster", "\n".join(lines(self.root)))

    def test_a_matching_receipt_removes_the_park_and_its_parked_state(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="choose the storage", t=when(2)))
        self.harbour(logs.entry("cleared", harbour=True, fairway="ORD", parked=when(2),
                                what="use the existing store", t=when(1)), machine="another")
        self.assertEqual(self.board()["inbox"], [])
        self.assertNotEqual(self.board()["berths"][0]["state"], "parked")

    def test_another_fairway_or_a_previous_park_receipt_cannot_answer_this_one(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="old", t=when(5)),
                  logs.entry("parked", fairway="ORD", why="new", t=when(2)))
        self.harbour(logs.entry("cleared", harbour=True, fairway="ORD", parked=when(5), what="old answer"),
                     logs.entry("cleared", harbour=True, fairway="BIL", parked=when(2), what="other answer"))
        self.assertEqual([row["what"] for row in self.board()["inbox"]], ["new"])
        self.assertEqual(self.board()["berths"][0]["state"], "parked")


class FeedTest(Fixture):
    def test_both_logs_are_merged_by_time(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(3)))
        self.harbour(logs.entry("telegraph", harbour=True, position="slow-ahead", t=when(2)))
        self.deck("BIL", logs.entry("claimed", fairway="BIL", slice="BIL-01", t=when(1)),
                  feature="ordering")
        self.assertEqual([who for _, who, _ in self.board()["feed"]], ["ORD", "harbour", "BIL"])


class UnreadableTest(Fixture):
    def test_a_log_that_cannot_be_read_is_said_rather_than_drawn_empty(self) -> None:
        """An empty row and an unreadable one are different facts, and drawing both the same is guessing."""
        path = self.root / logs.deck_path("ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json\n", encoding="utf-8")
        self.assertIn("ORD", self.board()["unreadable"])
        self.assertIn("cannot be read", "\n".join(lines(self.root)))


class ThreeMachinesTest(Fixture):
    """Three machines write three harbour logs and the board folds them into one.

    The harbour log had exactly one writer — unambiguous on one machine, meaningless on three. An elected
    writer needs an election; three writers on one file breaks the rule the whole log design rests on. One
    file per machine folded on read costs nothing here and removes the single writer rather than electing
    one, and the board is where that has to be invisible: a board showing one machine's harbour would be
    confidently wrong about the other two, which is worse than no board.
    """

    def test_the_board_folds_three_harbour_logs_into_one_feed(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(9)))
        for minutes, machine, position in ((8, "one", "slow-ahead"), (6, "two", "half-ahead"),
                                           (7, "three", "dead-slow")):
            self.harbour(logs.entry("telegraph", harbour=True, position=position, t=when(minutes)),
                         machine=machine)
        feed = [(who, kind) for _, who, kind in self.board()["feed"]]
        self.assertEqual(feed.count(("harbour", "telegraph")), 3)

    def test_and_in_the_order_the_lines_were_written_rather_than_by_machine(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(5)))
        self.harbour(logs.entry("flag-hoisted", harbour=True, flag="late", where="x", t=when(2)),
                     machine="zulu")
        self.harbour(logs.entry("flag-struck", harbour=True, flag="early", t=when(8)), machine="alpha")
        self.assertEqual([kind for _, _, kind in self.board()["feed"]],
                         ["flag-struck", "claimed", "flag-hoisted"])

    def test_the_last_word_on_the_fires_is_the_harbour_s_and_not_one_machine_s(self) -> None:
        """What the board says the harbour is doing has to be the latest line any machine wrote, or two
        people looking at two boards disagree about whether the fires are banked."""
        self.harbour(logs.entry("fires-banked", harbour=True, step="boilers", why="early", t=when(9)),
                     machine="alpha")
        self.harbour(logs.entry("fires-banked", harbour=True, step="fanout", why="late", t=when(1)),
                     machine="zulu")
        self.assertEqual(self.board()["pressure"]["banked"], "late")


class FoldTest(Fixture):
    def test_the_board_keeps_nothing_so_a_new_line_changes_it(self) -> None:
        """Every column is computed each time: a board that cached anything could be wrong about what
        happened, and a board that can be wrong is worse than no board, because it is believed."""
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=when(2)))
        before = self.board()["berths"][0]["merged"]
        self.deck("ORD", logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc", t=when(1)))
        self.assertEqual((before, self.board()["berths"][0]["merged"]), (0, 1))


if __name__ == "__main__":
    unittest.main()
