"""Talking to the fleet from the board: the captains, and what a conversation puts on the one list.

A captain's window is drawn with and without the files a captain agent writes (`orders/`, `events/`), which
are written here in the shape `docs/captain-agent-plan.md` §2.2 gives them; the captains strip and Tell every
captain are driven through the board's routes; what waits on a person is read through `on_you.waiting`.
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
from slipwai.talk_page import payload


def row(slice_id: str, state: str, fairway: str = "ORD") -> dict[str, str]:
    return {"slice": slice_id, "title": "", "state": state, "fairway": fairway, "feature": "ordering", "why": ""}


def written(path: Path, held: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(held), encoding="utf-8")


class CaptainWindowTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        rows = [row("ORD-01", "working"), row("ORD-02", "queued"), row("ORD-03", "todo"),
                row("BIL-01", "working", "BIL")]
        kept = board_read.Read(rows, "", {}, {}, {}, [], {})
        patched = mock.patch("slipwai.captain_window.read", return_value=kept)
        patched.start()
        self.addCleanup(patched.stop)
        self.run_dir = logs.run_dir(self.root)

    def test_a_captain_that_is_the_program_alone_says_so_and_still_lists_its_slices(self) -> None:
        # A newly generated project has the captain agent on; this one's harbour says it is the program alone.
        harbour = self.root / "harbour.json"
        held = json.loads(harbour.read_text(encoding="utf-8")) if harbour.is_file() else {}
        harbour.write_text(json.dumps({**held, "captain": {"agent": False}}), encoding="utf-8")
        code, page = self.get("/captain-window?fairway=ORD")
        self.assertEqual(code, 200)
        self.assertIn("Captain · ORD", page)
        self.assertIn("captain is the program alone", page)
        self.assertIn("read at its next turn", page, "what is said to it is read by the program, not left waiting")
        self.assertIn('href="/slice?fairway=ORD&amp;slice=ORD-01"', page, "each slice opens its own window")
        self.assertIn('href="/slice?fairway=ORD&amp;slice=ORD-02"', page)
        self.assertNotIn("BIL-01", page, "another stream's slice is not this captain's")
        self.assertIn("1 to do", page)
        self.assertIn("Conversation with the ORD captain", page)

    def test_what_a_captain_agent_decided_today_is_read_from_its_orders_and_events(self) -> None:
        now = talk.now()  # taken here: a suite that runs past midnight has a new today
        mine = talk.send(talk.place(self.run_dir, "ORD"), "say", "accent colour on every button")
        orders, events = self.run_dir / "orders/ORD", self.run_dir / "events/ORD"
        written(orders / "o1.json", {"v": 1, "id": "o1", "t": now, "verb": "message", "slice": "ORD-01",
                                     "text": "accent colour on every button", "of": mine["id"]})
        written(orders / "o1.result.json", {"result": "done"})
        written(orders / "o2.json", {"v": 1, "id": "o2", "t": now, "verb": "start", "slice": "ORD-09"})
        written(orders / "o2.result.json", {"result": "refused", "why": "ORD-09 has no clearance"})
        written(orders / "o3.json", {"v": 1, "id": "o3", "t": now, "verb": "say", "text": "I nudged ORD-01."})
        (orders / "broken.json").write_text("{not json", encoding="utf-8")
        written(events / "e1.json", {"v": 1, "id": "e1", "t": now, "kind": "stuck", "slice": "ORD-02"})
        written(events / "e1.closed.json", {"by": "rule", "why": "the captain was silent past its bound"})
        code, page = self.get("/captain-window?fairway=ORD")
        self.assertEqual(code, 200)
        self.assertNotIn("program alone", page)
        self.assertIn("Told ORD-01: accent colour on every button", page)
        self.assertIn("refused: ORD-09 has no clearance", page)
        self.assertIn("The rule decided stuck · ORD-02", page)
        self.assertIn("I nudged ORD-01.", page, "what the captain said to a person is in its conversation")
        self.assertIn("went to ORD-01", page, "beside the message, where its captain sent it")
        found = json.loads(self.get("/captain-window.json?fairway=ORD")[1])
        self.assertIn("Told ORD-01", found["decided"])
        self.assertEqual(found["heard"], 1)

    def test_a_stream_this_project_has_not_got_is_a_404(self) -> None:
        with self.assertRaises(Exception) as refused:
            self.get("/captain-window?fairway=NOPE")
        self.assertEqual(getattr(refused.exception, "code", None), 404)
        refused.exception.close()  # type: ignore[attr-defined]


class StripTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.deck("BIL", logs.entry("claimed", fairway="BIL", slice="BIL-01"))
        self.run_dir = logs.run_dir(self.root)

    def test_a_button_a_stream_says_its_slices_and_marks_a_captain_that_said_something_unseen(self) -> None:
        rows = [row("ORD-01", "working"), row("ORD-02", "working"), row("ORD-03", "queued"), row("ORD-04", "waiting")]
        drawn = strip_html(self.root, rows, {"ORD-04"})
        self.assertIn("Captain · ORD</b><span>2 at work · 1 queued · 1 waiting on you</span>", drawn)
        self.assertIn('href="/captain-window?fairway=BIL"', drawn)
        self.assertNotIn("· new", drawn)
        place = talk.place(self.run_dir, "ORD")
        sent = talk.send(place, "say", "status?")
        talk.note(place, "reply", to=sent["id"], text="All three are moving.")
        self.assertIn("Captain · ORD <i>· new</i>", strip_html(self.root, rows, set()))
        self.post("/talk/seen", {"fairway": "ORD", "slice": "", "heard": 1})
        self.assertNotIn("· new", strip_html(self.root, rows, set()))
        self.assertIn("Ask about this project", drawn)
        self.assertNotIn("harbourmaster", drawn.lower())

    def test_tell_every_captain_places_one_message_per_stream_and_says_where_each_went(self) -> None:
        code, said = self.post("/talk/all", {"message": "use the club accent colour"})
        self.assertEqual(code, 200, said)
        record = json.loads(said)
        self.assertEqual(sorted(record["ids"]), ["BIL", "ORD"])
        for fairway, ident in record["ids"].items():
            [sent] = talk.inbox(talk.place(self.run_dir, fairway))
            self.assertEqual((sent["id"], sent["text"], sent["from"]), (ident, "use the club accent colour", "person"))
        talk.send(talk.place(self.run_dir, "ORD", "ORD-01"), "say", "use the club accent colour", by="person",
                  via="captain:ORD", of=record["ids"]["ORD"])
        drawn = strip_html(self.root, [], set())
        self.assertIn("You told every captain:</b> use the club accent colour", drawn)
        self.assertIn("Captain · ORD · sent · the fleet is not running: read when it is cast off · went to ORD-01",
                      drawn)
        self.assertIn("Captain · BIL · sent · the fleet is not running", drawn)
        self.assertEqual(self.post("/talk/all", {"message": "  "})[0], 400)

    def test_a_long_tell_to_every_captain_is_kept_and_one_past_the_limit_is_refused_before_any_is_told(self) -> None:
        from slipwai.talk_said import told_all

        long = "the accent colour, said at length. " * 3000  # past the 64 KB the tail was once read in
        self.assertEqual(self.post("/talk/all", {"message": long})[0], 200)
        self.assertEqual([one["text"] for one in told_all(self.root)], [long.strip()])
        self.assertEqual(self.post("/talk/all", {"message": "and a short one"})[0], 200)
        self.assertEqual([one["text"] for one in told_all(self.root)], ["and a short one", long.strip()],
                         "the next tell keeps the long one")
        code, said = self.post("/talk/all", {"message": "x" * talk.LARGEST})
        self.assertEqual(code, 400, said)
        self.assertIn(f"{talk.LARGEST:,}", said)
        for fairway in ("BIL", "ORD"):
            self.assertEqual(len(talk.inbox(talk.place(self.run_dir, fairway))), 2, "no captain was told it")

    def test_turns_said_in_one_second_are_drawn_in_the_order_they_were_said(self) -> None:
        from slipwai.talk_fold import fold

        place = talk.place(self.run_dir, "ORD", "ORD-01")
        with mock.patch.object(talk, "now", return_value="2026-11-17T09:00:00Z"):
            for number in range(20):
                talk.send(place, "say", f"message {number}")
            talk.note(place, "ask", id="ask-1", what="question", text="first ask", options=[])
            talk.note(place, "paused", by="person", why="second note")
        drawn = [one["text"] for one in fold(place)["turns"]]
        self.assertEqual(drawn, [f"message {number}" for number in range(20)]
                         + ["first ask", "Paused by you: second note"])


class AskTest(unittest.TestCase):
    """A product question waits on a person only where the project says a person answers them."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        path = logs.deck_path(self.root, "ordering", "ORD")
        path.parent.mkdir(parents=True)
        path.write_text(logs.entry("claimed", fairway="ORD", slice="ORD-01").line(), encoding="utf-8")
        self.home = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")
        talk.note(self.home, "ask", id="ask-1", what="question", text="Remind everyone, or only the undecided?",
                  options=["everyone", "the undecided"])
        self.rows = [row("ORD-01", "working")]

    def listed(self) -> dict:
        return waiting(SimpleNamespace(root=self.root, fitting=None), {}, {}, self.rows)

    def cruise(self, **held: object) -> None:
        (self.root / ".specify").mkdir(exist_ok=True)
        (self.root / ".specify/cruise.json").write_text(json.dumps(held), encoding="utf-8")

    def test_where_a_person_answers_the_ask_is_a_card_and_holds_work_up(self) -> None:
        self.cruise(enabled=False)
        found = self.listed()
        self.assertEqual([one["text"] for one in found["holding"]],
                         ["ORD-01 asks: Remind everyone, or only the undecided?"])
        self.assertEqual(found["holding"][0]["href"], "/slice?fairway=ORD&slice=ORD-01#ask-ask-1")
        self.assertEqual(found["slices"], ["ORD-01"])
        log = payload(self.root, "ORD", "ORD-01")["log"]
        self.assertIn('data-ask="ask-1"', log)
        self.assertIn('data-ask-pick="the undecided"', log)
        self.assertIn("Waiting on you", log)

    def test_an_answer_is_a_message_naming_the_ask_and_it_leaves_the_list(self) -> None:
        self.cruise(enabled=False)
        talk.send(self.home, "say", "the undecided", of="ask-1")
        self.assertEqual(self.listed()["holding"], [])
        self.assertIn("Your answer: the undecided", payload(self.root, "ORD", "ORD-01")["log"])

    def test_where_the_skipper_answers_nothing_waits_and_its_answer_is_in_the_thread(self) -> None:
        self.cruise(enabled=True, decide="recommended-first")
        self.assertEqual(self.listed()["count"], 0)
        self.assertIn("This fleet is cruising, so it answers product questions itself",
                      payload(self.root, "ORD", "ORD-01")["log"])
        talk.note(self.home, "answer", to="ask-1", by="skipper", text="the undecided")
        self.assertIn("Answered by the skipper: the undecided", payload(self.root, "ORD", "ORD-01")["log"])


class PausedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.home = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")

    def later(self) -> list[str]:
        found = waiting(SimpleNamespace(root=self.root, fitting=None), {}, {}, [row("ORD-01", "queued")])
        return [one["text"] for one in found["later"]]

    def test_a_slice_a_person_paused_waits_until_they_have_time_and_so_does_one_its_captain_paused(self) -> None:
        # Decision 17a amends 11: no rule lifts a captain's pause, so a person has to see it.
        talk.note(self.home, "paused", by="captain:ORD", why="trunk is red")
        self.assertEqual(self.later(), ["ORD-01 is paused by captain:ORD, and no rule lifts it: resume it when you "
                                        "are ready"])
        talk.note(self.home, "resumed", by="captain:ORD")
        talk.note(self.home, "paused", by="person", why="lunch")
        self.assertEqual(self.later(), ["ORD-01 is paused by you: resume it when you are ready"])


if __name__ == "__main__":
    unittest.main()
