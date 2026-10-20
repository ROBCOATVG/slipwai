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

from slipwai.passage import current, modelled, record_verdict, stages

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
        self.assertEqual(current(stages(root)).key, "storyboard",  # type: ignore[union-attr]
                         "a surface nobody has seen is cheaper to move as a drawing than as a read model")
        detail = next(one.detail for one in stages(root) if one.key == "init")
        self.assertIn("claude", detail)

    def test_a_captured_idea_is_named_on_the_specification_stage(self) -> None:
        """Another feature's spec.md does not hide an idea /sail has not finished."""
        root = tree(**{**INIT, "specs__001-demo__spec.md": "# Demo\n",
                       "docs__intake__billing__brief.md": "# Billing\n\nBilling\n"})
        stage = next(one for one in stages(root) if one.key == "specification")
        self.assertEqual(stage.state, "done")
        self.assertIn("waiting: billing", stage.detail)

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
        self.assertEqual([one.key for one in found if one.state == "todo"][:2], ["storyboard", "model"],
                         "both still to do, and the surfaces come first")
        self.assertEqual(current(found).key, "storyboard")  # type: ignore[union-attr]
        (root / "docs/event-model/model.yaml").write_text("version: 1\nslices:\n  - id: RegisterGame\n",
                                                           encoding="utf-8")
        self.assertEqual(states(root)["model"], "done")

    def test_the_storyboard_stands_before_the_model_and_is_read_from_the_states_a_person_marked(self) -> None:
        """Where `project/ladder.py` has the mock-up review, and for its reason: the screens are what the
        modelling conversation is held over. It also says what a person is waiting on while the stage runs,
        which the strip could not before — the stage stops at every surface by design, and a stage that
        waits by design looked exactly like one that had hung."""
        made = {**INIT, CONSTITUTION.replace("/", "__"): "# Constitution\n",
                "specs__001-demo__spec.md": "# Demo\n"}
        root = tree(**made)
        self.assertEqual(states(root)["storyboard"], "todo")
        self.assertEqual([one.key for one in stages(root)][3:6], ["specification", "storyboard", "model"],
                         "the ladder's order: a surface is seen before it is modelled")

        marked = ("## Surface: Catalog\n- empty \u2014 approved\n- loaded \u2014 approved\n"
                  "## Surface: Checkout\n- error \u2014 parked: which message?\n")
        root = tree(**{**made, "specs__001-demo__mockups__mock-states.md": marked})
        self.assertEqual(states(root)["storyboard"], "waiting")
        self.assertEqual(current(stages(root)).key, "storyboard")  # type: ignore[union-attr]
        self.assertIn("2 of 3 states approved, 1 parked",
                      next(one.detail for one in stages(root) if one.key == "storyboard"))

        settled = "## Surface: Catalog\n- empty \u2014 approved\n- legacy \u2014 n/a: dropped\n"
        root = tree(**{**made, "specs__001-demo__mockups__mock-states.md": settled})
        self.assertEqual(states(root)["storyboard"], "done", "approved and n/a are both settled")

    def test_surfaces_drawn_and_nothing_approved_is_waiting_on_a_person_rather_than_still_to_do(self) -> None:
        """The reading was `mock-states.md` or nothing, and that file is written at the *end* of the stage.
        Between the drawing and the verdicts — which is where the board's Draw the surfaces button leaves a
        project, and where a person is the only thing holding it up — the strip said *to do*."""
        made = {**INIT, "specs__001-demo__spec.md": "# Demo\n",
                "specs__001-demo__mockups__basket.html": "<title>Mock: Basket</title>\n"}
        root = tree(**made)
        self.assertEqual(states(root)["storyboard"], "waiting")
        self.assertIn("drawn", next(one.detail for one in stages(root) if one.key == "storyboard"))
        self.assertEqual(states(tree(**{**made, "specs__001-demo__mockups__mock-states.md":
                                        "## Surface: Basket\n- empty \u2014 approved\n"}))["storyboard"],
                         "done", "and the verdicts settle it")

    def test_a_feature_with_no_surfaces_has_run_the_stage_rather_than_skipped_it(self) -> None:
        """A written answer, not an absence."""
        root = tree(**{**INIT, "specs__001-demo__spec.md": "# Demo\n",
                       "specs__001-demo__mockups__mock-states.md": "surfaces: none\n"})
        self.assertEqual(states(root)["storyboard"], "done")
        self.assertIn("no surfaces", next(one.detail for one in stages(root) if one.key == "storyboard"))

