"""A captain's own `ask` reaches a person (whole-branch review, M2).

Contract 2.2 says a captain's `ask` becomes *Waiting on you*. It reached nobody: the list walked the slices'
conversations and skipped the captain's, the window drew the ask twice — once from the order, once from the
thread — and under `/cruise` the thread's copy said nothing waited on anyone, though no skipper answers a
captain. Here the ask is written as `captain_orders.Acts` writes it, and the order beside it as `orders.py`
does, and the list and the window are read the way the board reads them.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import checkout_packages  # noqa: F401

from slipwai import logs, talk
from slipwai.captain_window import talk_parts
from slipwai.on_you import waiting
from slipwai.talk_page import payload

ASK = "captain-ask-e1-1"


class CaptainAskTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        path = logs.deck_path(self.root, "ordering", "ORD")
        path.parent.mkdir(parents=True)
        path.write_text(logs.entry("claimed", fairway="ORD", slice="ORD-01").line(), encoding="utf-8")
        run = logs.run_dir(self.root)
        self.home = talk.place(run, "ORD", talk.CAPTAIN)
        talk.note(self.home, "ask", id=ASK, what="question", text="Ship the export without the CSV?",
                  options=["yes", "no"], by="captain")
        orders = run / "orders" / "ORD"
        orders.mkdir(parents=True)
        (orders / "20261117T100000Z-aaaaaa.json").write_text(json.dumps(
            {"v": 1, "id": "20261117T100000Z-aaaaaa", "t": "2026-11-17T10:00:00Z", "event": "e1", "fairway": "ORD",
             "verb": "ask", "text": "Ship the export without the CSV?", "options": ["yes", "no"], "sig": ""}),
            encoding="utf-8")
        (orders / "20261117T100000Z-aaaaaa.result.json").write_text(json.dumps({"v": 1, "state": "done"}),
                                                                     encoding="utf-8")
        self.rows = [{"slice": "ORD-01", "title": "", "state": "working", "fairway": "ORD", "feature": "ordering",
                      "why": ""}]

    def cruise(self, **held: object) -> None:
        (self.root / ".specify").mkdir(exist_ok=True)
        (self.root / ".specify/cruise.json").write_text(json.dumps(held), encoding="utf-8")

    def holding(self) -> list[dict]:
        return waiting(SimpleNamespace(root=self.root, fitting=None), {}, {}, self.rows)["holding"]

    def log(self) -> str:
        extra, sent, said = talk_parts(self.root, "ORD")
        return payload(self.root, "ORD", "", extra, sent, said)["log"]

    def test_a_captain_s_open_ask_holds_work_up_under_cruise_as_without_it(self) -> None:
        for cruise in (None, {"enabled": False}, {"enabled": True, "decide": "recommended-first"}):
            if cruise is not None:
                self.cruise(**cruise)
            with self.subTest(cruise=cruise):
                self.assertEqual([(one["text"], one["href"]) for one in self.holding()],
                                 [("The ORD captain asks: Ship the export without the CSV?",
                                   f"/captain-window?fairway=ORD#ask-{ASK}")])

    def test_the_window_draws_the_ask_once_with_its_options_and_a_box_even_while_cruising(self) -> None:
        self.cruise(enabled=True, decide="recommended-first")
        log = self.log()
        self.assertEqual(log.count("Ship the export without the CSV?"), 1, log)
        self.assertIn(f'data-ask="{ASK}"', log)
        self.assertIn('data-ask-pick="no"', log)
        self.assertIn("data-ask-send", log)
        self.assertIn("Waiting on you", log)
        self.assertNotIn("nothing waits on you", log)

    def test_a_person_s_answer_names_the_ask_and_takes_it_off_the_list(self) -> None:
        talk.send(self.home, "say", "no", of=ASK)
        self.assertEqual(self.holding(), [])
        self.assertIn("Your answer: no", self.log())


class ReadByInboxTest(unittest.TestCase):
    def test_the_board_counts_a_told_its_captain_acted_on_as_answered_and_nothing_else_in_its_second(self) -> None:
        """M6, the board's reader: a `read` naming an inbox id is that `told`'s alone."""
        from slipwai.fleet import Fairway
        t = "2026-11-17T10:00:00Z"
        lines = [logs.entry("decision", fairway="ORD", id="D-ORD-01", what="x"),
                 logs.entry("told", fairway="ORD", message="one", by="person", inbox="m-1"),
                 logs.entry("told", fairway="ORD", message="two", by="person", inbox="m-2"),
                 logs.entry("read", fairway="ORD", told=t, inbox="m-1")]
        found = logs.fold([json.dumps({**json.loads(line.line()), "t": t}) for line in lines])
        owner = Fairway("ORD", "ordering", found)
        self.assertEqual([str(e.fields["message"]) for e in owner.unanswered], ["two"])
        self.assertEqual(len(owner.unreviewed), 1, "the decision in that second is not read by it")


if __name__ == "__main__":
    unittest.main()
