"""The adoption's steps the board takes itself: which control each is, and what each writes or starts."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import adoption_flow as flow
from slipwai.errors import GenerationError
from slipwai.layout import Layout


class KeyTest(unittest.TestCase):
    def test_each_step_of_the_sequence_is_known_by_its_action(self) -> None:
        self.assertEqual(flow.key_of("./adopt/init"), flow.INIT)
        self.assertEqual(flow.key_of("/ground, in the agent"), flow.GROUND)
        self.assertEqual(flow.key_of("an accepted ADR with a `Strategy:` line"), flow.STRATEGY)
        self.assertEqual(flow.key_of("/sail, in the agent"), "")

    def test_only_a_step_the_board_takes_has_a_control(self) -> None:
        self.assertIn('data-step="init"', flow.control(flow.INIT, None, "<option>claude</option>"))
        self.assertIn('value="in-place" checked', flow.control(flow.STRATEGY, "in-place", ""))
        self.assertIn('data-step="draft"', flow.control(flow.SPECIFY, None, ""))
        self.assertEqual(flow.control("", None, ""), "")


STRANGLER = {"strategy": "strangler-fig", "freeze": "agreed", "freeze_said": "the owner, 2026-10-23",
             "home": "beside", "home_path": "apps/shop-next", "end": "all", "checkpoint": "2027-04-30",
             "target": "modules in one deployable, hexagonal inside each", "backend": "java-spring",
             "frontend": "react-vite", "persistence": "postgres"}


class DecideTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.layout = Layout("adopt")
        for patched in (mock.patch.object(flow, "refuse_foreign"),
                        mock.patch.object(flow.resurvey, "writes", return_value=set()),
                        mock.patch.object(flow.resurvey, "refresh",
                                          return_value=SimpleNamespace(rewritten=["adopt/docs/convergence.md"])),
                        mock.patch.object(flow.subprocess, "run")):
            patched.start()
            self.addCleanup(patched.stop)
        (self.root / "project.json").write_text(json.dumps({
            "name": "shop", "origin": "adopted", "profile": "standard", "frontend": "none", "target": "existing",
            "deployables": {}, "layout": {"delivery": "adopt"}}))

    def test_the_reason_is_recorded_with_the_decision_and_none_is_refused(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            flow.decide(self.root, self.layout, STRANGLER)
        self.assertIn("business trigger", str(refused.exception))
        flow.decide(self.root, self.layout, {**STRANGLER, "why": "the old app must go"})
        self.assertEqual(json.loads((self.root / "project.json").read_text())["why"], "the old app must go",
                         "the gate holds a strategy with no `why` at `open`, decided or not")

    def test_the_strategy_is_the_accepted_adr_the_gate_reads(self) -> None:
        (self.root / "adopt/docs/adr").mkdir(parents=True)
        (self.root / "adopt/docs/adr/0001-record-architecture-decisions.md").write_text("# 0001\n")
        path = flow.decide(self.root, self.layout, {**STRANGLER, "why": "the old app must go"}, today="2026-10-23")
        self.assertEqual(path, "adopt/docs/adr/0002-change-strategy.md")
        text = (self.root / path).read_text(encoding="utf-8")
        self.assertRegex(text, r"## Status\s*\n+\s*Accepted")
        self.assertIn("\nStrategy: strangler-fig\n", text)
        self.assertIn("the old app must go", text)
        # Every line the strategy needs, on the ADR the record reads it from.
        for line in ("Freeze: agreed — the owner, 2026-10-23", "New home: beside apps/shop-next",
                     "End: all — the old app is deleted by 2027-04-30", "Checkpoint: 2027-04-30",
                     "New home stack: backend java-spring · frontend react-vite · persistence postgres",
                     "Build: pinned as-is"):
            self.assertIn(line, text)

    def test_a_strategy_missing_a_line_it_needs_writes_nothing_and_says_which(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            flow.decide(self.root, self.layout, {**STRANGLER, "freeze_said": "", "checkpoint": ""})
        self.assertIn("Freeze", str(refused.exception))
        self.assertIn("Checkpoint", str(refused.exception))
        self.assertFalse((self.root / "adopt/docs/adr").exists())

    def test_a_rewrite_says_why_one_cut_over_and_how_it_rolls_back(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            flow.record_lines({**STRANGLER, "strategy": "rewrite"})
        self.assertIn("Why single cut-over", str(refused.exception))
        strategy, lines = flow.record_lines({**STRANGLER, "strategy": "rewrite", "home": "new-repo",
                                             "home_path": "../shop-next", "why_cutover": "the host closes in March",
                                             "cutover_by": "the owner", "rollback": "DNS back within an hour"})
        self.assertEqual((strategy, lines["Home"], lines["Cut-over"]),
                         ("rewrite", "new-repo ../shop-next", "single — decided by the owner"))
        self.assertIn("Stack", lines)

    def test_leaving_it_names_the_risk_owner_and_the_review(self) -> None:
        strategy, lines = flow.record_lines({"strategy": "leave-it", "risk_owner": "the owner",
                                             "review": "2027-04-30"})
        self.assertEqual((lines["Variant"], lines["Target"], lines["Review"]), ("retain", "as-is", "2027-04-30"))

    def test_a_strategy_not_on_offer_writes_nothing(self) -> None:
        with self.assertRaises(GenerationError):
            flow.decide(self.root, self.layout, {"strategy": "big-bang"})
        self.assertFalse((self.root / "adopt/docs/adr").exists())

    def test_four_answers_are_the_prd_the_draft_reads(self) -> None:
        answers = {"who": "Family historians", "does": "Members can export their tree", "done": "An export opens"}
        with mock.patch.object(flow.Fitting, "run"):
            fitting = flow.draft(self.root, self.layout, answers)
        prd = (self.root / "adopt/docs/prd.md").read_text()
        self.assertIn("## Who uses it, and what for\n\nFamily historians", prd)
        self.assertNotIn("Out of scope", prd, "an optional answer left empty is not a heading over nothing")
        self.assertEqual(fitting.steps[0].argv[-2:], ["draft", "PRD=adopt/docs/prd.md"])

    def test_one_word_is_refused_before_a_session_is_spent_on_it(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            flow.draft(self.root, self.layout, {"does": "modernisation"})
        self.assertIn("who uses it", str(refused.exception))
        self.assertFalse((self.root / "adopt/docs/prd.md").exists())

    def test_a_prd_named_by_its_path_is_copied_in(self) -> None:
        mine = Path(tempfile.mkdtemp()) / "requirements.md"
        mine.write_text("# Export\n\nFamily historians export their tree.\n")
        with mock.patch.object(flow.Fitting, "run"):
            flow.draft(self.root, self.layout, {"prd": str(mine)})
        self.assertEqual((self.root / "adopt/docs/prd.md").read_text(), mine.read_text())
        with self.assertRaises(GenerationError):
            flow.draft(self.root, self.layout, {"prd": str(mine.with_name("missing.md"))})

    def test_answers_win_over_the_prd_offered_again(self) -> None:
        (self.root / "adopt/docs").mkdir(parents=True)
        (self.root / "adopt/docs/prd.md").write_text("# The first feature\n\nmodernisation\n")
        answers = {"prd": "adopt/docs/prd.md", "who": "Family historians", "does": "Export", "done": "It opens"}
        with mock.patch.object(flow.Fitting, "run"):
            flow.draft(self.root, self.layout, answers)
        self.assertIn("Family historians", (self.root / "adopt/docs/prd.md").read_text())

    def test_the_form_offers_the_prd_already_written(self) -> None:
        with mock.patch("slipwai.folder_field.asking", return_value=["osascript"]):
            page = flow.control(flow.SPECIFY, None, "", "/kept/adopt/docs/prd.md")
        self.assertIn('value="/kept/adopt/docs/prd.md"', page)
        self.assertIn('data-choose="prd"', page, "chosen with the machine's dialog, not typed")
        self.assertIn("Choose file…", page)
        self.assertEqual(page.count("<textarea"), 4)


class StepTest(unittest.TestCase):
    def test_nothing_starts_while_something_is_running(self) -> None:
        running = mock.Mock()
        running.said.return_value = {"done": False, "lines": []}
        code, said, started = flow.take_step(Path("."), {"step": "verify"}, running)
        self.assertEqual((code, started), (409, None))


class ToolingTest(unittest.TestCase):
    """The dev tooling a generated project is offered beside `./init`, offered to an adopted one too."""

    OFFERED = [("codegraph", "CodeGraph", "a code index"), ("uipro", "UI/UX Pro Max", "design rules")]

    def test_the_adopt_page_asks_beside_init(self) -> None:
        from slipwai.adopt_page import picker
        with mock.patch("slipwai.interview_page.extensions_offered", return_value=self.OFFERED):
            page = picker("/kept")
        self.assertIn('type="checkbox" name="extensions" value="codegraph"', page)
        with mock.patch("slipwai.interview_page.extensions_offered", return_value=[]):
            self.assertNotIn('name="extensions"', picker("/kept"), "none installed is no question")

    def test_the_voyage_init_step_elects_the_ones_checked_and_only_ones_installed(self) -> None:
        root = Path(tempfile.mkdtemp())
        with mock.patch.object(flow, "read_manifest", return_value={}), \
                mock.patch.object(flow, "layout_of", return_value=Layout("adopt")), \
                mock.patch.object(flow, "adopted") as started, \
                mock.patch("slipwai.interview_page.extensions_offered", return_value=self.OFFERED):
            flow.take_step(root, {"step": "init", "harness": "claude", "extensions": "codegraph,madeup"}, None)
        self.assertEqual(started.call_args.args[-1], ("codegraph",))

    def test_the_init_control_carries_the_checkboxes(self) -> None:
        self.assertIn("<b>tooling</b>", flow.control(flow.INIT, None, "", tooling="<b>tooling</b>"))


if __name__ == "__main__":
    unittest.main()
