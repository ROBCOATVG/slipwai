"""The captain's eval cases are readable, scored by the order and never the wording, and carry nothing personal.

An eval is not a test (decision 22): it puts a recorded moment to a real agent and its score is advice. What
*is* tested is the machinery an eval stands on — that every case on file is one the runner can read, that a
case laid out becomes the project state the captain reads, and that the scorer judges what it says it
judges: the verb and the slices, with routing as a set, and nothing of what the agent wrote. The drafted
cases were cut from real runs, so they are also held to having nothing personal in them.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import eval_cases  # noqa: E402
import eval_score  # noqa: E402

LABEL = {"accept": [{"verb": "park", "slice": "S1"}, {"verb": "ask"}],
         "wrong": [{"verb": "retry", "slice": "S1"}], "why": "the same refusal twice", "signed_off": ""}
MAY = ["retry", "park", "say", "ask", "none"]
#: A path under somebody's home, on any of the three platforms, or an email address.
PERSONAL = re.compile(r"/Users/|/home/|[A-Za-z]:\\Users\\|[\w.+-]+@[\w-]+\.[A-Za-z]{2,}")
#: Words in the registry's harness names that are ordinary English, or a forge rather than a harness: a case
#: may say "agent" or "code" without naming a product.
ORDINARY = {"agent", "ai", "build", "cli", "code", "coding", "factory", "for", "github", "my", "oh", "terminal"}
#: A harness's own sentence when its session limit is reached, which names it as surely as its name does.
HARNESS_SENTENCES = ("hit your session limit",)


def product_names() -> re.Pattern[str]:
    """Every harness and model a case could name, read from where the keel keeps them, never typed here."""
    from slipwai.project import stage_models

    rows = json.loads(stage_models.REGISTRY.read_text(encoding="utf-8"))["harnesses"]
    words = {row["key"].lower() for row in rows}
    words |= {word.lower() for row in rows for word in re.findall(r"[A-Za-z][\w-]+", row["name"])}
    template = json.loads(stage_models.stage_models())
    models = {value for role in template["roles"].values() for value in role.values()
              if value and value != stage_models.HOST}
    models |= set(re.findall(r"--set \w+\.\w+=([\w.-]+)", template["_comment"]))
    names = sorted((words - ORDINARY) | models | set(HARNESS_SENTENCES))
    return re.compile("|".join(rf"\b{re.escape(name)}\b" for name in names), re.IGNORECASE)


def orders(folder: Path, *bodies: object) -> list[Path]:
    paths = []
    for number, body in enumerate(bodies, 1):
        path = folder / f"{number:03d}.json"
        path.write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
        paths.append(path)
    return paths


class TheCasesOnFile(unittest.TestCase):

    def test_every_case_on_file_is_one_the_runner_can_read(self) -> None:
        found = eval_cases.every()
        self.assertTrue(found)
        for path in found:
            with self.subTest(case=eval_cases.case_id(path)):
                self.assertEqual([], eval_cases.faults(eval_cases.load(path), path.parent.name))

    def test_there_are_cases_for_each_of_the_four_decisions(self) -> None:
        for decision in eval_cases.DECISIONS:
            with self.subTest(decision=decision):
                self.assertTrue(eval_cases.every(decision=decision))

    def test_a_case_copied_from_a_run_carries_no_home_path_email_or_harness_or_model_name(self) -> None:
        named = product_names()
        for path in eval_cases.every():
            text = path.read_text(encoding="utf-8")
            with self.subTest(case=eval_cases.case_id(path)):
                self.assertIsNone(PERSONAL.search(text), PERSONAL.search(text))
                self.assertIsNone(named.search(text), named.search(text))

    def test_the_name_check_catches_a_harness_a_model_and_a_harness_sentence(self) -> None:
        named = product_names()
        for text in ('"model": "sonnet"', "ran under Claude Code", "You've hit your session limit"):
            with self.subTest(text=text):
                self.assertIsNotNone(named.search(text))
        self.assertIsNone(named.search("the agent wrote code for the terminal"))

    def test_a_label_nobody_has_signed_off_says_it_is_a_draft_or_made_up_and_what_it_rests_on(self) -> None:
        for path in eval_cases.every():
            case = eval_cases.load(path)
            note = case["label"].get("note", "")
            with self.subTest(case=eval_cases.case_id(path)):
                self.assertTrue(case["label"]["signed_off"] or note.startswith("Synthetic" if case.get("synthetic")
                                                                               else "Draft"))
                self.assertIn("Rests on:", note)
                if case.get("synthetic"):
                    self.assertTrue(case["source"].startswith("made up"))


class ACaseReadAndLaidOut(unittest.TestCase):

    def case(self) -> dict:
        return {"situation": "s", "source": "a recorded run",
                "snapshot": {"feature": "001-f", "fairway": "tables", "slices": {"S1": "claimed"},
                             "deck": [{"t": "2026-11-13T12:00:00Z", "kind": "claimed", "slice": "S1"}],
                             "harbour": [{"t": "2026-11-13T12:00:01Z", "kind": "slots", "slots": 1}],
                             "activity": {"S1": [{"t": "2026-11-13T12:00:02Z", "kind": "ran", "what": "make"}]},
                             "said": {"id": "m1", "text": "carry on"}, "gate": "no mark-set"},
                "event": {"id": "e1", "t": "2026-11-13T12:01:00Z", "kind": "gate-failed", "slice": "S1"},
                "label": dict(LABEL)}

    def test_a_case_filed_under_another_decision_is_refused_with_the_reason(self) -> None:
        self.assertIn("event `kind` is 'gate-failed' and the case is filed under 'stuck'",
                      eval_cases.faults(self.case(), "stuck"))

    def test_a_pattern_with_two_shapes_or_an_unknown_verb_is_refused(self) -> None:
        case = self.case()
        case["label"]["accept"] = [{"verb": "park", "slice": "S1", "slices": ["S1"]}, {"verb": "merge"}]
        said = " ".join(eval_cases.faults(case))
        self.assertIn("one of slice, slices, within, naming, required/optional at most", said)
        self.assertIn("`verb` is one of", said)

    def test_a_label_with_no_accepted_order_or_no_reason_is_refused(self) -> None:
        case = self.case()
        case["label"] = {"accept": [], "why": "", "signed_off": None}
        self.assertEqual(3, len(eval_cases.faults(case)))

    def test_the_event_gets_its_decisions_may_and_the_snapshot_as_its_facts(self) -> None:
        event = eval_cases.event_of(self.case())
        self.assertEqual(eval_cases.MAY["gate-failed"], event["may"])
        self.assertEqual("no mark-set", event["facts"]["gate"])
        self.assertNotIn("feature", event["facts"])

    def test_a_laid_out_case_is_the_state_where_the_program_keeps_it(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            event = eval_cases.lay_out(self.case(), root)
            run = root / ".slipwai/run"
            self.assertEqual(run / "events/tables/e1.json", event)
            self.assertEqual("gate-failed", json.loads(event.read_text(encoding="utf-8"))["kind"])
            deck = json.loads((run / "logs/001-f/tables.jsonl").read_text(encoding="utf-8"))
            self.assertEqual({"v": 1, "fairway": "tables", "t": "2026-11-13T12:00:00Z", "kind": "claimed",
                              "slice": "S1"}, deck)
            self.assertTrue((run / "activity/tables/S1.jsonl").is_file())
            said = json.loads((run / "talk/tables/_captain/inbox/m1.json").read_text(encoding="utf-8"))
            self.assertEqual(("person", "carry on"), (said["from"], said["text"]))
            self.assertTrue((run / "orders/tables").is_dir())
            self.assertTrue((root / "scripts/agents/harness.py").is_file())


class TheScorer(unittest.TestCase):

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.folder = Path(scratch.name)

    def judge(self, *bodies: object, label: dict | None = None, may: list[str] = MAY) -> eval_score.Judged:
        return eval_score.judge(label or LABEL, may, orders(self.folder, *bodies))

    def test_an_order_a_person_would_accept_is_right(self) -> None:
        self.assertEqual("right", self.judge({"verb": "park", "slice": "S1", "why": "twice"}).outcome)

    def test_an_order_that_is_plainly_wrong_is_wrong(self) -> None:
        self.assertEqual("wrong", self.judge({"verb": "retry", "slice": "S1", "note": "again"}).outcome)

    def test_an_order_in_neither_set_is_unjudged_not_wrong(self) -> None:
        self.assertEqual("unjudged", self.judge({"verb": "park", "slice": "S2", "why": "other"}).outcome)

    def test_wrong_wins_over_right_when_a_run_gives_both(self) -> None:
        self.assertEqual("wrong", self.judge({"verb": "park", "slice": "S1"}, {"verb": "retry", "slice": "S1"}).outcome)

    def test_the_wording_is_kept_beside_the_score_and_never_changes_it(self) -> None:
        one = self.judge({"verb": "park", "slice": "S1", "why": "the same refusal twice"})
        for path in self.folder.glob("*.json"):
            path.unlink()
        other = self.judge({"verb": "park", "slice": "S1", "why": "something else entirely"})
        self.assertEqual((one.outcome, one.signature), (other.outcome, other.signature))
        self.assertEqual(["park S1: the same refusal twice"], one.texts)

    def test_routing_is_scored_on_the_set_of_slices_in_any_order(self) -> None:
        label = {"accept": [{"verb": ["message", "resume"], "slices": ["PR2", "PR3"]}], "wrong": []}
        may = eval_cases.MAY["message"]
        self.assertEqual("right", self.judge({"verb": "message", "slice": "PR3", "text": "a"},
                                             {"verb": "resume", "slice": "PR2", "why": "b"},
                                             label=label, may=may).outcome)

    def test_routing_to_part_of_the_set_is_unjudged(self) -> None:
        label = {"accept": [{"verb": "message", "slices": ["PR2", "PR3"]}], "wrong": []}
        self.assertEqual("unjudged", self.judge({"verb": "message", "slice": "PR2", "text": "a"},
                                                label=label, may=eval_cases.MAY["message"]).outcome)

    def test_within_takes_any_slices_from_its_list_and_naming_catches_one(self) -> None:
        label = {"accept": [{"verb": "start", "within": ["L3", "L7"]}], "wrong": [{"verb": "start", "naming": "L4"}]}
        may = eval_cases.MAY["choose-next"]
        self.assertEqual("right", self.judge({"verb": "start", "slice": "L7"}, label=label, may=may).outcome)
        for path in self.folder.glob("*.json"):
            path.unlink()
        self.assertEqual("wrong", self.judge({"verb": "start", "slice": "L3"}, {"verb": "start", "slice": "L4"},
                                             label=label, may=may).outcome)

    def test_a_message_with_interrupt_is_scored_as_an_interrupt_not_a_nudge(self) -> None:
        label = {"accept": [{"verb": "message", "slice": "S1"}], "wrong": [{"verb": "interrupt", "slice": "S1"}]}
        judged = self.judge({"verb": "message", "slice": "S1", "text": "hm", "interrupt": True}, label=label,
                            may=eval_cases.MAY["stuck"])
        self.assertEqual(("wrong", {"interrupt": ["S1"]}), (judged.outcome, judged.answer))

    def test_a_malformed_order_is_no_order_and_says_why(self) -> None:
        judged = self.judge("{not json", {"verb": "park"}, {"verb": "merge", "slice": "S1"}, [1])
        self.assertEqual("malformed", judged.outcome)
        self.assertEqual(4, len(judged.malformed))
        self.assertIn("`park` names no slice", " ".join(judged.malformed))

    def test_no_order_at_all_is_silence_which_the_fixed_rule_answers(self) -> None:
        self.assertEqual("silent", self.judge().outcome)
        self.assertIn("silent", eval_score.FALLBACK)

    def test_an_order_the_event_did_not_allow_is_refused(self) -> None:
        judged = self.judge({"verb": "start", "slice": "S1"})
        self.assertEqual("refused", judged.outcome)

    def test_the_programs_result_beside_an_order_is_not_read_as_one(self) -> None:
        orders(self.folder, {"verb": "park", "slice": "S1"})
        (self.folder / "001.result.json").write_text('{"result": "done"}', encoding="utf-8")
        self.assertEqual(["001.json"], [path.name for path in eval_score.order_files(self.folder)])

    def test_agreement_is_the_share_of_runs_that_gave_the_commonest_answer(self) -> None:
        park = eval_score.Judged("right", {"park": ["S1"]})
        retry = eval_score.Judged("wrong", {"retry": ["S1"]})
        self.assertAlmostEqual(2 / 3, eval_score.agreement([park, park, retry]))
        self.assertEqual(1.0, eval_score.agreement([eval_score.Judged("silent", {})] * 2))


if __name__ == "__main__":
    unittest.main()
