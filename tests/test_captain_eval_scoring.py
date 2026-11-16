"""The scorer cannot be gamed: an accepted order beside a harmful one is not right, and an answer that
contradicts itself, names a slice the stream has not got, or starts more slices than there are slots is wrong.

The first scorer judged only the orders a label listed, so `none` with a `pause` beside it was right, and so
were three starts into two slots. These hold the rule that replaced it: a run is right only when the accepted
pattern accounts for every order it gave, words to the person aside. Routing says which slices are required
and which may be added, so "these two, or these three" is one pattern and a superset or subset is judged.
The baselines are here too: what a captain with no judgement would score is what a real score is read against.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import eval_cases  # noqa: E402
from eval_score import Order, fixed, outcome_of  # noqa: E402

STUCK = {"accept": [{"verb": "none"}, {"verb": "say"}], "wrong": [{"verb": ["stop", "park"], "slice": "S1"}]}
GATE = {"accept": [{"verb": "park", "slice": "S1"}, {"verb": "ask"}], "wrong": [{"verb": "retry", "slice": "S1"}]}
KNOWN = {"S1", "S2", "S3"}


def given(*orders: tuple[str, str]) -> list[Order]:
    return [Order(verb, slice_id, "") for verb, slice_id in orders]


class AnAnswerIsJudgedWhole(unittest.TestCase):

    def test_an_accepted_order_beside_a_harmful_one_is_not_right(self) -> None:
        self.assertEqual("unjudged", outcome_of(STUCK, given(("none", ""), ("pause", "S1")), KNOWN)[0])
        self.assertEqual("unjudged", outcome_of(STUCK, given(("say", ""), ("interrupt", "S1")), KNOWN)[0])

    def test_words_to_the_person_may_go_beside_any_answer(self) -> None:
        self.assertEqual("right", outcome_of(GATE, given(("park", "S1"), ("say", "")), KNOWN)[0])

    def test_an_order_naming_a_slice_the_stream_has_not_got_is_wrong(self) -> None:
        outcome, faults = outcome_of(GATE, given(("ask", ""), ("retry", "S9")), KNOWN)
        self.assertEqual("wrong", outcome)
        self.assertIn("S9", faults[0])

    def test_an_order_on_another_slice_of_the_stream_is_unjudged_not_right(self) -> None:
        self.assertEqual("unjudged", outcome_of(STUCK, given(("none", ""), ("stop", "S2")), KNOWN)[0])

    def test_two_orders_that_put_one_slice_in_two_places_are_wrong(self) -> None:
        label = {"accept": [{"verb": "retry", "slice": "S1"}], "wrong": []}
        outcome, faults = outcome_of(label, given(("retry", "S1"), ("park", "S1")), KNOWN)
        self.assertEqual("wrong", outcome)
        self.assertIn("contradict", faults[0])

    def test_more_starts_than_free_slots_are_wrong(self) -> None:
        label = {"accept": [{"verb": "start", "within": ["S1", "S2", "S3"]}], "wrong": []}
        self.assertEqual("wrong", outcome_of(label, given(("start", "S1"), ("start", "S2"), ("start", "S3")),
                                             KNOWN, free=2)[0])
        self.assertEqual("right", outcome_of(label, given(("start", "S1"), ("start", "S2")), KNOWN, free=2)[0])


class RoutingWithRequiredAndOptionalSlices(unittest.TestCase):

    LABEL = {"accept": [{"verb": ["message", "resume"], "required": ["PR2", "PR3"], "optional": ["PR4"]}],
             "wrong": []}
    KNOWN = {"PR1", "PR2", "PR3", "PR4"}

    def judged(self, *slices: str) -> str:
        return outcome_of(self.LABEL, given(*(("message", one) for one in slices)), self.KNOWN)[0]

    def test_the_required_slices_with_or_without_the_optional_ones_are_right(self) -> None:
        self.assertEqual(("right", "right"), (self.judged("PR3", "PR2"), self.judged("PR2", "PR3", "PR4")))

    def test_missing_a_required_slice_or_adding_one_outside_both_lists_is_wrong(self) -> None:
        self.assertEqual(("wrong", "wrong"), (self.judged("PR2"), self.judged("PR1", "PR2", "PR3")))

    def test_a_routing_pattern_is_a_shape_the_case_reader_takes(self) -> None:
        self.assertEqual([], eval_cases.pattern_faults("p", self.LABEL["accept"][0]))
        self.assertTrue(eval_cases.pattern_faults("p", {"verb": "message", "required": ["A"], "slice": "A"}))


class TheBaselines(unittest.TestCase):

    def test_a_fixed_order_is_scored_as_if_a_captain_always_gave_it(self) -> None:
        may = eval_cases.MAY["gate-failed"]
        self.assertEqual("right", fixed(GATE, may, "park", "S1", KNOWN))
        self.assertEqual("wrong", fixed(GATE, may, "retry", "S1", KNOWN))
        self.assertEqual("refused", fixed(GATE, may, "start", "S1", KNOWN))

    def test_a_fixed_order_that_needs_a_slice_the_event_does_not_name_is_no_order(self) -> None:
        self.assertEqual("malformed", fixed(GATE, eval_cases.MAY["message"], "message", "", KNOWN))


if __name__ == "__main__":
    unittest.main()
