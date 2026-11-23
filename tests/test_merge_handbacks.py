"""A hand-back that needs the slice's own code lands with the slice's merge, and a product question is not the
mender's (issue #154, fix 5).

manda's slices handed back changes to files they may not write as prose needs, and the mender landed each on
trunk on its own, usually before the slice merged. 43 of those jobs failed: about twenty needed the slice's own
unmerged code ("they have to land together"), fifteen landed and then failed the full gate, a few cited what
only the slice's branch held, and six asked for a follow-up slice — a product decision the mender rightly
refused, at a session's cost each. Here a hand-back is a patch in the slice's record, applied on the rebased
slice at its merge and gated with it, and a decision goes down the question path.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401
from captain_fixture import CHART
from harbourmaster_fixture import AGENTS, MergeFixture

from slipwai import logs
from slipwai.assets import TOOLKIT_ROOT

HOME = "specs/ordering/slices/ORD-01/handback"


def load_mender() -> Any:
    sys.path.insert(0, str(AGENTS))
    spec = importlib.util.spec_from_file_location("mender_handbacks", AGENTS / "mender.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HandbackMergeTest(MergeFixture):
    def write(self, path: str, body: str) -> None:
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        # LF on every platform: the patch is diffed from these files, and Windows text mode would write CRLF.
        (self.root / path).write_text(body, encoding="utf-8", newline="\n")

    def on_trunk(self, path: str, body: str) -> None:
        self.git("checkout", "--quiet", "main")
        self.write(path, body)
        self.commit(f"trunk has {path}")

    def slice_with(self, name: str, path: str, before: str, after: str, why: str = "") -> None:
        """A slice branch that changes its own code and carries a hand-back of `path`, made the way
        `sail.md` says: the change made in the berth, diffed into the record, and put back."""
        self.git("checkout", "--quiet", "-b", "slice/ORD-01", "main")
        self.write("service.txt", "one\ntwo\n")
        self.write(path, after)
        diff = self.git("diff", "--", path).stdout if (self.root / path).exists() and before else \
            self.git("diff", "--no-index", "--", "/dev/null", path).stdout
        if before:
            self.write(path, before)
        else:
            (self.root / path).unlink()
        self.write(f"{HOME}/{name}.patch", (f"{why}\n\n" if why else "") + diff)
        self.commit("ORD-01")
        self.git("checkout", "--quiet", "-b", "parked-elsewhere", "slice/ORD-01")

    def test_the_patch_is_applied_on_the_rebased_slice_and_lands_with_it(self) -> None:
        self.on_trunk("docs/design.md", "# Design\n")
        self.slice_with("design", "docs/design.md", "# Design\n", "# Design\n\nThe two pattern, from ORD-01.\n",
                        why="The page names the pattern ORD-01's code introduces.")
        self.ask("ORD-01")
        done = self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "granted", f"{answer.fields}\n{done.stderr}")
        self.assertEqual(self.git("show", "main:docs/design.md").stdout, "# Design\n\nThe two pattern, from ORD-01.\n")
        self.assertEqual(self.git("show", "main:service.txt").stdout, "one\ntwo\n")
        self.assertEqual(answer.fields["handbacks"], [f"{HOME}/design.patch"])
        said = self.git("log", "-1", "--format=%B", "main").stdout
        self.assertIn("ORD-01: land the hand-backs it carried", said)
        self.assertIn("The page names the pattern ORD-01's code introduces.", said)

    def test_one_gate_runs_over_both_and_its_failure_refuses_both(self) -> None:
        """The combined change is what is gated: the slice alone passes here, and with its hand-back fails."""
        (self.root / "Makefile").write_text(
            "verify:\n\t@if grep -q broken docs/design.md; then echo 'check-design: broken'; exit 1; fi\n",
            encoding="utf-8")
        self.on_trunk("docs/design.md", "# Design\n")
        self.slice_with("design", "docs/design.md", "# Design\n", "# Design\nbroken\n")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused")
        self.assertIn("with its hand-backs", str(answer.fields["why"]))
        self.assertIn("check-design: broken", str(answer.fields["why"]))
        self.assertTrue(answer.fields["resolve"])
        self.assertEqual(self.git("show", "main:service.txt").stdout, "one\n", "the slice did not land either")
        self.assertEqual(self.git("show", "main:docs/design.md").stdout, "# Design\n")

    def test_a_patch_that_no_longer_applies_refuses_the_slice_with_it(self) -> None:
        self.on_trunk("docs/design.md", "# Design\n")
        self.slice_with("design", "docs/design.md", "# Design\n", "# Design\nmore\n")
        self.on_trunk("docs/design.md", "# Another heading altogether\n")
        self.git("checkout", "--quiet", "parked-elsewhere")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused")
        self.assertIn(f"{HOME}/design.patch does not apply", str(answer.fields["why"]))
        self.assertTrue(answer.fields["resolve"], "writing the patch again is the berth's to do")
        self.assertEqual(self.git("show", "main:service.txt").stdout, "one\n")

    def test_a_patch_to_the_cloud_or_a_gate_is_not_applied_and_stays_a_person_s(self) -> None:
        for path, before in (("infra/bootstrap/main.tf", "# grants\n"), ("Makefile", self.GATE)):
            with self.subTest(path=path):
                self.setUp()
                if path != "Makefile":
                    self.on_trunk(path, before)
                self.slice_with("grant", path, before, before + "# ses:SendEmail\n")
                self.ask("ORD-01")
                done = self.run_once()
                answer = self.answer()
                self.assertEqual(answer.kind, "granted", f"{answer.fields}\n{done.stderr}")
                self.assertEqual(self.git("show", f"main:{path}").stdout, before)
                self.assertNotIn("handbacks", answer.fields)
                self.assertIn(f"{HOME}/grant.patch", answer.fields["withheld"][0])

    def test_a_slice_with_no_hand_back_merges_as_it_did(self) -> None:
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "granted")
        self.assertNotIn("handbacks", answer.fields)
        self.assertEqual(self.git("log", "-1", "--format=%s", "main").stdout.strip(), "ORD-01")


class PatchRuleTest(unittest.TestCase):
    """What a hand-back patch may touch, read off the patch itself."""

    mender: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.mender = load_mender()

    def test_every_path_a_patch_touches_is_read_from_its_headers(self) -> None:
        patch = ("Why: the page.\n\ndiff --git a/docs/design.md b/docs/design.md\n--- a/docs/design.md\n"
                 "+++ b/docs/design.md\n@@ -1 +1 @@\n-x\n+y\n"
                 "diff --git a/old.txt b/infra/new.tf\nrename from old.txt\nrename to infra/new.tf\n")
        self.assertEqual(self.mender.patched_paths(patch), ["docs/design.md", "old.txt", "infra/new.tf"])
        self.assertEqual(self.mender.reason_of(patch), "Why: the page.")

    def test_a_gate_and_the_cloud_are_withheld_and_the_flag_line_is_not(self) -> None:
        for path in ("Makefile", "scripts/check-x.py", ".github/workflows/v.yml", "infra/bootstrap/main.tf"):
            with self.subTest(path=path):
                self.assertNotEqual(self.mender.withheld(["docs/design.md", path]), "")
        for path in ("docs/design.md", "specs/f/mockups/mock-states.md", ".env.example",
                     "infra/service/flags.auto.tfvars", "skills/run-the-app/SKILL.md", "apps/web/src/styles/x.css"):
            with self.subTest(path=path):
                self.assertEqual(self.mender.withheld([path]), "")


class DecisionNeedTest(unittest.TestCase):
    """A need that asks for a new slice or a model decision goes to whoever decides, never to the mender."""

    mender: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.mender = load_mender()

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        shutil.copytree(TOOLKIT_ROOT / "scripts/agents", self.root / "scripts/agents")
        (self.root / "project.json").write_text(json.dumps({"layout": {"delivery": "."}}), encoding="utf-8")
        (self.root / "specs/ordering").mkdir(parents=True)
        (self.root / "specs/ordering/chart.yaml").write_text(CHART, encoding="utf-8")
        self.log = logs.deck_path(self.root, "ordering", "ORD")
        self.log.parent.mkdir(parents=True)
        self.log.write_text(logs.entry("claimed", fairway="ORD", slice="ORD-01").line(), encoding="utf-8")

    def tell(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self.root / "scripts/agents/fleet.py"), "tell", "ORD", *argv],
                              capture_output=True, text=True, cwd=self.root, check=False)

    def lines(self, kind: str) -> list[logs.Entry]:
        return [e for e in logs.fold(self.log.read_text(encoding="utf-8").splitlines()) if e.kind == kind]

    def test_a_decide_need_is_asked_as_a_question_against_the_slice(self) -> None:
        done = self.tell("--slice", "ORD-01", "--need", "a follow-up slice that mails the reminder",
                         "--check", "decide", "the reminder needs an event nobody has named")
        self.assertEqual(done.returncode, 0, done.stderr)
        need = self.lines("told")[-1].fields["needs"][0]
        self.assertEqual((need["by"], need["decide"], need["question"]), ("person", True, "ORD-01-decide-1"))
        question = self.lines("question")[-1].fields
        self.assertEqual((question["slice"], question["id"]), ("ORD-01", "ORD-01-decide-1"))
        self.assertIn("a follow-up slice that mails the reminder", question["what"])
        self.assertEqual(self.mender.eligible(need, True), "", "the mender never takes a decision")

    def test_a_need_checked_in_the_chart_or_the_model_is_a_decision_too(self) -> None:
        for path in ("specs/ordering/chart.yaml", "docs/event-model/model.yaml"):
            with self.subTest(path=path):
                done = self.tell("--slice", "ORD-01", "--need", "ORD-09 on the chart", "--check",
                                 f"text:{path}:ORD-09", "a new slice is needed")
                self.assertEqual(done.returncode, 0, done.stderr)
                need = self.lines("told")[-1].fields["needs"][0]
                self.assertTrue(need["decide"])
                self.assertEqual(need["check"]["path"], path, "the chart gaining it still ticks it")
                self.assertEqual(self.mender.eligible(need, True), "")
                self.assertEqual(self.lines("question")[-1].fields["id"], need["question"])

    def test_a_decision_needs_a_slice_to_be_asked_against(self) -> None:
        done = self.tell("--need", "a new slice", "--check", "decide", "nobody said which")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("--slice", done.stderr)

    def test_a_change_to_a_shared_surface_is_still_the_mender_s(self) -> None:
        done = self.tell("--slice", "ORD-01", "--need", "the pattern in docs/design.md", "--check",
                         "text:docs/design.md:two", "the page is the host's")
        self.assertEqual(done.returncode, 0, done.stderr)
        need = self.lines("told")[-1].fields["needs"][0]
        self.assertNotIn("decide", need)
        self.assertEqual(self.lines("question"), [])
        self.assertEqual(self.mender.eligible(need, False), "docs/design.md")


class DecisionTicksTheNeedTest(MergeFixture):
    def test_the_decision_that_answers_the_question_meets_the_need(self) -> None:
        told_at = "2026-11-23T09:00:00Z"
        self.deck("ordering", "ORD", logs.entry(
            "told", fairway="ORD", slice="ORD-01", by="session", t=told_at, message="a follow-up slice",
            needs=[{"what": "a follow-up slice", "by": "person", "decide": True, "question": "ORD-01-decide-1"}]),
            logs.entry("question", fairway="ORD", slice="ORD-01", id="ORD-01-decide-1", what="a follow-up slice",
                       t=told_at))
        self.run_once()
        self.assertEqual([e for e in self.harbour() if e.kind == "need-met"], [])
        self.deck("ordering", "ORD", logs.entry("decision", fairway="ORD", slice="ORD-01", id="ORD-01-decide-1",
                                                what="D9: ORD-09 follows, in the careen"))
        self.run_once()
        met = [e.fields for e in self.harbour() if e.kind == "need-met"]
        self.assertEqual(len(met), 1, met)
        self.assertIn("D9: ORD-09 follows", str(met[0]["how"]))
        self.assertEqual([e.fields["told"] for e in self.harbour() if e.kind == "told-met"], [told_at])


if __name__ == "__main__":
    unittest.main()
