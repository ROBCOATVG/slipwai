"""What the trunk mender may take and land for a need, read without a repository (issue 172).

manda's staff-directory need was tried twelve times, and every attempt ended with *the mender ended without
committing anything on its branch*. Read from the mender's own output, each attempt said the same thing: the
seed file had to gain a third person, a test pinned the file to exactly two, and a need's change was never
allowed to touch a test — so the seed could not land without turning trunk red, and the mender, correctly,
changed nothing. The rule was the cause. A test no slice in flight is changing is now the mender's for the
need, its brief says so, and an attempt that changes nothing says why on the card rather than being sent
again to say it twice.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, ClassVar
from unittest import mock

import checkout_packages  # noqa: F401
from harbourmaster_fixture import AGENTS

from slipwai import logs

SEED = "apps/manda-app/seed/staff-directory.json"
PINNED = "apps/manda-app/tests/staff-directory-seed.test.ts"
FREE: Any = ({}, frozenset())


def load() -> Any:
    sys.path.insert(0, str(AGENTS))
    spec = importlib.util.spec_from_file_location("mender_needs", AGENTS / "mender.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def told(need: dict, at: str = "2026-11-24T18:35:14Z") -> logs.Entry:
    return logs.Entry("told", {"fairway": "intake", "message": "S105's walks", "needs": [need]}, t=at)


STAFF = {"what": "A third BD in apps/manda-app/seed/staff-directory.json", "by": "fleet",
         "plain": "The several-signatories screen cannot be tried, because the staff list has two people.",
         "check": {"kind": "text", "path": SEED, "has": "\"Priya"}}


class StaffDirectoryTest(unittest.TestCase):
    mender: ClassVar[Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.mender = load()

    def test_the_seed_and_the_test_that_pins_it_land_together_where_no_slice_holds_the_test(self) -> None:
        with mock.patch.object(self.mender, "changed", return_value=[SEED, PINNED]):
            self.assertEqual(self.mender.refusal("need", "a", "b", [], SEED, FREE), "")
            held: Any = ({PINNED: "S105"}, frozenset())
            self.assertIn("Slice S105 is changing this file", self.mender.refusal("need", "a", "b", [], SEED, held))
            self.assertIn("is not a need's to change", self.mender.refusal("need", "a", "b", [], SEED),
                          "where nothing says what the slices hold, a test is still a slice's")

    def test_its_brief_says_the_pinning_test_is_its_to_change_and_where_to_say_why(self) -> None:
        wanted = self.mender.need_turn("green", [("intake", told(STAFF), 0)], [], FREE)
        self.assertEqual(wanted["check"], f"{SEED} holds `\"Priya` on trunk", "one quote is the text's own")
        quoted = {**STAFF, "check": {"kind": "text", "path": SEED, "has": '"D523"'}}
        self.assertIn("holds `D523` on trunk", self.mender.need_turn("green", [("intake", told(quoted), 0)], [],
                                                                     FREE)["check"],
                      "a pair of quotes round it is a shell's, trimmed as trunk is asked it (S110)")
        said = self.mender.prompt("need", Path("/w"), "mend/need-x", {**wanted, "why_file": "/w.why"})
        self.assertIn("a test that pins the file's contents", said)
        self.assertIn("/w.why", said)
        self.assertIn(STAFF["plain"], said)

    def test_an_attempt_that_changes_nothing_and_says_why_has_declined_and_is_not_sent_again(self) -> None:
        with tempfile.TemporaryDirectory() as there:
            why = Path(there) / "need-x.why"
            why.write_text("A test pins the seed to two people, and the slice that adds the second has not "
                           "merged.\n", encoding="utf-8")
            held = {"job": "need", "branch": "mend/need-x", "fairway": "intake", "parked": "2026-11-24T18:35:14Z",
                    "need": 0, "attempt": 1, "why_file": str(why), "reads": SEED}
            with mock.patch.object(self.mender, "changed", return_value=[]), \
                    mock.patch.object(self.mender, "RECORD", Path(there) / "mender.json"):
                line = self.mender.finish(held, lambda branch: ("", "not reached"), "a", [], FREE)
        self.assertEqual(line.kind, "mend-failed")
        self.assertTrue(line.fields["declined"])
        self.assertIn("A test pins the seed to two people", line.fields["why"])
        harbour = [logs.entry("mend", harbour=True, job="need", commit="", attempt=1, fairway="intake",
                              parked="2026-11-24T18:35:14Z", need=0), line]
        self.assertIsNone(self.mender.need_turn("green", [("intake", told(STAFF), 0)], harbour, FREE),
                          "one decline is the answer: another attempt would say it again")
        harbour.append(logs.entry("mend-again", harbour=True, fairway="intake", parked="2026-11-24T18:35:14Z",
                                  at="2026-11-25T16:59:24Z"))
        self.assertIsNotNone(self.mender.need_turn("green", [("intake", told(STAFF), 0)], harbour, FREE),
                             "a person's Have the mender try again asks afresh")

    def test_an_attempt_that_changes_nothing_and_says_nothing_is_a_failed_attempt_as_before(self) -> None:
        with tempfile.TemporaryDirectory() as there:
            held = {"job": "need", "branch": "b", "fairway": "intake", "parked": "p", "need": 0, "attempt": 1,
                    "why_file": str(Path(there) / "absent.why")}
            with mock.patch.object(self.mender, "changed", return_value=[]), \
                    mock.patch.object(self.mender, "RECORD", Path(there) / "mender.json"):
                line = self.mender.finish(held, lambda branch: ("", ""), "a", [], FREE)
        self.assertEqual(line.fields["why"], "the mender ended without committing anything on its branch")
        self.assertNotIn("declined", line.fields)


#: A careen's model frame, as manda's `model-yaml-required-item-unsatisfied.patch` carried it.
FRAME = """CR-72: the model's frame for an event events.ts already has.

