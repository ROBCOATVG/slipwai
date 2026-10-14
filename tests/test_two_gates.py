"""Two gates, not one: what an increment pays for, and what runs once before the merge.

In the first attempt one `make verify` did everything, so every increment paid for lint, typecheck,
structure and the whole suite. The owner's own note in the experiment was "use full verify sparingly, it's
heavy", which is a gate nobody runs. Theme B item 9 splits it: the fast checks per increment inside a
slice, the full gate once on the rebased branch before `main`.

A generated project needs its own `unit` for that, and which of its targets are fast is the backends' to
say rather than the keel's to assume — so `fast_targets` is a protocol member with a default that answers
every backend that has nothing to add.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.assets import GUIDANCE_ROOT, TOOLKIT_ROOT
from slipwai.project import ladder
from slipwai.project.makefile import makefile
from slipwai.project.native_commands import DEFAULT_FAST, TARGETS, fast_targets
from slipwai.project.unit_targets import unit_targets
from slipwai.registry import FAST_TARGETS, PROTOCOL
from slipwai.selection import Selection
from slipwai.services import App, service_app


class FastTargetsTest(unittest.TestCase):
    def test_the_member_is_declared_and_never_required(self) -> None:
        """It arrives optional because every backend already has an answer: the test target alone."""
        self.assertIn(FAST_TARGETS, PROTOCOL)
        self.assertFalse(FAST_TARGETS.required)

    def test_the_default_is_the_test_suite_alone(self) -> None:
        """Integration, mutation, the image build and the audit belong to the gate before the merge."""
        self.assertEqual(DEFAULT_FAST, ("test",))
        for slow in ("integration", "mutation", "audit"):
            with self.subTest(target=slow):
                self.assertNotIn(slow, DEFAULT_FAST)

    def test_a_project_with_no_services_still_has_an_answer(self) -> None:
        self.assertEqual(fast_targets([]), DEFAULT_FAST)

    def test_every_default_target_is_one_the_contract_names(self) -> None:
        """A fast target that is not a target is a Makefile recipe keyed on nothing."""
        for target in DEFAULT_FAST:
            with self.subTest(target=target):
                self.assertIn(target, TARGETS)


class PerDeployableUnitTest(unittest.TestCase):
    """`make unit` is one target over every deployable, which is right for the merge and wrong for the
    increment: a Go increment paid about ninety seconds of Vitest each time on one project. A project with
    more than one deployable gets `unit-<name>` per deployable; one with one gets nothing to add."""

    def service(self, name: str, first: bool = False) -> App:
        return service_app(name, "toy-plain", 8000, Selection({}), first=first)

    def test_a_service_and_a_browser_app_each_get_their_own_fast_target(self) -> None:
        web = App("web", "apps/web", "web", "typescript", "react-vite", 5173, api="service", first=True)
        phony, targets = unit_targets([self.service("service", first=True), web])
        self.assertEqual(phony, "unit-service unit-web")
        self.assertIn("unit-service: ## The fast tests of apps/service alone", targets)
        self.assertIn("unit-web: ## The fast tests of apps/web alone", targets)
        self.assertIn("npm --workspace apps/web test", targets)
        self.assertNotIn("npm --workspace", targets.split("unit-web:")[0])

    def test_two_services_each_get_their_own_and_the_makefile_carries_them(self) -> None:
        apps = [self.service("orders", first=True), self.service("billing")]
        written = makefile("shop", "standard", apps)
        self.assertIn(".PHONY: unit unit-orders unit-billing test", written)
        self.assertIn("\nunit-orders: ## The fast tests of apps/orders alone", written)
        self.assertIn("\nunit-billing: ## The fast tests of apps/billing alone", written)
        self.assertNotIn("apps/billing", written.split("unit-orders:")[1].split("unit-billing:")[0])

    def test_one_deployable_has_unit_and_nothing_to_add(self) -> None:
        alone = [self.service("service", first=True)]
        self.assertEqual(unit_targets(alone), ("", ""))
        self.assertNotIn("unit-service", makefile("shop", "standard", alone))

    def test_the_rung_and_the_brief_name_the_owning_target(self) -> None:
        rung = " ".join(ladder.sail_ladder(event=True, apps=[], target="aws").split())
        self.assertIn("`make unit-<name>`", rung)
        brief = (TOOLKIT_ROOT / "agents/sail-implement-shipwright.md").read_text(encoding="utf-8")
        self.assertIn("{{make}} unit-<name>", brief)


class LadderGateTest(unittest.TestCase):
    def rungs(self) -> dict[str, str]:
        import re
        written = ladder.sail_ladder(event=True, apps=[], target="aws")
        parts = re.split(r"^(?=\d+\. \*\*)", written, flags=re.MULTILINE)
        found = {}
        for part in parts:
            match = re.match(r"^\d+\. \*\*(.+?)\*\*", part)
            if match:
                found[match.group(1)] = " ".join(part.split())
        return found

    def test_the_increment_runs_the_fast_checks_and_says_the_full_gate_is_the_merge_s(self) -> None:
        implement = self.rungs()["Implementation"]
        self.assertIn("make unit", implement)
        self.assertIn("never the full gate, which belongs to the merge", implement)

    def test_only_the_merge_rung_runs_the_full_gate(self) -> None:
        """The habit version 2 drops: an increment that pays for the whole suite."""
        rungs = self.rungs()
        self.assertIn("make verify", rungs["Merge to main"])
        for heading, body in rungs.items():
            if heading in {"Merge to main", "Principles"}:
                continue
            with self.subTest(rung=heading):
                self.assertNotIn("make verify", body)


class GeneratedGuidanceTest(unittest.TestCase):
    """The rule lives where a slice in that project will read it, not in the keel's own repository.

    And it names the line the architecture already draws rather than a second one: a test needing a real
    database, process or network is exercising an adapter, so it is an integration test by construction.
    The first draft of this reached for the keel's own mechanism — an explicit list of slow modules — which
    the keel needs because it has no adapters to put them behind, and a product does not.
    """

    def guidance(self) -> str:
        """The page as a project receives it, read from the asset it is now written in.

        This read the module's source until slice 16.3 moved the page into `assets/guidance/agents.md`.
        The asset rather than a rendered page because every line asked about here is standing text: a
        rendering would need a project built to carry it, and would be asking the same file one hop later.
        """
        return " ".join((GUIDANCE_ROOT / "agents.md").read_text(encoding="utf-8").split())

    def test_a_project_is_told_its_two_gates_and_which_runs_when(self) -> None:
        text = self.guidance()
        self.assertIn("Two gates, not one", text)
        self.assertIn("Every increment inside a slice", text)
        self.assertIn("before the merge to `main`", text)

    def test_the_fast_half_stays_fast_by_where_a_test_lives(self) -> None:
        text = self.guidance()
        self.assertIn("real database, a real process or the network is exercising an adapter", text)
        self.assertIn("it is an integration test", text)

    def test_it_says_what_happens_when_the_unit_suite_creeps(self) -> None:
        """Because the consequence is the thing worth knowing, not the rule."""
        self.assertIn("version 1's single `make verify` back again", self.guidance())

    def test_the_gate_that_keeps_the_layers_apart_is_named(self) -> None:
        self.assertIn("check-imports", self.guidance())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
