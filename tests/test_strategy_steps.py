"""The steps a decided strategy adds to an adoption before its first specification."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import adoption_flow
from slipwai.errors import GenerationError
from slipwai.layout import Layout
from slipwai.next_steps import steps as sequence
from slipwai.origin import Adoption
from slipwai.services import App
from slipwai.strategy_steps import CONTINUE, stack_of, steps

LAYOUT = Layout("adopt")
STRANGLER = {"Freeze": "agreed — the owner", "New home": "beside apps/shop-next", "End": "all — by 2027-04-30",
             "Target": "as-is", "Parity": "every behaviour", "Checkpoint": "2027-04-30",
             "New home stack": "backend java-spring · frontend none · persistence postgres"}


def old(**commands: str) -> App:
    return App("shop", "web", "service", "java", None, 0, generated=False, commands=commands)


def decided(strategy: str, lines: dict[str, str], missing: list[str] | None = None, **record: object) -> Adoption:
    return Adoption(strategy={"decided": strategy, "lines": lines, "missing": missing or [], **record})


def actions(root: Path, adoption: Adoption, apps: list[App]) -> list[str]:
    return [action for action, _why, _done in steps(root, LAYOUT, adoption, apps)]


class StepsTest(unittest.TestCase):
    def setUp(self) -> None:
        # A folder of its own around the repository: a new repository is made beside it.
        self.root = Path(tempfile.mkdtemp()) / "shop"
        self.root.mkdir()

    def test_an_incomplete_decision_adds_nothing_the_decision_is_still_the_step(self) -> None:
        self.assertEqual(steps(self.root, LAYOUT, decided("rewrite", {}, ["Home"]), [old()]), [])
        ordered = sequence(self.root, LAYOUT, decided("rewrite", {}, ["Home"]), [old()])
        adr = next(step for step in ordered if step.action.startswith("an accepted ADR"))
        self.assertFalse(adr.done)
        self.assertIn("`Home:`", adr.why)

    def test_every_strategy_starts_with_the_build_floor_and_smoke(self) -> None:
        for strategy, lines in (("in-place", {"Target": "as-is"}), ("strangler-fig", STRANGLER),
                                ("leave-it", {"Variant": "retain", "Risk-owner": "me", "Review": "2999-01-01"})):
            with self.subTest(strategy=strategy):
                self.assertEqual(actions(self.root, decided(strategy, lines), [old()])[:2],
                                 ["the build floor, in the agent",
                                  "prove each application starts (`smoke`), in the agent"])

    def test_a_strangler_beside_generates_its_home_and_owes_the_parity_list_when_everything_moves(self) -> None:
        found = actions(self.root, decided("strangler-fig", STRANGLER), [old(smoke="make smoke")])
        self.assertIn("generate the new home", found)
        self.assertIn("the behaviour to keep, `docs/parity.md`, in the agent", found)
        partial = actions(self.root, decided("strangler-fig", {**STRANGLER, "End": "partial"}), [old()])
        self.assertNotIn("the behaviour to keep, `docs/parity.md`, in the agent", partial)
        inside = actions(self.root, decided("strangler-fig", {**STRANGLER, "New home": "inside src/next"}), [old()])
        self.assertIn("declare the modules and freeze their violations, in the agent", inside)
        self.assertNotIn("generate the new home", inside)

    def test_the_new_home_is_done_once_a_generated_service_exists(self) -> None:
        new = App("shop-next", "apps/shop-next", "service", "java", "java-spring", 3000, generated=True)
        done = {action: was for action, _why, was in steps(self.root, LAYOUT, decided("strangler-fig", STRANGLER),
                                                           [old(), new])}
        self.assertTrue(done["generate the new home"])

    def test_leaving_it_keeps_a_risk_register(self) -> None:
        found = actions(self.root, decided("leave-it", {"Variant": "retain", "Risk-owner": "me",
                                                        "Review": "2999-01-01"}), [old()])
        self.assertEqual(found[-1], "the risk register, in the agent")

    def test_a_rewrite_in_a_new_repository_hands_the_voyage_over_once_it_exists(self) -> None:
        lines = {"Home": "new-repo ../shop-rewrite", "Stack": "backend go · frontend none · persistence postgres"}
        adoption = decided("rewrite", lines)
        self.assertTrue(any(step.action.startswith("/speckit-constitution")
                            for step in sequence(self.root, LAYOUT, adoption, [old()])))
        made = self.root.parent / "shop-rewrite"
        made.mkdir(exist_ok=True)
        (made / "project.json").write_text("{}")
        ordered = sequence(self.root, LAYOUT, adoption, [old()])
        self.assertTrue(ordered[-1].action.startswith(CONTINUE))
        self.assertFalse(any(step.action.startswith("/speckit-constitution") for step in ordered),
                         "the constitution and the first feature are the new project's")

    def test_the_stack_line_is_read_back_as_its_three_answers(self) -> None:
        self.assertEqual(stack_of(STRANGLER), {"backend": "java-spring", "frontend": "none", "persistence": "postgres"})


class HomeTest(unittest.TestCase):
    def test_the_board_generates_no_home_over_changes_nobody_committed(self) -> None:
        root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        (root / "project.json").write_text(json.dumps({
            "name": "shop", "origin": "adopted", "profile": "standard", "frontend": "none", "target": "existing",
            "deployables": {}, "layout": {"delivery": "adopt"},
            "strategy": {"recommended": "strangler-fig", "decided": "strangler-fig", "lines": STRANGLER,
                         "missing": []}}))
        with self.assertRaises(GenerationError) as refused:
            adoption_flow.home(root)
        self.assertIn("commit or stash", str(refused.exception))


class PagesTest(unittest.TestCase):
    """The draft, the mock-ups and `/sail` each read the decided strategy before they place a feature."""

    def test_the_draft_specifies_where_the_strategy_says_and_overrides_a_contradiction(self) -> None:
        import command_pages
        draft = command_pages.pages("adopted")["commands/draft.md"]
        self.assertIn("the decided\n   strategy governs everything below", draft)
        self.assertIn("is overridden, and said", draft)
        self.assertIn("## Strategy fit", draft)

    def test_the_mock_ups_take_the_new_homes_look_where_the_feature_lands_there(self) -> None:
        import command_pages
        self.assertIn("drawn in the new home's UI, never the old\napp's",
                      command_pages.pages("adopted")["commands/mockups.md"])

    def test_sail_places_a_slice_by_each_of_the_four_strategies(self) -> None:
        import command_pages
        plan = command_pages.pages("adopted")["commands/sail.md"]
        for rule in ("**strangler fig, or rewrite**", "**in place**", "**leave it**", "`Target:` is modules"):
            self.assertIn(rule, plan)


if __name__ == "__main__":
    unittest.main()
