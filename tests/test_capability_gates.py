"""The capability gates: the readings that need a whole capability, decided 2026-10-17.

Split from `test_ladder_parts.py`, which holds the ladder's shape; this holds what the gates say, what a slice
keeps, and what still runs per slice under the `open` release mode.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from test_ladder_parts import every_rung, headings, rung_bodies

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project import capability_gates, converge_stage, design_stage


def flat(text: str) -> str:
    return " ".join(text.split())


class CapabilityGatesTest(unittest.TestCase):
    """Converge, gaps, the design review, the adversary pass, mutation and the hand's walk, once per capability.

    Each reads something a slice has a fraction of. Converge asks whether the code does what the specification
    requires, which has its answer only once the slices sharing a requirement are built; the adversary pass
    runs only where a slice widened something; under `open`, where a merge reaches the actor at once, four
    readings run per slice as well.
    """

    def rungs(self) -> dict[str, str]:
        return {heading: flat(body) for heading, body in rung_bodies(every_rung()).items()}

    def test_the_gates_run_in_order_converge_first(self) -> None:
        self.assertEqual(capability_gates.GATES,
                         ("converge", "gaps", "design review", "adversary", "mutation", "the hand's walk"))
        rung = self.rungs()["Capability gates"]
        positions = [rung.index(f"**{gate}**") for gate in ("Converge", "Gaps", "Design review", "Adversary",
                                                             "Mutation", "The hand's walk")]
        self.assertEqual(positions, sorted(positions))

    def test_the_converge_gate_carries_the_bound_the_reopen_rules_and_the_levels(self) -> None:
        """The rules that governed the slice's rung govern the gate now, written once in `converge_stage`."""
        rung = self.rungs()["Capability gates"]
        self.assertIn(flat(converge_stage.convergence_gate()), rung)
        self.assertIn(f"at most {converge_stage.PASSES} passes", rung)
        self.assertIn(converge_stage.levels(), rung)
        self.assertIn("an open `CRITICAL` finding re-opens the loop however many passes have run", rung)
        self.assertIn("the tree is clean before anything else runs", rung)
        self.assertIn("Each appended task closes the class, not the instance", rung)
        self.assertIn("under `## Convergence`", rung)

    def test_convergence_is_no_rung_of_the_slice(self) -> None:
        self.assertNotIn("Convergence", headings(every_rung()))
        rung = self.rungs()["Implementation"]
        self.assertIn("the slice goes straight on to its examples: convergence is the capability's first gate", rung)
        self.assertIn("this slice converges here", rung, "under `open` the slice still converges")

    def test_the_record_is_keyed_by_the_capability_and_cleared_is_what_makes_a_demo_due(self) -> None:
        rung = self.rungs()["Capability gates"]
        self.assertIn(capability_gates.GATES_FILE, rung)
        self.assertIn("`Cleared: <date> · <commit>`", rung)

    def test_findings_above_the_bar_close_before_the_person_s_demo(self) -> None:
        rung = self.rungs()["Capability gates"]
        self.assertIn("fixed **before the person's demo**, in a follow-up slice in the same fairway", rung)
        self.assertIn("stowed to the careen", rung)
        self.assertIn("an open `CRITICAL` is the next slice", rung)

    def test_keystone_gates_the_last_slice_before_the_merge_that_lights_it(self) -> None:
        self.assertIn("under the `keystone` release mode on the last slice's branch before its merge",
                      self.rungs()["Capability gates"])

    def test_the_demo_rung_proves_examples_by_tests_and_opens_no_browser(self) -> None:
        rung = self.rungs()["Demo"]
        self.assertIn("`## Examples proven`", rung)
        self.assertIn("it stands where the hand's verdict stood", rung)
        self.assertIn("no browser is opened", rung)
        self.assertIn("Under the `open` release mode", rung)


