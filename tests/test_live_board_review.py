"""What the review of the live board changed that nothing held: each case here goes red with its fix undone.

A park that names no slice, the model card that says when its strokes are out of date, the reload that
waits for anything somebody has typed, and a person's action dropping the kept read before its answer is
sent rather than after. `test_live_board_read` holds the rest of that review.
"""
from __future__ import annotations

import json
import re
import unittest
from unittest import mock

import checkout_packages  # noqa: F401
from board_fixture import BoardTest

from slipwai import board_read, bridge, logs
from slipwai.voyage_page import SCRIPT, model_card, model_said

DRAWIO = ('<mxfile host="app.diagrams.net"><diagram id="d" name="model"><mxGraphModel><root>'
          '<mxCell id="0"/><mxCell id="1" parent="0"/>'
          '<mxCell id="c-slice-Join" value="Join" style="rounded=1;" vertex="1" parent="1"/>'
          '</root></mxGraphModel></diagram></mxfile>')


class StreamParkTest(BoardTest):
    def test_a_park_that_names_no_slice_and_has_no_row_is_still_waiting_on_you(self) -> None:
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="Which owner? It matters."))
        found = json.loads(self.get("/live.json")[1])["waiting"]
        self.assertEqual(found["count"], 1)
        self.assertEqual(found["holding"][0]["text"], "The ORD stream: Which owner? It matters")
        self.assertEqual(found["holding"][0]["href"], "#from-streams")


class ModelOutOfDateTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "docs/event-model").mkdir(parents=True)
        (self.root / "docs/event-model/model.drawio").write_text(DRAWIO, encoding="utf-8")

    def test_the_page_and_the_poll_say_the_same_of_a_model_nothing_has_moved_under(self) -> None:
        drawn = re.search(r'data-model-said="([0-9a-f]+)"', self.get("/voyage")[1])
        assert drawn is not None, "the model card says what its strokes were drawn from"
        self.assertEqual(json.loads(self.get("/live.json")[1])["model"], drawn.group(1))

    def test_a_slice_changing_state_changes_what_the_poll_says_and_nothing_else_does(self) -> None:
        working = [{"slice": "S1", "title": "Join", "state": "working"}]
        self.assertNotEqual(model_said(working), model_said([{**working[0], "state": "done"}]))
        self.assertEqual(model_said(working), model_said([{**working[0], "why": "another reason"}]))

    def test_the_card_holds_a_hidden_notice_with_redraw_and_the_poll_shows_it_when_they_differ(self) -> None:
        card = model_card(DRAWIO, "", "", "abc123")
        self.assertIn('data-model-said="abc123"', card)
        self.assertRegex(card, r'<p class="empty stale" hidden>[^<]*<button[^>]*data-model-redraw>Redraw</button>')
        self.assertIn("model.querySelector('.stale').hidden = model.dataset.modelSaid === found.model", SCRIPT)
        self.assertIn("if (event.target.closest('[data-model-redraw]')) location.reload();", SCRIPT)


class TypingTest(unittest.TestCase):
    def test_the_reload_waits_for_words_typed_in_any_box_on_the_page_not_only_a_card_s(self) -> None:
        guard = SCRIPT[SCRIPT.index("const typing ="):]
        guard = guard[:guard.index("location.reload(); return; }")]
        self.assertIn("document.querySelectorAll('textarea, input')", guard)
        self.assertIn("box.value.trim() && changed(box)", guard, "a box holding only what the page drew is not typing")
        self.assertIn("!typing", guard)


class BeforeTheAnswerTest(BoardTest):
    def test_a_person_s_action_has_dropped_the_kept_read_by_the_time_its_answer_is_sent(self) -> None:
        """A poll that lands the moment the answer does must not be handed the read from before the action."""
        kept_at_answer: list[bool] = []
        real = bridge.Bridge.send_response

        def watched(handler: bridge.Bridge, code: int, message: str | None = None) -> None:
            if handler.command == "POST":
                kept_at_answer.append(str(self.root) in board_read.KEPT)
            real(handler, code, message)

        with mock.patch.object(board_read, "KEEP", 60.0), \
                mock.patch.object(bridge.Bridge, "send_response", watched):
            self.get("/live.json")
            self.assertIn(str(self.root), board_read.KEPT)
            self.post("/tell", {"fairway": "ORD", "message": "said from the page"})
        self.assertEqual(kept_at_answer, [False])


if __name__ == "__main__":
    unittest.main()
