"""What a person does about a block, said on its card: why, the numbered steps, and an answer that is held.

manda's S97 stood parked for forty-two hours on a card that said `waiting on you for 2546m (past wait bound):
S97: S97 can…` and nothing else, and its owner's three answers were held by the decision ceiling with nothing
saying so. Each kind of block here gets its why and its steps, each step names a command or a control that
exists, a block of no known kind quotes its park whole, and a held answer says it is held — read off the same
`logs.answer_held` the harbourmaster clears parks by.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import fleet, logs
from slipwai.block_actions import KINDS, action, kind_of, said_lines
from slipwai.cli_fleet import lines
from slipwai.fleet_page import group_card
from slipwai.project.harbour import harbour_config

#: S97's park as manda's intake log holds it, cut to what the case needs.
S97 = ("S97: S97 cannot start, and another run will not change that: D316 holds it until a person approves a "
       "founder-facing mock state for See what you told us about the business, and mock-states.md has none.")
S97_NEED = ("A person runs /mockups 002-prd-v4-gap-closure, has the founder-facing state drawn and gives it a "
            "verdict.")


def park(**fields: object) -> dict:
    row = {"kind": "parked", "fairway": "intake", "slice": "S97", "t": "2026-11-21T16:12:42Z", "what": "S97: stuck.",
           "cause": "other", "needs": [], "paused": "no", "held": "", "unread": 0, "ceiling": 12, "answered": {}}
    return {**row, **fields}


class KindTest(unittest.TestCase):
    """One case per kind: its why is whole, and its steps name what does them."""

    def test_a_mock_up_verdict_says_how_to_draw_it_and_where_to_approve_it(self) -> None:
        found = action(park(what=S97, cause="gate", needs=[{"what": S97_NEED, "by": "person", "met": "no"}]))
        self.assertEqual(found["kind"], "mockup")
        self.assertTrue(found["why"].startswith("S97 cannot start") and found["why"].endswith("has none."),
                        "the first sentence whole, without the slice's own prefix")
        self.assertIn("`/mockups 002-prd-v4-gap-closure`", found["do"][0])
        self.assertIn("Press Approve or Reject", found["do"][-1])
        self.assertEqual(found["verdict"], "002-prd-v4-gap-closure", "the feature its card gives a verdict on")

    def test_a_question_is_answered_from_its_box_or_the_project_s_own_tell(self) -> None:
        found = action({"kind": "question", "fairway": "ORD", "slice": "ORD-01", "id": "D13", "t": "",
                        "asked": "One context or two?", "what": "D13 (ORD-01): One context or two?"})
        self.assertEqual(found["kind"], "question")
        self.assertNotIn("One context or two?", found["why"], "the row says the question; the why does not repeat it")
        self.assertIn("Send to ORD-01", found["do"][1])
        self.assertIn('`python3 scripts/agents/fleet.py tell ORD --slice ORD-01 "<your answer>"`', found["do"][1])

    def test_the_chart_s_context_question_says_nothing_waits_on_it(self) -> None:
        """`commands/chart.md` posts it as `"slice": "chart"` so nothing waits on it; manda's D495 card said the
        chart waited, over a Continue the build that was the only thing moving the project."""
        found = action({"kind": "question", "fairway": "intake", "slice": "chart", "id": "D495", "t": "",
                        "what": "Which bounded contexts does 003 touch (D495)? Taken as it stands: two."})
        self.assertEqual(found["kind"], "question")
        self.assertTrue(found["why"].startswith("Nothing waits on this"), found["why"])
        self.assertNotIn("waits for it", found["why"])
        self.assertIn("Read the question D495 above", found["do"][0])
        self.assertIn("Send to chart", found["do"][1])

    def test_a_park_at_the_ceiling_says_how_many_to_read(self) -> None:
        found = action(park(waiting="decision-review", cause="ceiling", unread=34, ceiling=12))
        self.assertEqual(found["kind"], "ceiling")
        self.assertIn("Read 22 of the 34 unread decisions", found["do"][0])
        self.assertIn("`slipwai telegraph --set decision_ceiling=34`", found["do"][0])

    def test_decisions_over_the_ceiling_say_how_many_and_under_it_hold_nothing(self) -> None:
        over = action({"kind": "decisions", "fairway": "intake", "blocking": "yes", "ceiling": 1,
                       "decisions": [{}, {}, {}], "what": "", "t": ""})
        self.assertIn("Read 2 of the 3 unread decisions", over["do"][0])
        under = action({"kind": "decisions", "fairway": "intake", "blocking": "no", "ceiling": 9,
                        "decisions": [{}], "what": "", "t": ""})
        self.assertIn("nothing is held up", under["why"])

    def test_a_grant_names_the_bootstrap_stack_and_who_applies_it(self) -> None:
        need = {"what": "ses:SendEmail on the service role in infra/bootstrap/main.tf", "by": "person", "met": "no"}
        found = action(park(cause="host", needs=[need]))
        self.assertEqual(found["kind"], "grant")
        self.assertIn("then press Done beside it", found["do"][0])
        self.assertIn("`make bootstrap`", found["do"][1])

    def test_a_person_need_is_done_then_ticked_and_a_met_one_is_left_out(self) -> None:
        needs = [{"what": "rotate the API key", "by": "person", "met": "no"},
                 {"what": "already done", "by": "person", "met": "yes"}]
        found = action(park(cause="host", needs=needs))
        self.assertEqual(found["kind"], "person")
        self.assertEqual(found["do"][0], "rotate the API key — then press Done beside it on this card.")
        self.assertNotIn("already done", " ".join(found["do"]))
        self.assertIn("I have landed it, carry on", found["do"][-1])

    def test_a_park_on_the_events_module_rule_names_the_rule_and_what_carry_on_does(self) -> None:
        """manda's S115 parked here with a card that said *a person or the host lands it on main*, which names
        nobody on the board (issue 168). The card names the rule and what the button does."""
        refusal = ("S115: make verify stops at check-slice-scope: apps/app/src/domain/intake/events.ts: the events "
                   "module may only grow on a slice branch, and this change reads as a member removed "
                   "(`, 'digest'`). Events already written are read back through it.")
        found = action(park(slice="S115", cause="host", what=refusal))
        self.assertEqual(found["kind"], "trunk")
        self.assertIn("the events module may only grow", found["why"])
        self.assertIn("the gate saw a member removed (`, 'digest'`)", found["why"])
        self.assertNotIn("the host", " ".join([found["why"], *found["do"]]))
        self.assertIn("I have landed it, carry on: S115 merges trunk and carries on", found["do"][-1])

    def test_its_card_s_button_says_it_was_landed_whatever_the_park_s_cause(self) -> None:
        said = "S115: events.ts: the events module may only grow on a slice branch, and this change reads as x."
        row = park(slice="S115", what=said)
        card = group_card({**row, "parks": [row], "slices": ["S115"], "action": action(row)}, controls=True)
        self.assertIn(">I have landed it, carry on</button>", card)
        self.assertNotIn("Sorted, carry on", card)

    def test_a_park_in_the_gate_s_words_before_issue_168_is_read_the_same(self) -> None:
        said = "S115: events.ts: the events module is the contract and grows additively — a line was removed."
        self.assertEqual(action(park(slice="S115", what=said))["kind"], "trunk")

    def test_a_hand_back_is_landed_on_trunk_and_ticks_itself(self) -> None:
        need = {"what": "the S92 frame in model.yaml", "by": "fleet", "met": "no", "how": "model.yaml holds it"}
        found = action({"kind": "told", "fairway": "intake", "t": "", "what": "S50 hands back: two edits.",
                        "needs": [need]})
        self.assertEqual(found["kind"], "handback")
        self.assertIn("Have the mender try again", found["do"][0], "the button first; the edit by hand is the fallback")
        self.assertIn("ticks itself when model.yaml holds it", found["do"][1])

    def test_a_run_that_stopped_on_the_machine_says_where_to_read_and_how_to_send_it_on(self) -> None:
        found = action(park(cause="exit", what="S12: /sail exited 1: docker is not running."))
        self.assertEqual(found["kind"], "machine")
        self.assertIn("`slipwai fleet intake`", found["do"][0])
        self.assertIn("Send to S97", found["do"][2])

    def test_a_demo_sent_back_says_where_its_verdict_is(self) -> None:
        found = action(park(cause="demo", what="S12: the demo was sent back: behaviour."))
        self.assertEqual(found["kind"], "demo")

    def test_a_pause_asks_nothing(self) -> None:
        found = action(park(cause="limit", paused="yes", until="2026-11-21T21:40:00Z"))
        self.assertEqual(found["kind"], "paused")
        self.assertIn("nothing for you to do", found["why"])

    def test_an_unreadable_log_says_which_file(self) -> None:
        found = action({"kind": "unreadable", "fairway": "intake", "t": "", "what": "line 4: not JSON"})
        self.assertEqual(found["kind"], "unreadable")
        self.assertIn("intake.jsonl", found["do"][0])

    def test_a_block_of_no_known_kind_quotes_its_park_whole(self) -> None:
        why = "S97: a long paragraph. With a second sentence; and a third clause nobody templated."
        found = action(park(cause="gate", what=why))
        self.assertEqual((found["kind"], found["why"]), ("other", why))
        self.assertNotIn(why, " ".join(found["do"]), "said once, in the why: the steps do not say it again")

    def test_a_park_an_earlier_slipwai_wrote_is_obsolete_and_dismissed(self) -> None:
        found = action(park(obsolete="1.5.1 → 2.1.0.dev93", what="name the next lane, or lift the W4 lane lock"))
        self.assertEqual(found["kind"], "obsolete")
        self.assertIn("1.5.1 → 2.1.0.dev93", found["why"])
        self.assertIn("Press Dismiss", found["do"][0])

    def test_a_merged_slice_s_unchecked_hand_back_is_probably_done_and_confirmed_by_a_tick(self) -> None:
        found = action({"kind": "told", "fairway": "intake", "t": "", "what": "S53: add the picker rule",
                        "probably": "yes", "needs": [{"what": "the picker rule in base.css", "by": "person",
                                                      "met": "no"}]})
        self.assertEqual(found["kind"], "probably")
        self.assertIn("press Done beside it: the picker rule in base.css", found["do"][0])

    def test_every_kind_is_one_the_set_names(self) -> None:
        for row in (park(), park(cause="question"), {"kind": "told", "t": "", "what": "a note"}):
            self.assertIn(kind_of(row), KINDS)


class HeldTest(unittest.TestCase):
    """An answer the harbourmaster's rule would hold says so, with the step that lets it through first."""

    def test_an_answer_past_the_ceiling_is_held_and_reading_comes_first(self) -> None:
        found = action(park(held="ceiling", unread=34, answered={"text": "mock it up", "t": "2026-11-23T09:19:02Z"}))
        self.assertRegex(found["held"], r"^Your answer 'mock it up' \(\d\d:\d\d\) is HELD: 34 unread decisions, "
                                        r"ceiling 12$")
        self.assertTrue(found["do"][0].startswith("First: Read 22 of the 34 unread decisions"))

    def test_an_answer_still_in_the_inbox_is_held_the_same_way(self) -> None:
        found = action(park(held="ceiling", unread=13, answer={"text": "go", "t": "2026-11-23T09:09:58Z"}))
        self.assertIn("Your answer 'go'", found["held"])

    def test_nothing_held_says_nothing_and_a_count_nobody_can_read_says_may_be(self) -> None:
        self.assertEqual(action(park(answered={"text": "go", "t": ""}))["held"], "")
        self.assertIn("MAY BE HELD", action(park(held="uncounted", ceiling=None, answered={"text": "go", "t": ""}))
                      ["held"])

    def test_the_rule_is_the_harbourmaster_s(self) -> None:
        """`logs.answer_held` is what both read: the board's word is the rule's word."""
        review = logs.entry("parked", fairway="F", why="x", waiting=logs.REVIEW)
        plain = logs.entry("parked", fairway="F", why="x")
        self.assertEqual([logs.answer_held(review, False), logs.answer_held(plain, True),
                          logs.answer_held(plain, None), logs.answer_held(plain, False)],
                         ["review", "ceiling", "uncounted", ""])


