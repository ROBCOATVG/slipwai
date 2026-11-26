"""Stale cards close themselves (issue 172): a need or a question nobody owes an answer to leaves the board.

manda's `S110-decide-2` was handed back as a model change *per D523*, asked as a question, and answered by
D523 under another question's id; S110 merged. The need's text check ticked once trunk had the model change,
but the question stood under *Waiting on you* for good, because only a `decision` carrying its own id closed
one. Now a question whose need is met, or whose slice has merged and which a recorded decision it cites
answers, gets a `question-met` saying which; and a decision need of a merged slice that cites a recorded
decision gets a `need-met` saying why.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from harbourmaster_fixture import Fixture

from slipwai import logs
from slipwai.fleet import fairways

MODEL = ("docs/event-model/model.yaml, per D523: reconcile to events.ts; cite D523 in a comment on each block "
         "changed")


class StaleTest(Fixture):
    def handed_back(self, *after: logs.Entry) -> None:
        self.deck("ordering", "ORD",
                  logs.entry("claimed", fairway="ORD", slice="ORD-01", t="2026-11-24T15:30:00Z"),
                  logs.entry("decision", fairway="ORD", slice="ORD-01", id="ORD-01-decide-1",
                             what="D523: reconcile the model to events.ts as a hand-back", t="2026-11-24T15:32:32Z"),
                  logs.entry("told", fairway="ORD", slice="ORD-01", message="D523 decided (A): the model is "
                             "reconciled", by="session", t="2026-11-24T15:34:50Z",
                             needs=[{"what": MODEL, "by": "person", "decide": True, "question": "ORD-01-decide-2"}]),
                  logs.entry("question", fairway="ORD", slice="ORD-01", id="ORD-01-decide-2", what=MODEL,
                             t="2026-11-24T15:34:50Z"),
                  *after)

    def receipts(self, kind: str) -> list[dict]:
        return [entry.fields for entry in self.harbour() if entry.kind == kind]

    def test_a_merged_slice_s_question_a_recorded_decision_answers_drops_off(self) -> None:
        self.handed_back(logs.entry("merged", fairway="ORD", slice="ORD-01", commit="abc1234",
                                    t="2026-11-24T16:00:00Z"))
        for _ in range(2):
            done = self.run_once()
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.receipts("need-met"), [{"fairway": "ORD", "parked": "2026-11-24T15:34:50Z", "need": 0,
                                                      "how": "ORD-01 has merged and D523 answers it"}])
        self.assertEqual(self.receipts("question-met"), [{"fairway": "ORD", "id": "ORD-01-decide-2",
                                                          "how": "the need it was asked for is met: ORD-01 has "
                                                                 "merged and D523 answers it"}])
        [stream] = fairways(self.root)[0]
        self.assertEqual(stream.asked, [], "the board no longer asks it")

    def test_an_unmerged_slice_s_question_still_stands(self) -> None:
        self.handed_back()
        self.run_once()
        self.assertEqual(self.receipts("question-met"), [])
        self.assertEqual(self.receipts("need-met"), [])


if __name__ == "__main__":
    unittest.main()
