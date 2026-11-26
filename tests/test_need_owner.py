"""Who acts on a need, and why (`need_owner`): the rule the mender takes a need by and the board says who acts by.

manda's board, issue 172: seven things *Waiting on you*, one of them a person's. A flaky test no open slice
touched, a merged slice's demo story and a model patch were never tried; a staff-directory seed was tried
twelve times and never committed, because the test that pins it was a slice's; and *Have the mender try
again* was offered on all of them. Each case below is one of those cards.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import logs
from slipwai.need_owner import DECIDE, MENDER, MERGE, PERSON, path_refusal, spent, tally, whose

FLAKY = "apps/manda-web/tests/routes/AboutYourBusinessAnswers.test.tsx"
STORY = "specs/003-make-manda-usable/slices/S110/try-it.json"
SEED = "apps/manda-app/seed/staff-directory.json"
PINNED = "apps/manda-app/tests/staff-directory-seed.test.ts"


def need(path: str, by: str = "fleet", what: str = "x") -> dict:
    return {"what": what, "by": by, "check": {"kind": "text", "path": path, "has": "x"}}


def who(one: dict, cruising: bool = False, busy: dict | None = None, merged: frozenset = frozenset()) -> tuple:
    return whose(one, logs.asks_a_decision(one), cruising, busy, merged)


class WhereANeedLandsTest(unittest.TestCase):
    def test_a_test_no_open_slice_is_changing_is_the_mender_s(self) -> None:
        self.assertEqual(who(need(FLAKY), busy={}), (MENDER, ""))

    def test_a_test_an_open_slice_is_changing_is_that_slice_s_and_says_so(self) -> None:
        acts, why = who(need(FLAKY), busy={FLAKY: "S120"})
        self.assertEqual(acts, PERSON)
        self.assertIn("Slice S120 is changing this file", why)

    def test_where_nothing_can_say_what_slices_touch_code_is_still_a_slice_s(self) -> None:
        self.assertEqual(who(need(FLAKY))[0], PERSON)

    def test_a_merged_slice_s_own_folder_is_the_mender_s(self) -> None:
        self.assertEqual(who(need(STORY), busy={}, merged=frozenset({"S110"})), (MENDER, ""))
        acts, why = who(need(STORY), busy={})
        self.assertEqual(acts, PERSON)
        self.assertIn("still being built", why)

    def test_the_cloud_and_a_gate_stay_a_person_s_and_say_why(self) -> None:
        acts, why = who(need("infra/service/main.tf"), busy={})
        self.assertEqual(acts, PERSON)
        self.assertIn("cloud", why)
        self.assertEqual(path_refusal("infra/service/flags.auto.tfvars", {}), "", "a flag's declaration is not")
        self.assertIn("checks the fleet runs on", path_refusal("scripts/check-x.py", {}))

    def test_the_seed_and_the_test_that_pins_it_can_both_be_the_mender_s(self) -> None:
        """Item 5: every one of the twelve attempts ended with nothing committed, each saying the seed could not
        change without the test that pins it, which a need was never allowed to touch."""
        self.assertEqual(path_refusal(SEED, {}), "")
        self.assertEqual(path_refusal(PINNED, {}), "")
        self.assertNotEqual(path_refusal(PINNED, {PINNED: "S105"}), "", "unless a slice in flight is changing it")


class WhoActsTest(unittest.TestCase):
    def test_a_model_patch_lands_with_its_slice_s_merge(self) -> None:
        careen = need("docs/event-model/model.yaml", what="apply specs/001-pir/slices/modelling-careen/handback/"
                                                          "model-yaml-required-item-unsatisfied.patch")
        acts, why = who(careen)
        self.assertEqual(acts, MERGE)
        self.assertIn("modelling-careen", why)
        acts, why = who(careen, merged=frozenset({"modelling-careen"}))
        self.assertEqual(acts, DECIDE, "merged without it: it was withheld as a decision")

    def test_a_model_change_with_no_patch_is_a_decision(self) -> None:
        self.assertEqual(who(need("docs/event-model/model.yaml"), busy={})[0], DECIDE)

    def test_a_secret_and_a_make_check_and_no_check_are_a_person_s(self) -> None:
        self.assertIn("secret", who({"what": "the SES sending key", "by": "person"})[1])
        self.assertIn("check run on trunk", who({"what": "x", "by": "fleet",
                                                 "check": {"kind": "make", "target": "check-try"}})[1])
        self.assertIn("only you can say", who({"what": "free a Docker network pool", "by": "person"})[1])

    def test_a_person_s_need_is_the_mender_s_only_while_cruising(self) -> None:
        self.assertEqual(who(need("docker/x.json", by="person"), busy={})[0], PERSON)
        self.assertEqual(who(need("docker/x.json", by="person"), cruising=True, busy={})[0], MENDER)


class AttemptsTest(unittest.TestCase):
    def line(self, kind: str, **fields: object) -> logs.Entry:
        return logs.entry(kind, harbour=True, **fields)

    def test_attempts_count_from_a_person_s_mend_again_and_a_decline_spends_them_all(self) -> None:
        key = {"fairway": "intake", "parked": "2026-11-24T18:35:14Z", "need": 2}
        harbour = [self.line("mend", job="need", commit="", attempt=n, **key) for n in (1, 2, 3)]
        done = tally(harbour)[("intake", "2026-11-24T18:35:14Z", 2)]
        self.assertTrue(spent(done, 3))
        harbour.append(self.line("mend-again", fairway="intake", parked="2026-11-24T18:35:14Z", at="x"))
        self.assertFalse(spent(tally(harbour)[("intake", "2026-11-24T18:35:14Z", 2)], 3))
        harbour += [self.line("mend", job="need", commit="", attempt=1, **key),
                    self.line("mend-failed", job="need", why="the mender changed nothing, and said why: a test "
                              "pins the file", declined=True, **key)]
        done = tally(harbour)[("intake", "2026-11-24T18:35:14Z", 2)]
        self.assertTrue(spent(done, 3), "one decline is the answer; another attempt would say it again")
        self.assertIn("a test pins the file", done["why"])


class PlainLineTest(unittest.TestCase):
    def test_a_plain_line_has_no_paths_ids_or_backticks(self) -> None:
        self.assertEqual(logs.unplain("The founder cannot reach help after a reload, so she is stuck."), "")
        for said in ("The seed in apps/manda-app/seed/staff-directory.json needs a third person.",
                     "FR-033 cannot be walked.", "Add `maxReceiveCount` to the queue.", "  "):
            with self.subTest(said=said):
                self.assertNotEqual(logs.unplain(said), "")

    def test_the_decisions_in_short_check_is_the_same_rule(self) -> None:
        import importlib.util
        import sys

        from slipwai.assets import TOOLKIT_ROOT

        sys.path.insert(0, str(TOOLKIT_ROOT / "scripts/agents"))
        spec = importlib.util.spec_from_file_location("check_decisions_plain",
                                                      TOOLKIT_ROOT / "scripts/check-decisions.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.NOT_PLAIN.pattern, logs.NOT_PLAIN.pattern, "one rule, not a second copy of it")


if __name__ == "__main__":
    unittest.main()
