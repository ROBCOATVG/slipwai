"""What the board shows of a slice nobody's rule will move, and of a stream whose captain is the program alone.

1. A slice paused or stopped by a person, or paused by its captain, says on its card who holds it and since
   when — a person's pause from the moment it is heard, before its turn has ended — and a captain's pause is
   on *Waiting on you* under *When you have time*, beside a person's (decision 17a, amending 11).
2. Where `captain.json` says the agent is off or failed, the captains strip and the captain's window say the
   stream runs on the program alone and why; the window lists the deck's `noted` lines as news, never as
   something owed an answer.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import board_read, logs, talk
from slipwai.captains_strip import strip_html
from slipwai.on_you import waiting
from slipwai.slice_card import lit, slice_html
from slipwai.talk_fold import clock

T = "2026-11-17T09:30:00Z"


def row(slice_id: str, state: str, fairway: str = "ORD") -> dict[str, str]:
    return {"slice": slice_id, "title": "", "state": state, "fairway": fairway, "feature": "ordering", "why": ""}


class HeldCardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.home = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")

    def note(self, kind: str, by: str, t: str = T, why: str = "") -> None:
        """A thread line at a set instant, as the driver writes one."""
        self.home.mkdir(parents=True, exist_ok=True)
        with (self.home / "thread.jsonl").open("a", encoding="utf-8") as out:
            out.write(json.dumps({"v": 1, "t": t, "kind": kind, "by": by, **({"why": why} if why else {})}) + "\n")

    def card(self, state: str = "queued") -> str:
        [drawn] = lit([row("ORD-01", state)], {}, self.root)
        return slice_html(drawn)

    def later(self) -> list[str]:
        found = waiting(SimpleNamespace(root=self.root, fitting=None), {}, {}, [row("ORD-01", "queued")])
        return [one["text"] for one in found["later"]]

    def test_a_person_s_pause_heard_before_its_turn_ended_is_on_the_card_with_who_and_since_when(self) -> None:
        self.note("pausing", "person", why="lunch")
        self.assertIn(f'<span class="held-by">Paused by you since {clock(T)}</span>', self.card("working"))
        self.note("paused", "person", t="2026-11-17T09:41:00Z", why="lunch")
        self.assertIn(f"Paused by you since {clock(T)}", self.card(), "the hold is as old as when it was heard")

    def test_a_person_s_stop_is_on_the_card(self) -> None:
        self.note("stopped", "person", why="wrong way")
        self.assertIn(f"Stopped by you since {clock(T)}", self.card("todo"))

    def test_a_captain_s_pause_is_on_the_card_and_waits_for_a_person_with_theirs(self) -> None:
        self.assertEqual(self.later(), [])
        self.note("paused", "captain:ORD", why="trunk is red")
        self.assertIn(f"Paused by captain:ORD since {clock(T)}", self.card())
        self.assertEqual(self.later(), ["ORD-01 is paused by captain:ORD, and no rule lifts it: resume it when you "
                                        "are ready"])

    def test_nothing_is_said_of_a_slice_nothing_holds(self) -> None:
        self.note("paused", "captain:ORD")
        self.note("stopped", "captain:ORD")  # a captain's own stop hands the slice back to the queue
        self.assertNotIn("held-by", self.card())
        self.assertEqual(self.later(), [])


class AloneTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        kept = board_read.Read([row("ORD-01", "working")], "", {}, {}, {}, [], {})
        patched = mock.patch("slipwai.captain_window.read", return_value=kept)
        patched.start()
        self.addCleanup(patched.stop)
        self.events = logs.run_dir(self.root) / "events/ORD"

    def failed(self) -> None:
        self.events.mkdir(parents=True, exist_ok=True)
        why = "the captain agent failed while deciding stuck (RuntimeError: gone)"
        (self.events / "captain.json").write_text(json.dumps({"v": 1, "agent": False, "t": T, "why": why}),
                                                  encoding="utf-8")
        self.deck("ORD", logs.entry("noted", fairway="ORD", by="captain program",
                                    what="The captain agent failed while deciding stuck; the stream runs on the "
                                         "program alone until the captain is started again"))

    def test_a_stream_whose_captain_agent_failed_says_it_runs_on_the_program_alone_and_why(self) -> None:
        rows = [row("ORD-01", "working")]
        self.assertNotIn("program alone", strip_html(self.root, rows, set()))
        self.failed()
        drawn = strip_html(self.root, rows, set())
        self.assertIn('<span class="alone">Running on the program alone: the captain agent failed while deciding '
                      "stuck (RuntimeError: gone)</span>", drawn)
        code, page = self.get("/captain-window?fairway=ORD")
        self.assertEqual(code, 200)
        self.assertIn(f"This stream is running on the program alone since {clock(T)}</b>: the captain agent "
                      f"failed while deciding stuck", page)
        for said in (drawn, page):
            self.assertNotIn("harbourmaster", said.lower())

    def test_the_window_lists_what_the_program_noted_as_news_and_nothing_waits_on_it(self) -> None:
        self.failed()
        found = json.loads(self.get("/captain-window.json?fairway=ORD")[1])
        self.assertIn("Noted by the captain program", found["decided"])
        self.assertIn("nothing here waits on you", found["decided"])
        self.assertIn("the stream runs on the program alone until the captain is started again", found["decided"])
        self.assertNotIn("<button", found["decided"])
        listed = waiting(SimpleNamespace(root=self.root, fitting=None), {}, {}, [row("ORD-01", "working")])
        self.assertEqual(listed["count"], 0, listed)

    def test_a_harness_with_no_protocol_launch_is_said_the_same_way(self) -> None:
        self.events.mkdir(parents=True, exist_ok=True)
        (self.events / "captain.json").write_text(json.dumps(
            {"v": 1, "agent": False, "t": T, "why": "no captain agent: this harness has no proven protocol launch"}),
            encoding="utf-8")
        self.assertIn("Running on the program alone: no captain agent: this harness has no proven protocol launch",
                      strip_html(self.root, [row("ORD-01", "working")], set()))

    def test_the_window_goes_by_what_the_captain_said_over_a_harbour_that_asks_for_an_agent(self) -> None:
        harbour = self.root / "harbour.json"
        held = json.loads(harbour.read_text(encoding="utf-8")) if harbour.is_file() else {}
        harbour.write_text(json.dumps({**held, "captain": {"agent": True}}), encoding="utf-8")
        decided = json.loads(self.get("/captain-window.json?fairway=ORD")[1])["decided"]
        self.assertIn("Nothing yet today", decided, "before the captain has started, the file is the word")
        self.assertNotIn("program alone", decided)
        self.events.mkdir(parents=True, exist_ok=True)
        (self.events / "captain.json").write_text(json.dumps(
            {"v": 1, "agent": False, "t": T, "why": "no captain agent: this harness has no proven protocol launch"}),
            encoding="utf-8")
        decided = json.loads(self.get("/captain-window.json?fairway=ORD")[1])["decided"]
        self.assertIn("captain is the program alone", decided)
        self.assertIn("running on the program alone since", decided)
        self.assertIn("no proven protocol launch", decided)
        self.assertNotIn("Nothing yet today", decided)


if __name__ == "__main__":
    unittest.main()
