"""Whether a question is open is one rule, `logs.unanswered`, and the board, the captain and clearance read it.

#174 taught the board `question-met`, the harbourmaster's receipt for a question nobody owes an answer to any
more, and left the captain and clearance reading only a `decision` carrying the question's id. manda's
S110-decide-2 would have left the board and still held its slice in clearance, and been put to the skipper
again by the captain. Each reader is driven here with the same lines.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from typing import Any

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

AGENTS = TOOLKIT_ROOT / "scripts/agents"


def script(name: str) -> Any:
    if str(AGENTS) not in sys.path:
        sys.path.insert(0, str(AGENTS))
    found = importlib.util.spec_from_file_location(f"toolkit_{name}_question_open", AGENTS / f"{name}.py")
    assert found is not None and found.loader is not None
    made = importlib.util.module_from_spec(found)
    sys.dont_write_bytecode = True
    found.loader.exec_module(made)
    return made


def at(t: str, kind: str, harbour: bool = False, **fields: object) -> logs.Entry:
    """A line as a reader folds it from a log: its instant on the entry, not among its fields."""
    return logs.Entry(kind=kind, fields=logs.entry(kind, harbour, **fields).fields, t=t)


ASKED = at("2026-11-24T15:34:50Z", "question", fairway="ORD", slice="ORD-01", id="ORD-01-decide-2",
           what="which name?")
OTHER = at("2026-11-24T15:35:00Z", "question", fairway="ORD", slice="ORD-01", id="ORD-01-decide-3",
           what="which colour?")
MET = at("2026-11-24T16:00:00Z", "question-met", harbour=True, fairway="ORD", id="ORD-01-decide-2",
         how="ORD-01 has merged and D523 answers it")


class RuleTest(unittest.TestCase):
    def test_a_decision_carrying_its_id_answers_it(self) -> None:
        decided = logs.entry("decision", fairway="ORD", slice="ORD-01", id="ORD-01-decide-2", what="A")
        self.assertEqual(logs.unanswered([ASKED, OTHER], [ASKED, OTHER, decided]), [OTHER])

    def test_a_question_met_for_its_fairway_answers_it(self) -> None:
        self.assertEqual(logs.unanswered([ASKED, OTHER], [ASKED, OTHER, MET]), [OTHER])

    def test_a_question_met_for_another_fairway_does_not(self) -> None:
        elsewhere = logs.entry("question-met", harbour=True, fairway="PAY", id="ORD-01-decide-2", how="it is met")
        self.assertEqual(logs.unanswered([ASKED], [ASKED, elsewhere]), [ASKED])
        self.assertEqual(logs.unanswered([ASKED], [ASKED, MET], fairway="PAY"), [ASKED],
                         "the stream a caller names is the one the receipt must name")

    def test_only_questions_are_ever_open(self) -> None:
        told = logs.entry("told", fairway="ORD", message="hello")
        self.assertEqual(logs.unanswered([told, ASKED], []), [ASKED])


class ClearanceTest(unittest.TestCase):
    def test_a_question_met_no_longer_holds_its_slice(self) -> None:
        clearance = script("clearance")
        lines = [{"v": 1, "kind": e.kind, "t": e.t, **e.fields} for e in (ASKED, OTHER, MET)]
        self.assertEqual(clearance.folded(lines, demos="hand").questions,
                         {"ORD-01": [("ORD-01-decide-3", "which colour?")]})

    def test_a_decision_still_answers_one_whichever_came_first(self) -> None:
        clearance = script("clearance")
        lines = [{"v": 1, "kind": "decision", "fairway": "ORD", "slice": "ORD-01", "id": "ORD-01-decide-2",
                  "what": "A", "t": "2026-11-24T15:30:00Z"},
                 {"v": 1, "kind": ASKED.kind, "t": ASKED.t, **ASKED.fields}]
        self.assertEqual(clearance.folded(lines, demos="hand").questions, {})


class CaptainTest(unittest.TestCase):
    def test_the_captain_reads_question_met_from_the_harbour(self) -> None:
        captain = script("captain")
        captain.harbour_entries = lambda: [MET]
        self.assertEqual(captain.open_questions([ASKED, OTHER], "ORD-01"), [OTHER])
        self.assertFalse(captain.settled([ASKED, OTHER], "ORD-01"))
        captain.harbour_entries = lambda: [MET, logs.entry("question-met", harbour=True, fairway="ORD",
                                                           id="ORD-01-decide-3", how="it is met")]
        self.assertEqual(captain.open_questions([ASKED, OTHER], "ORD-01"), [])
        self.assertTrue(captain.settled([ASKED, OTHER], "ORD-01"), "a slice whose questions are met carries on")

    def test_a_park_written_after_its_question_was_met_did_not_wait_on_it(self) -> None:
        captain = script("captain")
        captain.harbour_entries = lambda: [MET]
        park = at("2026-11-24T17:00:00Z", "parked", fairway="ORD", slice="ORD-01", why="ORD-01: held on the host")
        self.assertFalse(captain.park_waited_on_questions([ASKED, park], [park]))
        earlier = at("2026-11-24T15:40:00Z", "parked", fairway="ORD", slice="ORD-01",
                     why="ORD-01: awaiting a decision")
        self.assertTrue(captain.park_waited_on_questions([ASKED, earlier], [earlier]))


if __name__ == "__main__":
    unittest.main()
