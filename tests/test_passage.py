"""Where a project stands, read off the tree: each stage's state is a file, a marker or a line, never a field.

Trees are built by hand here, one fact at a time, because that is the claim: a stage moves when the thing
that proves it appears, and only then.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.passage import current, modelled, stages

CONSTITUTION = ".specify/memory/constitution.md"


def tree(**facts: str) -> Path:
    """A project with those files in it; `__` in a name is a directory separator."""
    root = Path(tempfile.mkdtemp())
    for relative, text in facts.items():
        path = root / relative.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


INIT = {".specify__integration.json": json.dumps({"default_integration": "claude"})}


def states(root: Path, **given) -> dict[str, str]:
    return {one.key: one.state for one in stages(root, **given)}


class StagesTest(unittest.TestCase):
    def test_an_empty_tree_is_at_init_with_the_prd_stage_faint(self) -> None:
        root = tree()
        found = states(root)
        self.assertEqual(found["prd"], "skipped")
        self.assertEqual(found["init"], "todo")
        self.assertEqual(found["model"], "skipped", "the standard profile has no model stage")
        self.assertEqual(current(stages(root)).key, "init")  # type: ignore[union-attr]

    def test_each_stage_is_done_by_the_fact_that_proves_it(self) -> None:
        root = tree(**{"docs__prd.md": "# A product\n", **INIT,
                       CONSTITUTION.replace("/", "__"): "# Constitution\n\n## Principles\n",
                       "specs__001-demo__spec.md": "# Demo\n"})
        found = states(root)
        self.assertEqual([found[k] for k in ("prd", "init", "constitution", "specification")], ["done"] * 4)
        self.assertEqual(found["chart"], "todo")
        self.assertEqual(current(stages(root)).key, "chart")  # type: ignore[union-attr]
        detail = next(one.detail for one in stages(root) if one.key == "init")
        self.assertIn("claude", detail)

    def test_a_constitution_still_carrying_the_template_is_not_ratified(self) -> None:
        root = tree(**{CONSTITUTION.replace("/", "__"): "# [PRINCIPLE_1_NAME]\n"})
        self.assertEqual(states(root)["constitution"], "todo")

    def test_the_board_s_own_child_is_what_says_working_and_what_says_waiting(self) -> None:
        root = tree()
        drafting = {"step": "draft", "done": False, "code": None}
        found = states(root, receipt=drafting)
        self.assertEqual((found["constitution"], found["specification"]), ("working", "working"))
        failed = {"step": "draft", "done": True, "code": 2}
        self.assertEqual(states(root, receipt=failed)["specification"], "waiting")
        self.assertEqual(states(root, receipt={"step": "init", "done": False, "code": None})["init"], "working")
        self.assertEqual(states(root, receipt={"step": "launch", "done": False, "code": None})["chart"], "working")

    def test_the_event_profile_asks_for_a_model_before_the_chart(self) -> None:
        root = tree(**{"project.json": json.dumps({"profile": "event-modelling"}), **INIT,
                       CONSTITUTION.replace("/", "__"): "# Constitution\n",
                       "specs__001-demo__spec.md": "# Demo\n",
                       "docs__event-model__model.yaml": "version: 1\n\nslices: []\n"})
        found = stages(root)
        self.assertEqual(states(root)["model"], "todo")
        self.assertEqual(current(found).key, "model")  # type: ignore[union-attr]
        (root / "docs/event-model/model.yaml").write_text("version: 1\nslices:\n  - id: RegisterGame\n",
                                                           encoding="utf-8")
        self.assertEqual(states(root)["model"], "done")

    def test_modelled_reads_the_slices_key_as_text(self) -> None:
        for text, expected in (("slices: []\n", False), ("slices: {}\n", False), ("# slices: x\nslices:\n", False),
                               ("slices:\n  - id: A\n", True), ("slices: [A]\n", True)):
            root = tree(**{"docs__event-model__model.yaml": text})
            self.assertEqual(modelled(root), expected, text)

    def test_the_slices_stage_reads_the_fold_and_the_fleet(self) -> None:
        root = tree(**{"specs__001-demo__spec.md": "# Demo\n", "specs__001-demo__chart.yaml": "fairways: {}\n"})
        self.assertEqual(states(root, slices={"todo": 3})["chart"], "done")
        self.assertEqual(states(root, slices={"todo": 2, "working": 1})["slices"], "working")
        self.assertEqual(states(root, slices={"todo": 2, "waiting": 1})["slices"], "waiting")
        self.assertEqual(states(root, slices={"done": 2})["slices"], "done")
        self.assertEqual(states(root, slices={"done": 2}, fleet={"inbox": [{"kind": "parked"}]})["slices"], "waiting")
        found = states(root, slices={"done": 2}, fleet={"accepted": ["orders"]})
        self.assertEqual(found["accepted"], "done")
        self.assertEqual(states(root, slices={"done": 2}, fleet={"demo_due": ["orders"]})["accepted"], "working")
        self.assertEqual(states(root, slices={"todo": 2}, fleet={"running": False})["slices"], "waiting",
                         "split and nothing running is a silence a person is told about")
        self.assertIn("not running", next(one.detail for one in stages(root, slices={"todo": 2}, fleet={})
                                          if one.key == "slices"))
        self.assertEqual(states(root, slices={"todo": 2}, fleet={"running": True})["slices"], "todo")
        self.assertEqual(states(root, receipt={"step": "cruise", "done": False, "code": None},
                                slices={"todo": 2})["slices"], "working")
        self.assertEqual(states(root, slices={})["chart"], "todo")
        self.assertIn("charted, not split", next(one.detail for one in stages(root) if one.key == "chart"))


if __name__ == "__main__":
    unittest.main()
