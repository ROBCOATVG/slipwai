"""Continue the build on a further feature: refused until that feature is drawn and modelled (#131).

Split from `test_bridge.py`, which is at its claimed budget; the fixture is its landed board, made the same way here.
"""
from __future__ import annotations

import importlib
import json
import tempfile
import time
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401
from board_fixture import BoardTest


class FurtherFeatureLaunchTest(BoardTest):
    def setUp(self) -> None:
        super().setUp()
        self.made = Path(tempfile.mkdtemp()) / "demo"
        self.made.mkdir()
        module = importlib.import_module("slipwai.bridge")
        for name, with_this in (("generate", lambda answers, root: (True, f"created: {self.made}")),
                                ("destination", lambda answers, root: self.made)):
            self.addCleanup(setattr, module, name, getattr(module, name))
            setattr(module, name, with_this)

    def _until(self, step: str) -> dict:
        receipt: dict = {}
        for _ in range(100):
            receipt = json.loads(self.get("/init.json")[1])
            if receipt["done"] and receipt["step"] == step:
                break
            time.sleep(0.05)
        return receipt

    def _storyboard(self, profile: str) -> None:
        """A landed project with one feature specified and drawn, as `test_bridge.LandingTest` makes one."""
        self.post("/generate/run", {"name": "demo", "init": "none"})
        for _ in range(100):
            if json.loads(self.get("/init.json")[1])["done"]:
                break
            time.sleep(0.05)
        (self.made / "project.json").write_text(json.dumps({"profile": profile}), encoding="utf-8")
        home = self.made / "specs/001-demo"
        (home / "mockups").mkdir(parents=True)
        (home / "spec.md").write_text("# Demo\n", encoding="utf-8")
        (home / "mockups/discover.html").write_text(
            "<html><head><title>Demo \u2014 Discover</title></head>"
            '<body><article class="state"><h2>Populated</h2></article></body></html>', encoding="utf-8")
        (self.made / "Makefile").write_text("surfaces:\n\t@echo 'drawing $(FEATURE) again'\n", encoding="utf-8")

    def test_a_further_feature_is_not_launched_on_the_first_feature_s_model_and_chart(self) -> None:
        """A project that had built one feature launched its next in a second: the model named a slice and a
        chart named a slice, so nothing held Continue the build back and the fleet was cast off on a chart with
        nothing left in it (#131). What is asked is whether the feature in hand is modelled, and it is drawn first."""
        self._storyboard("event-modelling")
        (self.made / "docs/event-model").mkdir(parents=True, exist_ok=True)
        (self.made / "docs/event-model/model.yaml").write_text("slices:\n  - id: S1\n", encoding="utf-8")
        (self.made / "specs/001-demo/chart.yaml").write_text("slices:\n  S1:\n    fairway: a\n", encoding="utf-8")
        (self.made / "specs/001-demo/mockups/mock-states.md").write_text(
            "- Discover \u00b7 Populated \u2014 approved\n", encoding="utf-8")
        (self.made / "specs/002-more").mkdir()
        (self.made / "specs/002-more/spec.md").write_text("# More\n", encoding="utf-8")
        (self.made / ".specify").mkdir(exist_ok=True)
        (self.made / ".specify/feature.json").write_text(
            json.dumps({"feature_directory": "specs/002-more"}), encoding="utf-8")
        found = json.loads(self.get("/voyage.json")[1])
        self.assertFalse(found["launchable"], "the first feature's model is not this feature's")
        self.assertTrue(found["drawable"], "its storyboard is the next step, whatever was drawn before it")
        self.assertFalse(found["modelable"], "and its model waits on that storyboard's verdict, not an earlier one's")
        code, said = self.post("/launch", {})
        self.assertEqual(code, 400)
        self.assertIn("specs/002-more is not in the model yet", said)
        self.assertEqual(self.post("/draw", {}), (200, "drawing the surfaces"))
        self.assertIn("drawing 002-more again", self._until("surfaces")["lines"])


if __name__ == "__main__":
    unittest.main()
