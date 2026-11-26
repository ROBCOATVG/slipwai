"""What leaves *Waiting on you* by itself, what is only asked to be confirmed, and what is dismissed as obsolete.

manda's Work tab said *53 waiting* while its column said *Waiting on you · 0*: forty-seven *a slice needs this
on trunk* items, twenty-five of them from slices merged days before, and a park from before the crossing to
version 2 that nothing in the harness acted on. A need trunk already holds leaves (read by `need_check`, the
harbourmaster's own reading); a merged slice's need nothing can check is asked to be confirmed, with the tick
the board already writes; a park an earlier slipwai wrote is dismissed once. Builds a git repository, so it is
in the Makefile's `SLOW` list.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import fleet, logs
from slipwai.deck import dismiss, keep_recommendation, mend_again, tick_need
from slipwai.fleet_page import groups_html, headline
from slipwai.on_you import parked, settling
from slipwai.project.harbour import harbour_config

LANDED: dict = {"what": "the picker rule in base.css", "by": "fleet",
          "check": {"kind": "text", "path": "base.css", "has": ".colleague-picker"}}
NOT_YET = {"what": "the SES grant", "by": "fleet", "check": {"kind": "text", "path": "base.css", "has": "ses:Send"}}


class SettleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / ".slipwai").mkdir()
        (self.root / "harbour.json").write_text(harbour_config(), encoding="utf-8")
        (self.root / "project.json").write_text(json.dumps(
            {"generator": {"generatedWith": "1.5.1", "updatedWith": "2.1.0.dev93"}}), encoding="utf-8")
        (self.root / "base.css").write_text(".colleague-picker{flex:1}\n", encoding="utf-8")
        for argv in (["init", "-q", "--initial-branch=main"], ["add", "base.css"],
                     ["-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "trunk"]):
            subprocess.run(["git", *argv], cwd=self.root, check=True, capture_output=True)

    def deck(self, *entries: logs.Entry) -> None:
        path = logs.deck_path(self.root, "pir", "intake")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for one in entries:
                handle.write(one.line())

    def board(self) -> dict:
        return fleet.board(self.root, json.loads((self.root / "harbour.json").read_text()))

    def rows(self) -> list[dict]:
        found = self.board()["inbox"]
        assert isinstance(found, list)
        return found

    def test_a_need_trunk_already_holds_leaves_before_any_receipt_says_so(self) -> None:
        self.deck(logs.entry("told", fairway="intake", message="S53 hands back the picker rule",
                             t="2026-11-20T09:00:00Z", by="session", needs=[LANDED]))
        self.assertEqual([row for row in self.rows() if row["kind"] == "told"], [])

    def test_a_check_a_shell_left_quoted_is_read_as_the_words_it_quotes(self) -> None:
        """manda's sessions wrote `has: '"intakeTagsOf"'`; trunk held the word, and nothing ever ticked it."""
        quoted = {**LANDED, "check": {**LANDED["check"], "has": '".colleague-picker"'}}
        self.deck(logs.entry("told", fairway="intake", message="S53 hands back the picker rule",
                             t="2026-11-20T09:00:00Z", by="session", needs=[quoted]))
        self.assertEqual([row for row in self.rows() if row["kind"] == "told"], [])

    def test_a_merged_slice_s_need_trunk_does_not_hold_is_still_owed(self) -> None:
        """A slice built on a stand-in has not landed the rest: its failing check keeps it on the board."""
        self.deck(logs.entry("claimed", fairway="intake", slice="S84", t="2026-11-20T08:00:00Z"),
                  logs.entry("told", fairway="intake", slice="S84", message="S84: the SES grant",
                             t="2026-11-20T09:00:00Z", by="session", needs=[NOT_YET]),
                  logs.entry("merged", fairway="intake", slice="S84", commit="abc", t="2026-11-20T10:00:00Z"))
        [row] = [row for row in self.rows() if row["kind"] == "told"]
        self.assertNotIn("probably", row)

    def test_a_merged_slice_s_unchecked_need_is_asked_to_be_confirmed_not_counted_and_a_tick_confirms_it(self) -> None:
        self.deck(logs.entry("claimed", fairway="intake", slice="S53", t="2026-11-20T08:00:00Z"),
                  logs.entry("told", fairway="intake", message="S53 hands back: a rule for docs/design.md",
                             t="2026-11-20T09:00:00Z", by="session", needs=[{"what": "the design.md section",
                                                                             "by": "person"}]),
                  logs.entry("merged", fairway="intake", slice="S53", commit="abc", t="2026-11-20T10:00:00Z"))
        found = self.board()
        [row] = [row for row in found["inbox"] if row["kind"] == "told"]
        self.assertEqual((row["probably"], row["action"]["kind"]), ("yes", "probably"))
        self.assertEqual(parked(found, []), [], "not something only a person can move the work on by")
        self.assertEqual(headline(found)[2], "Nothing is waiting on you.", "the headline counts what the list does")
        self.assertEqual(settling(found), [{"n": 1, "href": "#probably",
                                            "text": "1 hand-back of merged slices probably done: confirm"}])
        tick_need(self.root, "intake", "2026-11-20T09:00:00Z", 0)
        self.assertEqual([row for row in self.rows() if row["kind"] == "told"], [], "the tick is the confirmation")

    def test_a_hand_back_the_mender_takes_comes_after_judgement_and_is_asked_again_once_spent(self) -> None:
        """manda's eleven CSS hand-backs sat in arrival order above the one verdict that held the project,
        each telling a person to edit trunk by hand; the mender, which lands them, had given up. And every card
        offered Have the mender try again, the ones it never takes and the ones it had not tried yet (#172)."""
        at = "2026-11-20T09:00:00Z"
        self.deck(logs.entry("told", fairway="intake", message="S53 hands back the SES grant", t=at, by="session",
                             needs=[NOT_YET]),
                  logs.entry("parked", fairway="intake", why="S12: which context owns alerts?",
                             t="2026-11-21T09:00:00Z"))
        drawn = groups_html(self.board()["groups"], True)
        self.assertLess(drawn.index('id="judgement"'), drawn.index('id="harness"'), "what only you decide, first")
        self.assertIn("The mender will do these", drawn)
        self.assertNotIn("data-mend-again=", drawn, "nothing to ask again while it has attempts left")
        path = logs.harbour_path(self.root, logs.machine())
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as out:
            for attempt in (1, 2, 3):
                out.write(logs.entry("mend", harbour=True, job="need", commit="", attempt=attempt, fairway="intake",
                                     parked=at, need=0).line())
        drawn = groups_html(self.board()["groups"], True)
        self.assertIn("data-mend-again=", drawn)
        self.assertIn("Have the mender try again", drawn)
        self.assertIn("the mender may try", mend_again(self.root, "intake", at))
        deck = logs.fold(logs.deck_path(self.root, "pir", "intake").read_text(encoding="utf-8").splitlines())
        self.assertEqual([(e.kind, e.fields["parked"]) for e in deck if e.kind == "mend-again"], [("mend-again", at)])
        with self.assertRaisesRegex(ValueError, "no hand-back with needs"):
            mend_again(self.root, "intake", "2026-01-01T00:00:00Z")

    def test_keeping_a_chart_question_s_recommendation_closes_it(self) -> None:
        self.deck(logs.entry("question", fairway="intake", slice="chart", id="D495", what="Which contexts?",
                             t="2026-11-24T08:48:31Z"))
        self.assertEqual([row["kind"] for row in self.rows()], ["question"])
        self.assertIn("kept", keep_recommendation(self.root, "intake", "D495"))
        self.assertNotIn("question", [row["kind"] for row in self.rows()])
        with self.assertRaisesRegex(ValueError, "no question D9"):
            keep_recommendation(self.root, "intake", "D9")

    def test_a_park_an_earlier_slipwai_wrote_is_obsolete_once_and_dismissed_everywhere(self) -> None:
        at = "2026-11-18T13:51:39Z"
        self.deck(logs.entry("parked", fairway="intake", why="name the next lane, or lift the W4 lane lock", t=at,
                             crossed="037bd452188cc8af"))
        found = self.board()
        [row] = [row for row in found["inbox"] if row["kind"] == "parked"]
        self.assertEqual(row["obsolete"], "1.5.1 → 2.1.0.dev93")
        self.assertEqual(parked(found, []), [])
        self.assertEqual([one["text"] for one in settling(found)],
                         ["The intake stream's park is obsolete since 1.5.1 → 2.1.0.dev93: dismiss it"])
        dismiss(self.root, "intake", at)
        self.assertEqual([row for row in self.rows() if row["kind"] == "parked"], [])
        deck = logs.fold(logs.deck_path(self.root, "pir", "intake").read_text(encoding="utf-8").splitlines())
        self.assertEqual(logs.open_parks(deck, [], "intake"), [], "the captain and harbourmaster let it go too")

    def test_a_park_of_this_harness_is_not_dismissed_by_the_obsolete_path(self) -> None:
        self.deck(logs.entry("parked", fairway="intake", why="S12: a question", t="2026-11-20T09:00:00Z"))
        with self.assertRaisesRegex(ValueError, "no message at"):
            dismiss(self.root, "intake", "2026-11-20T09:00:00Z")


if __name__ == "__main__":
    unittest.main()
