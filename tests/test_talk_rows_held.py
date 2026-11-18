"""What a placed message looks like where a person meets it, each held to one thing a review fixed.

A waiting message says what it will meet where its slice now is; a parked slice's card shows the answer in
place of its box; a group answered says what was said, and one half answered still has its button; and the
rows and scripts carry the slice, the park and the answer replaced. The board is read as its pages read it.
"""
from __future__ import annotations

import html
import json
import re
import unittest
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import board_read, bridge_page, fleet_page, logs, talk, talk_marks, talk_page, voyage_page
from slipwai.cli_fleet import config
from slipwai.fleet import board
from slipwai.fleet_page import group_card
from slipwai.on_you import streams_card
from slipwai.slice_card import lit, slice_html
from slipwai.talk_fold import WHERE

PARKED = "2026-11-16T09:02:00Z"


def row(state: str) -> dict[str, str]:
    return {"slice": "ORD-01", "title": "", "state": state, "fairway": "ORD", "feature": "ordering", "why": ""}


class WhereTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.place = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")

    def said(self, state: str, ident: str) -> str:
        kept = board_read.Read([row(state)], "", {}, {}, {}, [], {})
        with mock.patch("slipwai.talk_page.read", return_value=kept):
            drawn = json.loads(self.get("/talk.json?fairway=ORD&slice=ORD-01")[1])["log"]
        return html.unescape(drawn[drawn.index(f'id="m-{ident}"'):].split('<div class="said"', 1)[0])

    def test_a_waiting_message_says_what_it_will_meet_where_its_slice_now_is(self) -> None:
        sent = talk.send(self.place, "say", "use the blue header")
        for state in ("waiting", "done", "queued", "todo"):
            self.assertIn(WHERE[state], self.said(state, sent["id"]), state)
        self.assertIn("it is parked: its captain takes a person's message as the answer", WHERE["waiting"])
        self.assertIn("this slice has merged, so it will not be delivered", WHERE["done"])
        self.assertIn("Queued · goes in when its current turn ends", self.said("working", sent["id"]))

    def test_a_held_message_and_a_pause_keep_their_own_words_on_a_parked_slice(self) -> None:
        kept = talk.send(self.place, "say", "one more thing")
        talk.note(self.place, "held", id=kept["id"], why="held: this slice is at its merge")
        pause = talk.send(self.place, "pause", "lunch")
        self.assertIn("this slice is at its merge", self.said("waiting", kept["id"]))
        self.assertNotIn("it is parked", self.said("waiting", kept["id"]))
        self.assertNotIn("it is parked", self.said("waiting", pause["id"]), "a pause is not an answer to a park")

    def test_a_question_waits_on_a_person_because_the_run_is_not_cruising(self) -> None:
        (self.root / ".specify").mkdir()
        (self.root / ".specify/cruise.json").write_text(json.dumps({"enabled": False}), encoding="utf-8")
        talk.note(self.place, "ask", id="ask-1", what="question", text="Everyone, or only the undecided?")
        drawn = json.loads(self.get("/talk.json?fairway=ORD&slice=ORD-01")[1])["log"]
        self.assertIn("Waiting on you: this run is not cruising, so a person answers its product questions.", drawn)


class ParkedCardTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.place = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")

    def card(self) -> str:
        [found] = lit([row("waiting")], {}, self.root)
        return slice_html(found)

    def test_a_parked_slice_s_card_shows_the_answer_sent_in_place_of_its_box(self) -> None:
        talk.send(self.place, "say", "from its session", by="session")
        talk.send(self.place, "pause", "lunch")
        card = self.card()
        self.assertNotIn("Your answer:", card, "a session's words and a pause are not a person's answer")
        self.assertIn('<div class="ask"><textarea id="answer-ORD-01"', card)
        code, _ = self.post("/tell", {"fairway": "ORD", "slice": "ORD-01", "message": "one context"})
        self.assertEqual(code, 200)
        mine = next(one for one in talk.inbox(self.place) if one["text"] == "one context")
        card = self.card()
        self.assertIn("<b>Your answer:</b> one context", card)
        self.assertIn(html.escape(WHERE["waiting"]), card, "said as what it meets on a parked slice")
        self.assertIn(f'data-change-answer="answer-ORD-01" data-replaces="{mine["id"]}">Change my answer', card)
        self.assertIn('<div class="ask" hidden><textarea id="answer-ORD-01"', card, "the box only behind Change")
        talk.note(self.place, "seen", id=mine["id"])
        talk.note(self.place, "delivered", id=mine["id"], mode="wait")
        self.assertNotIn("Your answer:", self.card(), "delivered: it is no longer an answer waiting")


class GroupTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.deck("BIL", logs.entry("claimed", fairway="BIL", slice="BIL-01"))
        for fairway in ("ORD", "BIL"):
            self.deck(fairway, logs.entry("parked", fairway=fairway, cause="trunk", t=PARKED,
                                          why=f"{fairway}-01: trunk is red"))

    def group(self) -> dict:
        found: list[dict] = board(self.root, config(self.root))["groups"]  # type: ignore[assignment]
        self.assertEqual(len(found), 1, "two streams parked on the one red trunk are one group")
        return found[0]

    def parks(self, card: str) -> list[dict]:
        found = re.search(r"data-tell-each='([^']*)'", card)
        assert found is not None, card
        return json.loads(html.unescape(found.group(1)))

    def test_a_group_s_button_aims_each_park_at_its_slice_and_one_half_answered_keeps_it(self) -> None:
        sent = self.parks(group_card(self.group(), controls=True))
        self.assertEqual(sorted((one["fairway"], one["slice"], one["aim"], one["key"]) for one in sent),
                         [("BIL", "", "BIL-01", f"park:{PARKED}"), ("ORD", "", "ORD-01", f"park:{PARKED}")])
        for number, park in enumerate(sorted(sent, key=lambda one: one["fairway"], reverse=True)):
            code, said = self.post("/tell", {"fairway": park["fairway"], "slice": park["aim"], "of": park["key"],
                                             "message": "sorted, carry on"})
            self.assertEqual(code, 200, said)
            card = group_card(self.group(), controls=True)
            if number == 0:
                self.assertIn("data-tell-each", card, "one park of two answered: the group still has its button")
                self.assertNotIn("You said:", card)
        self.assertIn("<b>You said:</b> sorted, carry on", card)
        self.assertNotIn("data-tell-each", card)
        self.assertNotIn("You said:", group_card(self.group(), controls=False), "a read-only copy offers neither")


class RowTest(BoardTest):
    def test_a_question_s_row_carries_the_slice_and_what_its_answer_answers(self) -> None:
        self.deck("ORD", logs.entry("question", fairway="ORD", id="D13", slice="ORD-01", what="One context?"))
        drawn = streams_card(board(self.root, config(self.root)))
        self.assertIn('data-question="D13" data-slice="ORD-01" data-of="question:D13">Send</button>', drawn)
        self.assertIn("<h3>Talk to a stream's captain</h3>", drawn)
        self.assertIn('<a href="/captain-window?fairway=ORD"', drawn)
        self.assertNotIn("Say something to a stream", drawn + self.rendered(), "a stream is talked to in its window")
        self.assertIn('<h2>Talk to a stream\'s captain</h2><p><a href="/captain-window?fairway=ORD"', self.rendered())
        self.assertNotIn('data-tell="ORD">Send', self.rendered(), "no box that wrote to a stream nobody read")

    def test_a_hand_back_with_needs_is_answered_as_a_park_and_the_answer_stands_on_its_row(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", slice="ORD-01", by="session", t=PARKED,
                                    message="a person lands the migration",
                                    needs=[{"what": "the migration is on trunk", "by": "person"}]))
        drawn = streams_card(board(self.root, config(self.root)))
        self.assertIn(f'data-slice="ORD-01" data-of="park:{PARKED}">Send</button>', drawn)
        code, said = self.post("/tell", {"fairway": "ORD", "slice": "ORD-01", "of": f"park:{PARKED}",
                                         "message": "landed at 4e150b8"})
        self.assertEqual(code, 200, said)
        self.assertIn("<b>Your answer:</b> landed at 4e150b8", streams_card(board(self.root, config(self.root))))

    def test_the_pages_scripts_send_the_slice_the_park_and_the_answer_replaced(self) -> None:
        self.assertIn("slice: say.dataset.slice || '', of: say.dataset.of || '', replaces: say.dataset.replaces "
                      "|| '',", bridge_page.SCRIPT)
        self.assertIn("slice: park.aim || park.slice, of: park.key || '',", fleet_page.SCRIPT)
        self.assertIn("replaces: event.target.dataset.replaces || ''", voyage_page.SCRIPT)
        self.assertIn("one.dataset.replaces = change.dataset.replaces;", talk_marks.SCRIPT)
        self.assertIn("row.hidden = false;", talk_marks.SCRIPT)
        self.assertIn(talk_marks.SCRIPT, fleet_page.SCRIPT, "Change my answer is on the page the rows are on")

    def test_show_earlier_asks_the_poll_for_more_and_the_poll_is_read_each_time(self) -> None:
        self.assertIn("if (event.target.closest('[data-talk-earlier]')) {", talk_page.SCRIPT)
        self.assertIn("url.searchParams.set('limit', String(Number(url.searchParams.get('limit') || 200) + 200));",
                      talk_page.SCRIPT)
        self.assertIn("talk.dataset.poll = url.pathname + url.search;", talk_page.SCRIPT)
        self.assertIn("await fetch(talk.dataset.poll)", talk_page.SCRIPT, "not an address kept from the first draw")


if __name__ == "__main__":
    unittest.main()
