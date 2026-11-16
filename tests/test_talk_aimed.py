"""Talking to the fleet, held to what it promised: aimed at what it is about, honest about where it stands.

A message is aimed at the slice a park or a question is about, even where the park's own `slice` is empty;
a row with an answer placed shows the answer and where it stands, never a second box; nothing says "told"
for something nothing has read. And only the board's own pages may post to it. The whole-stream cases are
driven board to captain through the project's own `captain.py` (`captain_fixture`).
"""
from __future__ import annotations

import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest
from captain_fixture import WORKS, Fixture

from slipwai import logs, talk
from slipwai.cli_fleet import config
from slipwai.fleet import board
from slipwai.on_you import streams_card
from slipwai.talk_fold import see, seen, turns
from slipwai.talk_page import payload
from slipwai.talk_said import tell

PARKED = "2026-11-16T09:02:00Z"


class WholeStreamParkTest(Fixture):
    def setUp(self) -> None:
        super().setUp()
        self.fake = self.sail(WORKS)

    def row(self) -> dict:
        found = board(self.root, config(self.root))
        return next(one for one in found["inbox"] if one["kind"] == "parked")  # type: ignore[attr-defined]

    def test_a_park_with_no_slice_field_is_answered_at_the_slice_its_why_names(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t="2026-11-16T09:00:00Z"),
                  logs.entry("parked", fairway="ORD", why="ORD-01: the gate stayed red", t=PARKED))
        row = self.row()
        self.assertEqual((row["aim"], row["key"]), ("ORD-01", f"park:{PARKED}"))
        said = tell(self.root, "ORD", "sorted, carry on", row["aim"], of=row["key"])
        self.assertIn("ORD-01: sent · the fleet is not running", said)
        self.assertEqual(self.row()["answer"]["text"], "sorted, carry on")
        self.assertTrue(self.row()["answer"]["changeable"])
        done = self.captain("ORD", self.fake)
        told = [e for e in self.read("ORD") if e.kind == "told"]
        self.assertEqual([e.fields["message"] for e in told], ["sorted, carry on"], done.stdout)
        answer = self.row()["answer"]
        self.assertEqual(answer["line"], "read by the captain · delivered when the slice carries on")
        self.assertFalse(answer["changeable"], "a told is written: nothing can take it back now")

    # Waits for the captain stream's fix: the captain program reading its own inbox where there is no captain
    # agent, and a person's message clearing a park that names no slice. Until then nothing reads `_captain`.
    @unittest.expectedFailure
    def test_an_unaimed_group_button_reaches_the_captain_which_answers_the_stream_s_park(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t="2026-11-16T09:00:00Z"),
                  logs.entry("parked", fairway="ORD", why="the chart needs a person", t=PARKED))
        row = self.row()
        self.assertEqual(row["aim"], "", "about the whole stream: its captain's")
        tell(self.root, "ORD", "sorted, carry on", "", of=row["key"])
        done = self.captain("ORD", self.fake)
        self.assertEqual([e.fields["message"] for e in self.read("ORD") if e.kind == "told"],
                         ["sorted, carry on"], done.stdout)


class AnsweredRowTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.deck("ORD", logs.entry("question", fairway="ORD", id="D13", slice="ORD-01", what="One context?"))

    def streams(self) -> str:
        return streams_card(board(self.root, config(self.root)))

    def test_an_answer_with_no_captain_lit_is_shown_with_where_it_stands_and_no_second_box(self) -> None:
        code, said = self.post("/tell", {"fairway": "ORD", "message": "Yes, one context.", "question": "D13"})
        self.assertEqual(code, 200, said)
        self.assertNotIn("told", said)
        drawn = self.streams()
        self.assertIn("<b>Your answer:</b> Yes, one context.", drawn)
        self.assertIn("the fleet is not running: read when it is cast off", drawn)
        self.assertIn("Change my answer", drawn)
        self.assertIn('<div class="ask" hidden><input id="tell-wait-', drawn, "the box only behind Change")

    def test_changing_an_answer_withdraws_the_first_and_a_double_answer_is_one_answer(self) -> None:
        self.post("/tell", {"fairway": "ORD", "message": "Two contexts.", "question": "D13"})
        place = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")
        [first] = talk.inbox(place)
        code, said = self.post("/tell", {"fairway": "ORD", "message": "One context.", "question": "D13",
                                         "replaces": first["id"]})
        self.assertEqual(code, 200, said)
        kinds = sorted((one["kind"], one.get("of", "")) for one in talk.inbox(place))
        self.assertEqual(kinds, [("say", "question:D13"), ("say", "question:D13"), ("withdraw", first["id"])])
        drawn = self.streams()
        self.assertIn("<b>Your answer:</b> One context.", drawn)
        self.assertNotIn("Two contexts.", drawn)
        stranger = talk.send(place, "say", "from a session", by="session")
        self.assertEqual(self.post("/tell", {"fairway": "ORD", "message": "x", "question": "D13",
                                             "replaces": stranger["id"]})[0], 400)