diff --git a/docs/event-model/model.yaml b/docs/event-model/model.yaml
--- a/docs/event-model/model.yaml
+++ b/docs/event-model/model.yaml
@@ -1,3 +1,6 @@
   - type: evt
     name: RequiredItemSatisfied
+  - type: evt
+    name: RequiredItemUnsatisfied
+    attributes: []
"""


class ModelPatchTest(unittest.TestCase):
    mender: ClassVar[Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.mender = load()

    def test_a_frame_for_an_event_the_code_has_is_a_patch(self) -> None:
        self.assertEqual(self.mender.model_patch_refusal(FRAME, lambda name: name == "RequiredItemUnsatisfied"), "")

    def test_a_new_event_or_a_rename_is_a_decision(self) -> None:
        self.assertIn("no code on trunk has yet", self.mender.model_patch_refusal(FRAME, lambda name: False))
        renamed = FRAME.replace("     name: RequiredItemSatisfied", "-    name: RequiredItemSatisfied")
        self.assertIn("removes or renames RequiredItemSatisfied",
                      self.mender.model_patch_refusal(renamed, lambda name: True))

    def test_a_patch_to_anything_else_is_not_asked(self) -> None:
        other = FRAME.replace("docs/event-model/model.yaml", "docs/design.md")
        self.assertEqual(self.mender.model_patch_refusal(other, lambda name: False), "")


class RecordTest(unittest.TestCase):
    def test_a_need_raised_before_the_plain_line_still_reads(self) -> None:
        line = json.dumps({"v": 1, "t": "2026-11-24T15:34:50Z", "kind": "told", "fairway": "modelling",
                           "message": "m", "needs": [{"what": "w", "by": "person"}]})
        self.assertEqual(logs.read(line).fields["needs"][0], {"what": "w", "by": "person"})
        asked = json.dumps({"v": 1, "t": "2026-11-24T15:34:50Z", "kind": "question", "fairway": "modelling",
                            "slice": "S110", "id": "S110-decide-2", "what": "docs/event-model/model.yaml, per D523"})
        self.assertNotIn("plain", logs.read(asked).fields)


if __name__ == "__main__":
    unittest.main()