class StoryboardVerdictTest(unittest.TestCase):
    """The voyage records the verdict the storyboard was waiting on.

    Approving marks every drawn state approved. Disapproving parks them with the reason, which is what
    keeps the stage waiting. A file of approvals nobody gave is the failure the stage exists to prevent,
    so a disapproval with nothing said is refused.
    """

    def root(self) -> Path:
        root = tree(**{
            "specs__001-demo__mockups__storyboard.html": "<title>Storyboard</title>\n",
            "specs__001-demo__mockups__index.html": "<title>Contents</title>\n",
            "specs__001-demo__mockups__discover.html": (
                "<title>Game Finder \u2014 Discover</title>\n"
                '<article class="state" id="populated"><h2>Populated</h2></article>\n'
                '<article class="state" id="empty"><h2>Nothing nearby</h2></article>\n'
            ),
        })
        return root

    def test_approving_writes_the_drawn_states_and_not_the_storyboard_page(self) -> None:
        root = self.root()
        self.assertEqual(record_verdict(root, "001-demo", "approved"), "approved")
        text = (root / "specs/001-demo/mockups/mock-states.md").read_text(encoding="utf-8")
        self.assertIn("## Surface: Discover\n- Populated \u2014 approved\n- Nothing nearby \u2014 approved\n", text)
        self.assertNotIn("Storyboard", text)
        self.assertNotIn("Contents", text)

    def test_disapproving_parks_every_state_with_the_reason(self) -> None:
        root = self.root()
        with self.assertRaises(ValueError) as refused:
            record_verdict(root, "001-demo", "parked", "  ")
        self.assertIn("why", str(refused.exception).lower())
        self.assertFalse((root / "specs/001-demo/mockups/mock-states.md").exists())
        record_verdict(root, "001-demo", "parked", "the map shows the street")
        text = (root / "specs/001-demo/mockups/mock-states.md").read_text(encoding="utf-8")
        self.assertIn("- Populated \u2014 parked: the map shows the street", text)
        self.assertEqual(states(root)["storyboard"], "waiting")

    def test_a_feature_that_was_not_drawn_cannot_be_approved(self) -> None:
        with self.assertRaises(ValueError):
            record_verdict(tree(), "../secret", "approved")


class ExpectationTest(unittest.TestCase):
    def test_every_stage_says_what_to_expect_and_whether_it_stops_for_a_person(self) -> None:
        """The other half of "where are we": at the twenty-minute mark the question is whether this is
        normal, and a stage that waits for somebody by design reads as one that has hung without this."""
        found = stages(tree(**{"project.json": json.dumps({"profile": "event-modelling"})}))
        self.assertTrue(all(one.expect for one in found), "every stage, or the card has holes in it")
        waits = {one.key for one in found if "stops for you" in one.expect}
        self.assertEqual(waits, {"model", "storyboard", "slices", "accepted"})
        self.assertNotIn("stops for you",
                         next(one.expect for one in stages(tree()) if one.key == "model"),
                         "a stage this profile has not got waits on nobody")

    def test_a_stage_this_profile_has_not_got_claims_no_file_and_nothing_to_expect(self) -> None:
        """The faint column says something worth saying — that this project is on the standard profile —
        and that is all it should say. Before this it printed `docs/event-model/model.yaml` under itself,
        which is a file the project will never have, and a line in What to expect about a non-event."""
        from slipwai.voyage_page import expect_card, stage_html

        found = stages(tree(**{**INIT, "specs__001-demo__spec.md": "# Demo\n"}))
        model = next(one for one in found if one.key == "model")
        self.assertEqual((model.state, model.detail), ("skipped", "not on this profile"))
        self.assertNotIn("model.yaml", stage_html(model, 4), "no evidence for a stage that will never be done")
        self.assertIn("Event model", stage_html(model, 4), "the column itself stays, faint")
        self.assertNotIn("not on this profile", expect_card(found))
        self.assertIn("Storyboard", expect_card(found), "the stages that will happen are all still there")

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
        reading = {"inbox": [{"kind": "decisions", "blocking": "no"}]}
        self.assertEqual(states(root, slices={"todo": 2, "working": 1}, fleet=reading)["slices"], "working",
                         "decisions to read below the ceiling hold nothing up")
        held = {"inbox": [{"kind": "decisions", "blocking": "yes"}]}
        self.assertEqual(states(root, slices={"todo": 2, "working": 1}, fleet=held)["slices"], "waiting")
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