class AdversaryTest(unittest.TestCase):
    """No slice is attacked: it records which triggers it widened, and the capability is attacked only then."""

    def rungs(self) -> dict[str, str]:
        return {heading: flat(body) for heading, body in rung_bodies(every_rung()).items()}

    def test_the_slice_rung_is_a_trigger_record_and_attacks_nothing(self) -> None:
        rung = self.rungs()["Attack surface"]
        self.assertIn("**Nothing is attacked here**, `--full` included", rung)
        self.assertIn("trigger record", rung)

    def test_the_capability_is_attacked_only_where_a_slice_widened(self) -> None:
        rung = self.rungs()["Capability gates"]
        self.assertIn("**only where at least one of its slices' trigger records has a trigger `widened`**", rung)
        self.assertIn("the gate writes a skip row naming the trigger records it relied on, and the skip clears it",
                      rung)

    def test_the_split_closing_override_is_gone(self) -> None:
        page = flat((TOOLKIT_ROOT / "commands/adversary.md").read_text(encoding="utf-8"))
        self.assertIn("The slice that closes a feature's split no longer takes a full pass of its own", page)
        self.assertNotIn("takes a full pass whether or not the trigger fired", page)

    def test_under_open_only_authorisation_identity_or_money_is_attacked_per_slice(self) -> None:
        """"Anything not covered would be dark" — everywhere but `open`, a flag or a keystone holds it back."""
        rung = self.rungs()["Attack surface"]
        self.assertIn("the authorisation, identity or money trigger `widened` is attacked here as well", rung)
        self.assertIn("nothing else is", rung)
        self.assertIn("held back by a flag or a keystone", rung)


class OpenModeTest(unittest.TestCase):
    def test_which_readings_run_per_slice_under_open_and_which_at_the_capability_always(self) -> None:
        self.assertEqual(capability_gates.OPEN_PER_SLICE, ("converge", "gaps", "design review", "the hand's walk"))
        self.assertEqual(capability_gates.EVERY_MODE, ("converge", "adversary", "mutation"))

    def test_the_open_mode_paragraph_says_exactly_which_move(self) -> None:
        rung = flat(rung_bodies(every_rung())["Capability gates"])
        self.assertIn("Under the `open` release mode four of the gates do not wait for the capability", rung)
        self.assertIn("converge, the gaps trace, the design review and the hand's walk run per slice", rung)
        self.assertIn("attacks a slice whose record has the authorisation, identity or money trigger `widened`",
                      rung)
        self.assertIn("Converge, the adversary pass and mutation still run here, over the whole capability, in "
                      "every mode", rung)


class ScopeTest(unittest.TestCase):
    """A slice's own reviews read only what it added or changed; that is what keeps a slice small."""

    def test_the_review_rung_is_scoped_to_the_slice_s_diff(self) -> None:
        rung = flat(rung_bodies(every_rung())["Review and reshape"])
        self.assertIn("**The review is scoped to what the slice added or changed**", rung)
        self.assertIn("`git diff <merge-base>...HEAD`", rung)
        self.assertIn("every finding points at an added or changed line", rung)
        self.assertIn("noted for the capability gates or stowed to the careen, and never fixed here", rung)
        self.assertIn("only code the slice added or changed, never a neighbour", rung)

    def test_the_screen_design_rung_is_scoped_to_the_slice_s_screens(self) -> None:
        rung = flat(design_stage.screen_design_stage("`apps/web`"))
        self.assertIn("**The rung is scoped to what the slice adds or changes**", rung)
        self.assertIn("only the elements it changes", rung)
        self.assertIn("An untouched screen is not restyled here", rung)
        self.assertIn("recorded for the capability's design review", rung)

    def test_the_review_brief_carries_the_same_scope(self) -> None:
        brief = flat((TOOLKIT_ROOT / "agents/sail-review-mate.md").read_text(encoding="utf-8"))
        self.assertIn("**Your scope is what the slice added or changed, and nothing else.**", brief)
        self.assertIn("`git diff <merge-base>...HEAD`", brief)
        self.assertIn("Every finding points at a line the slice added or changed", brief)

    def test_the_design_review_rung_points_at_the_capability_and_keeps_open_s_reading(self) -> None:
        rung = flat(design_stage.design_review_stage("`apps/web`"))
        self.assertIn("`Reviewed with capability <name>`", rung)
        self.assertIn("**Under the `open` release mode**", rung)
        self.assertIn("and nothing it did not touch", rung)

    def test_the_capability_rung_reviews_screens_only_where_there_is_one(self) -> None:
        with_screen = flat(capability_gates.capability_gates_stage(True))
        without = flat(capability_gates.capability_gates_stage(False))
        self.assertIn("`skills/web-interface-guidelines`", with_screen)
        self.assertIn("this project has no browser app", without)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