class BoardTest(unittest.TestCase):
    """S97's case end to end on the board: the row carries its action, and the terminal prints it whole."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        held = json.loads(harbour_config())
        (self.root / "harbour.json").write_text(json.dumps({**held, "decision_ceiling": 1}), encoding="utf-8")
        path = logs.deck_path(self.root, "pir", "intake")
        path.parent.mkdir(parents=True)
        lines_ = [logs.entry("claimed", fairway="intake", slice="S97", t="2026-11-21T09:00:00Z"),
                  logs.entry("decision", fairway="intake", id="D1", what="a", t="2026-11-21T10:00:00Z"),
                  logs.entry("decision", fairway="intake", id="D2", what="b", t="2026-11-21T10:01:00Z"),
                  logs.entry("parked", fairway="intake", slice="S97", why=S97, cause="gate",
                             t="2026-11-21T16:12:42Z", needs=[{"what": S97_NEED, "by": "person"}]),
                  logs.entry("told", fairway="intake", slice="S97", message="mock it up", by="person",
                             t="2026-11-23T09:19:02Z")]
        path.write_text("".join(one.line() for one in lines_), encoding="utf-8")

    def row(self) -> dict:
        found = fleet.board(self.root, json.loads((self.root / "harbour.json").read_text()),
                            now=datetime(2026, 11, 23, 10, 0, tzinfo=UTC))
        return next(one for one in found["inbox"] if one["kind"] == "parked")  # type: ignore[attr-defined]

    def test_the_held_answer_and_its_release_are_on_the_row(self) -> None:
        found = self.row()["action"]
        self.assertEqual(found["kind"], "mockup")
        self.assertIn("is HELD: 2 unread decisions, ceiling 1", found["held"])
        self.assertIn("Read 1 of the 2 unread decisions", found["do"][0])

    def test_read_under_the_ceiling_the_answer_is_not_held(self) -> None:
        path = logs.deck_path(self.root, "pir", "intake")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(logs.entry("read", fairway="intake", told="2026-11-21T10:00:00Z").line())
        self.assertEqual(self.row()["action"]["held"], "")

    def test_the_terminal_prints_why_the_held_line_and_every_step_uncut(self) -> None:
        printed = "\n".join(lines(self.root))
        self.assertIn(f"    Why: {S97.removeprefix('S97: ')}", printed)
        self.assertIn("is HELD: 2 unread decisions, ceiling 1", printed)
        self.assertIn("      1. First: Read 1 of the 2 unread decisions", printed)
        self.assertEqual(said_lines(self.row())[0], f"    Why: {S97.removeprefix('S97: ')}")



#: S81's refusal as manda's harbour log holds it, cut.
S81 = ("the full gate failed on slice/S81 rebased onto origin/main: make[1]: *** [test] Error 1 — it said: "
       "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[6/6]⎯ | npm error Lifecycle script `test` failed with error: | npm error code 1")


class RefusalTest(unittest.TestCase):
    """A refused merge is one sentence, and the gate's log is behind a disclosure, never inline."""

    def test_a_failed_merge_gate_is_said_by_what_failed_and_where(self) -> None:
        from slipwai.refusal_said import raw, summary
        self.assertEqual(summary("S81", S81), "S81's merge gate failed 6 tests in the merge worktree, after its "
                                              "own gate passed in its berth.")
        self.assertEqual(raw(S81).splitlines()[1], "npm error Lifecycle script `test` failed with error:")
        self.assertEqual(summary("S9", "trunk is red, so nothing merges until it is green"),
                         "trunk is red, so nothing merges until it is green")

    def test_the_needs_a_look_row_and_the_card_say_the_sentence_and_keep_the_log_folded(self) -> None:
        from slipwai.live_page import looks
        from slipwai.slice_card import facts_html
        [look] = looks([{"slice": "S81", "stage": "Merge refused", "refused": S81, "state": "queued"}], {}, {})
        self.assertNotIn("⎯", look["says"])
        self.assertIn("failed 6 tests in the merge worktree", look["says"])
        card = facts_html({"slice": "S81", "state": "queued", "refused": S81})
        self.assertIn("<details><summary>The gate's own words</summary>", card)
        self.assertEqual(card.split("<details>")[0].count("⎯"), 0, "no rule of the log before the disclosure")

    def test_a_park_on_a_refused_merge_gives_its_reason_not_the_log(self) -> None:
        found = action(park(cause="exit", what=f"S81: the merge was refused: {S81}"))
        self.assertNotIn("npm error", found["why"])


