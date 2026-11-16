"""Talking to the fleet from the board: a slice's conversation in its window, and what its card carries.

Every thread here is written the way the fleet writes one — messages through `talk.send`, the driver's facts
through `talk.note` — and read back through what the window draws, so a receipt in words is the receipt the
files hold. The routes are driven against `board_fixture`.
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import logs, talk
from slipwai.slice_card import lit, slice_html
from slipwai.talk_fold import see, seen
from slipwai.talk_page import SCRIPT, pane, payload


def project() -> Path:
    root = Path(tempfile.mkdtemp())
    path = logs.deck_path(root, "ordering", "ORD")
    path.parent.mkdir(parents=True)
    path.write_text(logs.entry("claimed", fairway="ORD", slice="ORD-01").line(), encoding="utf-8")
    return root


def home(root: Path, slice_id: str = "ORD-01") -> Path:
    return talk.place(logs.run_dir(root), "ORD", slice_id)


def opened(place: Path) -> None:
    """The driver held open: a session it opened, as the thread says it."""
    talk.note(place, "session", id="s-1", loaded=False)


def delivered(place: Path, ident: str, mode: str = "wait") -> None:
    talk.note(place, "seen", id=ident)
    talk.note(place, "delivered", id=ident, mode=mode)
    talk.note(place, "turn", state="started", about=ident)


class ReceiptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = project()
        self.home = home(self.root)
        opened(self.home)

    def said(self, ident: str) -> str:
        drawn = payload(self.root, "ORD", "ORD-01")["log"]
        return drawn[drawn.index(f'id="m-{ident}"'):].split('<div class="said"', 1)[0]

    def test_every_receipt_state_is_said_in_words(self) -> None:
        waiting = talk.send(self.home, "say", "use the blue header")
        answered = talk.send(self.home, "say", "mind the rounding")
        delivered(self.home, answered["id"])
        talk.note(self.home, "reply", to=answered["id"], text="Rounded half-even now.")
        quiet = talk.send(self.home, "say", "fyi")
        delivered(self.home, quiet["id"])
        talk.note(self.home, "unaddressed", id=quiet["id"])
        lost = talk.send(self.home, "say", "are you there?")
        talk.note(self.home, "failed", id=lost["id"], why="the session ended before its turn did")
        gone = talk.send(self.home, "say", "never mind")
        talk.note(self.home, "withdrawn", id=gone["id"])
        given = talk.send(self.home, "say", "now")
        delivered(self.home, given["id"])
        self.assertIn("Queued · goes in when its current turn ends", self.said(waiting["id"]))
        self.assertIn("Interrupt now", self.said(waiting["id"]))
        self.assertIn("Withdraw", self.said(waiting["id"]))
        self.assertIn("Answered", self.said(answered["id"]))
        self.assertIn("Rounded half-even now.", self.said(answered["id"]))
        self.assertIn("Delivered", self.said(quiet["id"]))
        self.assertIn("not addressed", self.said(quiet["id"]))
        self.assertIn("Not delivered: the session ended before its turn did", self.said(lost["id"]))
        self.assertIn("Send again", self.said(lost["id"]))
        self.assertIn("Withdrawn", self.said(gone["id"]))
        self.assertRegex(self.said(given["id"]), r"Delivered \d\d:\d\d")
        self.assertNotIn("Withdraw<", self.said(given["id"]), "a delivered message cannot be taken back")

    def test_a_message_to_a_slice_at_its_merge_is_shown_as_held(self) -> None:
        sent = talk.send(self.home, "say", "one more thing")
        talk.note(self.home, "held", id=sent["id"], why="held: this slice is at its merge")
        self.assertIn("Held: this slice is at its merge", self.said(sent["id"]))

    def test_a_message_a_captain_routed_is_from_the_person_through_that_captain(self) -> None:
        mine = talk.send(home(self.root, talk.CAPTAIN), "say", "accent colour everywhere")
        talk.send(self.home, "say", "accent colour everywhere", by="person", via="captain:ORD", of=mine["id"])
        self.assertIn("You, through the ORD captain", payload(self.root, "ORD", "ORD-01")["log"])

    def test_a_pause_says_who_made_it_and_what_resume_does(self) -> None:
        talk.note(self.home, "paused", by="captain:ORD", why="trunk is red")
        found = payload(self.root, "ORD", "ORD-01")
        self.assertIn("Paused by its ORD captain: trunk is red", found["log"])
        self.assertIn("Paused by its ORD captain: trunk is red.", found["state"])
        self.assertIn('data-talk-steer="resume"', found["state"])
        talk.note(self.home, "resumed", by="captain:ORD")
        talk.note(self.home, "stopped", by="person", why="wrong approach")
        state = payload(self.root, "ORD", "ORD-01")["state"]
        self.assertIn("Stopped by you: wrong approach.", state)
        self.assertIn("starts in a fresh session", state)
        self.assertNotIn('data-talk-steer="pause"', state)

    def test_every_value_that_reaches_the_page_is_escaped(self) -> None:
        sent = talk.send(self.home, "say", '<script>alert("typed")</script>')
        delivered(self.home, sent["id"])
        talk.note(self.home, "reply", to=sent["id"], text="<img src=x onerror=alert(1)>")
        talk.note(self.home, "ask", id="ask-1", what="question", text="<b>which</b>?", options=['"><i>'])
        drawn = pane(self.root, "ORD", "ORD-01", "/talk.json?x=<y>")
        for raw in ("<script>alert", "<img src=x", "<b>which</b>", '"><i>', "x=<y>"):
            self.assertNotIn(raw, drawn)
        self.assertIn("&lt;script&gt;alert(&quot;typed&quot;)&lt;/script&gt;", drawn)


class PrintModeTest(unittest.TestCase):
    def test_print_mode_offers_no_interrupt_and_says_why(self) -> None:
        root = project()
        place = home(root)
        first = talk.send(place, "say", "mind the rounding")
        talk.note(place, "seen", id=first["id"])
        talk.note(place, "delivered", id=first["id"], mode="wait")  # in the prompt: no turn follows it
        waiting = talk.send(place, "say", "and the totals")
        found = payload(root, "ORD", "ORD-01")
        self.assertEqual(found["how"], "print")
        self.assertNotIn("Interrupt now", found["log"])
        self.assertIn("Queued · goes in when the captain next starts it; if it merges first, it is not delivered",
                      found["log"])
        drawn = pane(root, "ORD", "ORD-01", "/talk.json")
        self.assertIn('data-how="print"', drawn)
        self.assertIn("No Interrupt: this slice runs in print mode", drawn)
        self.assertIn(f'id="m-{waiting["id"]}"', drawn)

    def test_a_thread_that_says_neither_yet_offers_no_interrupt(self) -> None:
        root = project()
        talk.send(home(root), "say", "hello")
        self.assertEqual(payload(root, "ORD", "ORD-01")["how"], "")


class PollTest(unittest.TestCase):
    def test_the_poll_swaps_only_the_turns_and_the_controls_and_never_the_box(self) -> None:
        root = project()
        drawn = pane(root, "ORD", "ORD-01", "/talk.json")
        log = re.search(r'<div class="talk-log[^>]*>.*?</div>(?=<div class="box")', drawn, re.S)
        assert log is not None
        self.assertNotIn("data-talk-text", log.group(0), "what is typed is never inside what is swapped")
        self.assertLess(drawn.index("data-talk-text"), drawn.index("data-talk-state"))
        state = drawn[drawn.index("data-talk-state"):]
        self.assertNotIn("data-talk-text", state)

    def test_a_region_someone_is_typing_in_or_has_focused_is_not_swapped_and_its_scroll_is_kept(self) -> None:
        self.assertIn("one === document.activeElement || (one.value || '').trim()", SCRIPT)
        self.assertIn("if (!region || region.dataset.said === said || busy(region)) return;", SCRIPT)
        self.assertIn("region.scrollTop = atFoot ? region.scrollHeight : top;", SCRIPT)
        self.assertIn("if (open.has(one.id)) one.open = true;", SCRIPT)


class CardTest(unittest.TestCase):
    def row(self, state: str = "working") -> dict[str, str]:
        return {"slice": "ORD-01", "title": "", "state": state, "fairway": "ORD", "feature": "ordering", "why": ""}

    def test_a_card_carries_a_marker_and_the_last_thing_said_until_its_window_has_shown_it(self) -> None:
        root = project()
        place = home(root)
        opened(place)
        sent = talk.send(place, "say", "mind the rounding")
        delivered(place, sent["id"])
        talk.note(place, "reply", to=sent["id"], text="Done, half-even.")
        [row] = lit([self.row()], {}, root)
        card = slice_html(row)
        self.assertIn('<span class="talk-new"><b>New · </b>Reply: Done, half-even.</span>', card)
        self.assertIn("Open its window", card)
        self.assertIn('data-quick="ORD-01"', card)
        heard = payload(root, "ORD", "ORD-01")["heard"]
        self.assertEqual(heard, 1)
        see(root, "ORD", "ORD-01", heard)
        self.assertEqual(seen(root), {"ORD/ORD-01": 1})
        self.assertTrue((logs.run_dir(root) / "board" / "seen.json").is_file(), "under the run folder, per project")
        [row] = lit([self.row()], {}, root)
        self.assertNotIn("talk-new", slice_html(row))
        self.assertIn("Done, half-even.", slice_html(row), "the last word stays in the opened card")

    def test_a_merged_slice_offers_no_quick_send(self) -> None:
        root = project()
        talk.send(home(root), "say", "hello")
        [row] = lit([self.row("done")], {}, root)
        self.assertNotIn("data-quick", slice_html(row))


class RouteTest(BoardTest):
    def inbox(self, slice_id: str = "ORD-01") -> list[dict]:
        return talk.inbox(talk.place(logs.run_dir(self.root), "ORD", slice_id))

    def test_send_interrupt_withdraw_pause_resume_and_stop_each_place_the_right_signed_message(self) -> None:
        place = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")
        for body in ({"text": "after this turn"}, {"text": "right now", "mode": "interrupt"}):
            code, said = self.post("/talk/say", {"fairway": "ORD", "slice": "ORD-01", **body})
            self.assertEqual(code, 200, said)
        queued = next(one for one in self.inbox() if one["text"] == "after this turn")
        code, said = self.post("/talk/interrupt", {"fairway": "ORD", "slice": "ORD-01", "id": queued["id"]})
        self.assertEqual(code, 200, said)
        for kind in ("pause", "resume", "stop"):
            code, said = self.post("/talk/steer", {"fairway": "ORD", "slice": "ORD-01", "kind": kind, "why": "lunch"})
            self.assertEqual(code, 200, said)
        shape = sorted((one["kind"], one["mode"], one.get("of", ""), one["text"]) for one in self.inbox())
        self.assertEqual(shape, sorted([("say", "wait", "", "after this turn"), ("say", "interrupt", "", "right now"),
                                 ("withdraw", "wait", queued["id"], ""), ("say", "interrupt", "", "after this turn"),
                                 ("pause", "wait", "", "lunch"), ("resume", "wait", "", "lunch"),
                                        ("stop", "wait", "", "lunch")]))
        self.assertTrue(all(one["from"] == "person" and talk.genuine(place, one) for one in self.inbox()))
        self.assertEqual([e for e in self.read("ORD") if e.kind == "told"], [], "and no deck line for any of it")

    def test_send_again_places_the_same_words_and_a_wrong_kind_is_refused(self) -> None:
        place = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")
        lost = talk.send(place, "say", "are you there?")
        talk.note(place, "failed", id=lost["id"], why="the agent ended before it answered")
        self.assertEqual(self.post("/talk/again", {"fairway": "ORD", "slice": "ORD-01", "id": lost["id"]})[0], 200)
        self.assertEqual([one["text"] for one in self.inbox()], ["are you there?", "are you there?"])
        self.assertEqual(self.post("/talk/steer", {"fairway": "ORD", "slice": "ORD-01", "kind": "say"})[0], 400)
        self.assertEqual(self.post("/talk/say", {"fairway": "NOPE", "slice": "X", "text": "hi"})[0], 400)

    def test_the_window_draws_the_conversation_beside_its_tabs_and_its_poll_answers(self) -> None:
        talk.send(talk.place(logs.run_dir(self.root), "ORD", "ORD-01"), "say", "hello there")
        code, page = self.get("/slice?fairway=ORD&slice=ORD-01")
        self.assertEqual(code, 200)
        self.assertIn('<div class="slice-win"><div class="tabbed">', page)
        self.assertIn("Conversation with ORD-01", page)
        self.assertIn("hello there", page)
        code, said = self.get("/talk.json?fairway=ORD&slice=ORD-01")
        found = json.loads(said)
        self.assertEqual(set(found), {"log", "log_said", "state", "state_said", "how", "heard"})
        self.assertEqual(self.post("/talk/seen", {"fairway": "ORD", "slice": "ORD-01", "heard": 3}), (200, "0"),
                         "never more than the thread holds")
        place = talk.place(logs.run_dir(self.root), "ORD", "ORD-01")
        talk.note(place, "unaddressed", id="x")
        self.assertEqual(self.post("/talk/seen", {"fairway": "ORD", "slice": "ORD-01", "heard": 10**12}), (200, "1"))
        self.assertEqual(seen(self.root), {"ORD/ORD-01": 1})


if __name__ == "__main__":
    unittest.main()
