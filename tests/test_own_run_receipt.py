"""A stage this board started is this board's run, and its receipt says so on every window.

The marker a model or drawing stage writes is for a run started elsewhere — a terminal, another board — and
the receipt falls back to its one-line stand-in only where this board holds no run of its own. On 2026-11-06
the Voyage showed that stand-in for a model this very board had started: the board had asked the project's
old model script for its prompt, and the script, written before `--prompt`, ignored the flag and ran the
stage, writing the marker while the board held nothing yet. These prove the receipt is the board's own from
the first poll, over the protocol and headless, on the window that started it and on one opened by path.
"""
from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path

import checkout_packages  # noqa: F401
from test_bridge import LandingTest


class OwnRunReceiptTest(LandingTest):
    """A stage this board started over the protocol is this board's run, and its receipt says so — on the
    window that started it, and on a window opened on the project by path."""

    def test_the_receipt_is_the_run_s_own_lines_not_the_marker_s_stand_in(self) -> None:
        import sys
        from unittest import mock

        from slipwai import stage_session, stage_steps
        from slipwai.board_settings import Launch

        self._storyboard("event-modelling")
        agent = Path(__file__).resolve().parent / "fixtures" / "acp_agent.py"
        stand_in = Launch("stand-in", "Stand-in", (sys.executable, str(agent)), "a script")
        with mock.patch.object(stage_session, "launchable", return_value=stand_in), \
                mock.patch.object(stage_steps, "model_prompt", return_value="slow"):
            self.assertEqual(self.post("/storyboard", {"feature": "001-demo", "verdict": "approved"})[0], 200)
            for _ in range(200):  # the stand-in waits on a permission card, so the run is under way
                if (self.made / ".slipwai" / "model-next.pid").is_file():
                    break
                time.sleep(0.05)
            begun = "On stand-in 0.1, over the Agent Client Protocol, model A."
            receipt: dict = {}
            for _ in range(200):
                receipt = json.loads(self.get("/init.json")[1])
                if begun in receipt["lines"]:
                    break
                time.sleep(0.05)
            self.assertIn(begun, receipt["lines"])
            self.assertEqual(receipt["step"], "model")
            page = self.get("/voyage")[1]
            self.assertNotIn("has not got its log", page, "the run is this board's, not somebody else's")
            self.assertIn("over the Agent Client Protocol", page)
            # A second window opened on the project by path sees the same run.
            self.get(f"/voyage?look={urllib.parse.quote(str(self.made))}", seat="")
            other = next(seat for seat, held in self.seats().items() if held.root == self.made.resolve()
                         and seat != self.seat)
            page = self.get("/voyage", seat=other)[1]
            self.assertNotIn("has not got its log", page, "a window opened by path sees this board's run too")
            self.assertEqual(self.post("/stage/cancel", {})[0], 200)

    def test_a_headless_model_this_board_started_is_its_own_run_from_the_first_poll(self) -> None:
        """The headless child writes the marker itself, early; the board's receipt is still the child's."""
        self._storyboard("event-modelling")
        (self.made / "Makefile").write_text(
            "model-next:\n\t@mkdir -p .slipwai && printf '%s\\n' $$$$ > .slipwai/model-next.pid && echo modelling "
            "&& sleep 2 && rm -f .slipwai/model-next.pid\n", encoding="utf-8")
        self.assertEqual(self.post("/storyboard", {"feature": "001-demo", "verdict": "approved"})[0], 200)
        seen = []
        for _ in range(30):
            page = self.get("/voyage")[1]
            receipt = json.loads(self.get("/init.json")[1])
            seen.append(("has not got its log" in page, receipt["step"], bool(receipt.get("lines"))))
            if receipt["done"]:
                break
            time.sleep(0.1)
        self.assertFalse(any(stand_in for stand_in, _, _ in seen), seen)
        self.assertTrue(all(step == "model" for _, step, _ in seen), seen)