class ReplyOnceTest(unittest.TestCase):
    def test_a_waiting_card_shows_the_person_s_answer_once(self) -> None:
        from slipwai.talk_card import card_html
        talk = {"last": {"who": "You", "text": "mock it up", "line": "seen"},
                "answer": {"id": "m1", "text": "mock it up", "t": ""}}
        self.assertNotIn("mock it up", card_html({"slice": "S97", "fairway": "intake", "state": "waiting",
                                                  "talk": json.dumps(talk)}))
        self.assertIn("mock it up", card_html({"slice": "S97", "fairway": "intake", "state": "working",
                                               "talk": json.dumps(talk)}))


class CardTest(unittest.TestCase):
    """The slice's own card draws the same action, and the buttons only where a drawing waits."""

    def card(self, ready: bool) -> str:
        from slipwai.slice_card import answer_html
        found = action(park(what=S97, cause="gate", held="ceiling", unread=34,
                            answered={"text": "mock it up", "t": "2026-11-23T09:19:02Z"},
                            needs=[{"what": S97_NEED, "by": "person", "met": "no"}]))
        found["ready"] = ready
        return answer_html({"slice": "S97", "fairway": "intake", "state": "waiting", "park": S97,
                            "park_of": "park:2026-11-21T16:12:42Z", "action": json.dumps(found)})

    def test_the_card_says_why_what_is_held_and_each_step(self) -> None:
        drawn = self.card(ready=False)
        self.assertIn('<span class="lbl">Why:</span> S97 cannot start', drawn)
        self.assertIn("is HELD: 34 unread decisions, ceiling 12", drawn)
        self.assertIn("<li>First: Read 22 of the 34 unread decisions", drawn)
        self.assertNotIn("data-park-verdict", drawn)
        self.assertIn("Approve and Reject appear here once a drawing under specs/002-prd-v4-gap-closure", drawn)

    def test_with_a_drawing_waiting_it_offers_approve_and_reject_aimed_at_its_park(self) -> None:
        drawn = self.card(ready=True)
        self.assertIn('data-park-verdict="approve" data-fairway="intake" data-slice="S97" '
                      'data-of="park:2026-11-21T16:12:42Z" data-feature="002-prd-v4-gap-closure"', drawn)
        self.assertIn('data-park-verdict="reject"', drawn)


if __name__ == "__main__":
    unittest.main()
