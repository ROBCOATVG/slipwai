"""The conversation routes, each held to one thing a review fixed, through the running board.

Every case here was a fix that could be undone with the suite still green: the body a browser sends with no
type, a board asked for on another port, a park's answer carrying its park through `/tell`, a receipt that
never says "told", a fleet that is running, each place a message can stand, a window's `limit`, a captain's
seen, and how many "Tell every captain" are kept. They are driven as a page drives them (`board_fixture`).
"""
from __future__ import annotations

import http.client
import json
import os
import threading
import unittest

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import logs, talk
from slipwai.captains_strip import strip_html
from slipwai.cli_fleet import config
from slipwai.fleet import board
from slipwai.on_you import streams_card
from slipwai.talk_said import KEEP_TOLD, told_all_path

PARKED = "2026-11-16T09:02:00Z"
NOT_RUNNING = "sent · the fleet is not running: read when it is cast off"


class GuardTest(BoardTest):
    def raw(self, headers: dict[str, str], body: bytes = b'{"message": "hi"}') -> int:
        held = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        held.request("POST", f"/talk/all?seat={self.seat}", body=body, headers=headers)
        code = held.getresponse().status
        held.close()
        return code

    def test_a_body_that_says_no_type_and_a_board_on_another_port_are_refused(self) -> None:
        own = f"http://127.0.0.1:{self.port}"
        self.assertEqual(self.raw({"Origin": own}), 403, "a body with no Content-Type is not the board's JSON")
        self.assertEqual(self.raw({}), 403, "nor from a script that says no origin")
        other = {"Content-Type": "application/json", "Host": f"127.0.0.1:{self.port + 1}"}
        self.assertEqual(self.raw(other), 403, "this board is not served on that port")
        self.assertEqual(talk.inbox(talk.place(logs.run_dir(self.root), "ORD")), [], "nothing was placed")
        self.assertEqual(self.raw({"Content-Type": "application/json; charset=utf-8", "Origin": own}), 200)


class ParkAnswerTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="ORD-01: the gate stayed red", t=PARKED))
        self.place = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")

    def row(self) -> dict:
        found = board(self.root, config(self.root))
        return next(one for one in found["inbox"] if one["kind"] == "parked")  # type: ignore[attr-defined]

    def tell(self, message: str, **more: str) -> tuple[int, str]:
        row = self.row()
        return self.post("/tell", {"fairway": "ORD", "slice": row["aim"], "of": row["key"], "message": message,
                                   **more})

    def test_a_park_s_answer_posted_from_its_row_carries_the_park_and_stands_on_the_row(self) -> None:
        code, said = self.tell("sorted, carry on")
        [first] = talk.inbox(self.place)
        self.assertEqual((code, said), (200, f"ORD-01: {NOT_RUNNING} · message {first['id']}"))
        self.assertEqual(first["of"], f"park:{PARKED}", "what the park's row finds its answer by")
        self.assertEqual(self.row()["answer"]["text"], "sorted, carry on")
        drawn = streams_card(board(self.root, config(self.root)))
        self.assertIn(f"<b>You said:</b> sorted, carry on</span><small class=\"wait\">{NOT_RUNNING}</small>", drawn)
        self.assertNotIn("data-tell-each", drawn, "said already: no second button beside it")

    def test_changing_a_park_s_answer_withdraws_the_first_and_an_answer_that_is_not_there_is_refused(self) -> None:
        self.tell("wait for me")
        [first] = talk.inbox(self.place)
        self.assertEqual(self.tell("carry on", replaces=first["id"])[0], 200)
        kinds = sorted((one["kind"], one.get("of", "")) for one in talk.inbox(self.place))
        self.assertEqual(kinds, [("say", f"park:{PARKED}"), ("say", f"park:{PARKED}"), ("withdraw", first["id"])])
        self.assertEqual(self.row()["answer"]["text"], "carry on")
        code, said = self.tell("again", replaces="20260101T000000Z-nobody")
        self.assertEqual(code, 400, said)
        self.assertIn("no answer 20260101T000000Z-nobody of yours to change", said)
        self.assertEqual(len(talk.inbox(self.place)), 3, "and nothing was placed for it")

    def test_an_answer_the_captain_has_read_cannot_be_changed_and_a_stranger_s_is_not_yours(self) -> None:
        self.deck("ORD", logs.entry("question", fairway="ORD", id="D13", slice="ORD-01", what="One context?"))
        talk.send(self.place, "say", "forged", by="session", of="question:D13")
        drawn = streams_card(board(self.root, config(self.root)))
        self.assertNotIn("Your answer", drawn, "only a person's own message is their answer")
        self.assertEqual(self.post("/tell", {"fairway": "ORD", "message": "One.", "question": "D13"})[0], 200)
        mine = next(one for one in talk.inbox(self.place) if one["text"] == "One.")
        drawn = streams_card(board(self.root, config(self.root)))
        self.assertIn(f'data-change-answer="tell-wait-0" data-replaces="{mine["id"]}">Change my answer', drawn)
        talk.note(self.place, "seen", id=mine["id"])
        drawn = streams_card(board(self.root, config(self.root)))
        self.assertIn("<b>Your answer:</b> One.", drawn)
        self.assertIn("read by the captain · delivered when the slice carries on", drawn)
        self.assertNotIn("Change my answer", drawn, "nothing takes back what has been read")


class ReceiptTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.deck("BIL", logs.entry("claimed", fairway="BIL", slice="BIL-01"))
        self.run_dir = logs.run_dir(self.root)

    def test_say_and_send_again_answer_where_the_message_stands_and_never_told(self) -> None:
        place = talk.place(self.run_dir, "ORD", "ORD-01")
        code, said = self.post("/talk/say", {"fairway": "ORD", "slice": "ORD-01", "text": "mind the rounding"})
        [sent] = talk.inbox(place)
        self.assertEqual((code, said), (200, f"ORD-01: {NOT_RUNNING} · message {sent['id']}"))
        talk.note(place, "failed", id=sent["id"], why="the agent ended before it answered")
        code, said = self.post("/talk/again", {"fairway": "ORD", "slice": "ORD-01", "id": sent["id"]})
        again = next(one for one in talk.inbox(place) if one["id"] != sent["id"])
        self.assertEqual((code, said), (200, f"ORD-01: {NOT_RUNNING} · message {again['id']}"))
        code, said = self.post("/talk/say", {"fairway": "ORD", "text": "status?"})
        self.assertEqual(code, 200)
        self.assertTrue(said.startswith(f"the ORD captain: {NOT_RUNNING}"), said)

    def test_with_the_fleet_running_a_message_waits_for_the_captain_s_next_turn(self) -> None:
        running = self.run_dir / "running"
        running.mkdir(parents=True, exist_ok=True)
        (running / "captain-ORD.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")  # alive: this process
        code, said = self.post("/talk/say", {"fairway": "ORD", "slice": "ORD-01", "text": "mind the rounding"})
        self.assertEqual(code, 200)
        self.assertIn("ORD-01: sent · the captain reads it at its next turn · message ", said)
        (running / "captain-ORD.pid").write_text("not a pid\n", encoding="utf-8")
        code, said = self.post("/talk/say", {"fairway": "ORD", "slice": "ORD-01", "text": "and the totals"})
        self.assertIn(NOT_RUNNING, said)

    def test_every_captain_s_copy_says_where_it_stands_as_it_moves(self) -> None:
        ids = json.loads(self.post("/talk/all", {"message": "use the club accent colour"})[1])["ids"]
        ord_home, bil_home = talk.place(self.run_dir, "ORD"), talk.place(self.run_dir, "BIL")
        talk.note(ord_home, "seen", id=ids["ORD"])
        talk.note(bil_home, "failed", id=ids["BIL"], why="its key was made again")
        drawn = strip_html(self.root, [], set())
        self.assertIn("Captain · ORD · read by the captain</span>", drawn, "no slice to carry on: the stream's own")
        self.assertIn("Captain · BIL · not delivered: its key was made again</span>", drawn)
        talk.note(ord_home, "delivered", id=ids["ORD"], mode="wait")
        self.assertIn("Captain · ORD · delivered</span>", strip_html(self.root, [], set()))
        ids = json.loads(self.post("/talk/all", {"message": "never mind"})[1])["ids"]
        talk.note(bil_home, "withdrawn", id=ids["BIL"])
        self.assertIn("Captain · BIL · withdrawn</span>", strip_html(self.root, [], set()))
        with told_all_path(self.root).open("a", encoding="utf-8") as held:
            held.write(json.dumps({"t": talk.now(), "text": "lost", "ids": {"ORD": "20260101T000000Z-nobody"}}) + "\n")
        self.assertIn("Captain · ORD · not found in its inbox</span>", strip_html(self.root, [], set()))

    def test_only_the_last_ten_tell_every_captain_are_kept(self) -> None:
        for number in range(KEEP_TOLD + 2):
            self.assertEqual(self.post("/talk/all", {"message": f"word {number}"})[0], 200)
        kept = [json.loads(line)["text"] for line in told_all_path(self.root).read_text(encoding="utf-8").splitlines()]
        self.assertEqual(kept, [f"word {number}" for number in range(2, KEEP_TOLD + 2)])

    def test_two_windows_telling_every_captain_at_once_lose_neither(self) -> None:
        codes: list[int] = []

        def tell(number: int) -> None:
            codes.append(self.post("/talk/all", {"message": f"word {number}"})[0])

        threads = [threading.Thread(target=tell, args=(n,)) for n in range(8)]
        for one in threads:
            one.start()
        for one in threads:
            one.join()
        self.assertEqual(codes, [200] * 8)
        kept = [json.loads(line)["text"] for line in told_all_path(self.root).read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sorted(kept), [f"word {n}" for n in range(8)])


class WindowRouteTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.run_dir = logs.run_dir(self.root)

    def test_a_window_s_poll_and_a_captain_s_draw_the_newest_turns_the_limit_asks_for(self) -> None:
        for home in (talk.place(self.run_dir, "ORD", "ORD-01"), talk.place(self.run_dir, "ORD")):
            for number in range(5):
                talk.send(home, "say", f"message {number}")
        for path in ("/talk.json?fairway=ORD&slice=ORD-01", "/captain-window.json?fairway=ORD"):
            log = json.loads(self.get(path)[1])["log"]
            self.assertEqual(log.count('<div class="said"'), 5, path)
            log = json.loads(self.get(f"{path}&limit=2")[1])["log"]
            self.assertEqual(log.count('<div class="said"'), 2, path)
            self.assertIn("Show 3 earlier</button> of 3 not shown", log)
            self.assertEqual(json.loads(self.get(f"{path}&limit=many")[1])["log"].count('<div class="said"'), 5)

    def test_a_captain_s_seen_counts_its_own_words_and_is_never_past_them(self) -> None:
        orders = self.run_dir / "orders/ORD"
        orders.mkdir(parents=True)
        said = {"v": 1, "id": "o1", "t": talk.now(), "verb": "say", "text": "I nudged ORD-01."}
        (orders / "o1.json").write_text(json.dumps(said), encoding="utf-8")
        self.assertEqual(self.post("/talk/seen", {"fairway": "ORD", "slice": "", "heard": 10**12}), (200, "1"))
        place = talk.place(self.run_dir, "ORD")
        talk.note(place, "unaddressed", id="x")
        self.assertEqual(self.post("/talk/seen", {"fairway": "ORD", "slice": "", "heard": 10**12}), (200, "2"))


if __name__ == "__main__":
    unittest.main()
