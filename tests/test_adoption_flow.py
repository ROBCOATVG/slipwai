"""The adoption's steps the board takes itself: which control each is, and what each writes or starts."""
from __future__ import annotations

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

    def test_the_strategy_is_the_accepted_adr_the_gate_reads(self) -> None:
        (self.root / "adopt/docs/adr").mkdir(parents=True)
        (self.root / "adopt/docs/adr/0001-record-architecture-decisions.md").write_text("# 0001\n")
        path = flow.decide(self.root, self.layout, {"strategy": "strangler-fig", "why": "the old app must go"},
                           today="2026-10-23")
        self.assertEqual(path, "adopt/docs/adr/0002-change-strategy.md")
        text = (self.root / path).read_text()
        self.assertRegex(text, r"## Status\s*\n+\s*Accepted")
        self.assertIn("\nStrategy: strangler-fig\n", text)
        self.assertIn("the old app must go", text)

    def test_a_strategy_not_on_offer_writes_nothing(self) -> None:
        with self.assertRaises(GenerationError):
            flow.decide(self.root, self.layout, {"strategy": "big-bang"})
        self.assertFalse((self.root / "adopt/docs/adr").exists())

    def test_the_first_feature_is_the_prd_the_draft_reads(self) -> None:
        with mock.patch.object(flow.Fitting, "run"):
            fitting = flow.draft(self.root, self.layout, {"feature": "Members can export their tree"})
        self.assertIn("Members can export their tree", (self.root / "adopt/docs/prd.md").read_text())
        self.assertEqual(fitting.steps[0].argv[-1], "draft")
        with self.assertRaises(GenerationError):
            flow.draft(Path(tempfile.mkdtemp()), self.layout, {})


class StepTest(unittest.TestCase):
    def test_nothing_starts_while_something_is_running(self) -> None:
        running = mock.Mock()
        running.said.return_value = {"done": False, "lines": []}
        code, said, started = flow.take_step(Path("."), {"step": "verify"}, running)
        self.assertEqual((code, started), (409, None))


if __name__ == "__main__":
    unittest.main()