class CrossSiteTest(BoardTest):
    def raw(self, headers: dict[str, str], body: bytes = b'{"message": "hi"}') -> int:
        held = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        held.request("POST", f"/talk/all?seat={self.seat}", body=body, headers=headers)
        code = held.getresponse().status
        held.close()
        return code

    def test_only_the_board_s_own_pages_may_post_and_a_local_script_still_may(self) -> None:
        own = f"http://127.0.0.1:{self.port}"
        json_type = {"Content-Type": "application/json"}
        self.assertEqual(self.raw({**json_type, "Origin": "http://evil.example"}), 403)
        self.assertEqual(self.raw({**json_type, "Origin": "null"}), 403)
        self.assertEqual(self.raw({**json_type, "Referer": "http://evil.example/page"}), 403)
        self.assertEqual(self.raw({"Content-Type": "text/plain", "Origin": own}), 403, "a simple cross-site post")
        self.assertEqual(self.raw({"Content-Type": "application/x-www-form-urlencoded"}, b"message=hi"), 403)
        self.assertEqual(self.raw({**json_type, "Host": f"rebound.example:{self.port}"}), 403)
        self.assertEqual(talk.inbox(talk.place(logs.run_dir(self.root), "ORD")), [], "nothing was placed")
        self.assertEqual(self.raw({**json_type, "Origin": own}), 200, "the board's own page")
        self.assertEqual(self.raw(json_type), 200, "a script on this machine says no origin")


class CaptainFilesTest(BoardTest):
    def test_an_order_whose_words_look_like_a_template_does_not_take_the_window_down(self) -> None:
        orders = logs.run_dir(self.root) / "orders/ORD"
        orders.mkdir(parents=True)
        for ident, verb in (("o1", "{slice}{0}"), ("o2", "{nope}"), ("o3", "start")):
            (orders / f"{ident}.json").write_text(json.dumps({"id": ident, "t": talk.now(), "verb": verb,
                                                              "slice": "{0}"}), encoding="utf-8")
        (orders / "o4.json").write_text("[1, 2", encoding="utf-8")
        code, page = self.get("/captain-window?fairway=ORD")
        self.assertEqual(code, 200)
        self.assertIn("{slice}{0}", page)
        self.assertIn("Started {0}", page)


class LongThreadTest(unittest.TestCase):
    def test_a_long_thread_is_folded_once_and_a_window_draws_its_newest_turns(self) -> None:
        root = Path(tempfile.mkdtemp())
        path = logs.deck_path(root, "ordering", "ORD")
        path.parent.mkdir(parents=True)
        path.write_text(logs.entry("claimed", fairway="ORD", slice="ORD-01").line(), encoding="utf-8")
        place = talk.place(logs.run_dir(root), "ORD", "ORD-01")
        for number in range(450):
            talk.send(place, "say", f"message {number}")
        first = turns(place)
        started = time.monotonic()
        self.assertIs(turns(place), first, "unchanged files: the fold kept, not made again")
        self.assertLess(time.monotonic() - started, 0.05)
        found = payload(root, "ORD", "ORD-01")
        self.assertEqual(found["log"].count('<div class="said"'), 200)
        self.assertIn("Show 200 earlier</button> of 250 not shown", found["log"])
        self.assertEqual(payload(root, "ORD", "ORD-01", limit=400)["log"].count('<div class="said"'), 400)
        talk.send(place, "say", "one more")
        self.assertIsNot(turns(place), first, "a new message is read")


class SeenTest(unittest.TestCase):
    def test_two_windows_writing_seen_at_once_lose_nothing(self) -> None:
        root = Path(tempfile.mkdtemp())
        (root / ".slipwai").mkdir()
        threads = [threading.Thread(target=see, args=(root, "ORD", f"ORD-0{n % 4}", n)) for n in range(40)]
        for one in threads:
            one.start()
        for one in threads:
            one.join()
        self.assertEqual(seen(root), {f"ORD/ORD-0{k}": max(n for n in range(40) if n % 4 == k) for k in range(4)})


if __name__ == "__main__":
    unittest.main()
