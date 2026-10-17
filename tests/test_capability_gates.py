"""The capability gates: the readings that moved from every slice to the capability whole on 2026-10-17.

Split from `test_ladder_parts.py`, which holds the ladder's shape; this holds what the four moved readings
say and where each stays under the `open` release mode.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401
from test_ladder_parts import every_rung, rung_bodies

from slipwai.project import capability_gates, converge_stage, design_stage


class CapabilityGatesTest(unittest.TestCase):
    """The readings that run once over a whole capability, decided 2026-10-17.

    Gaps after code, the design review from screenshots and the hand's walk each read something a slice has a
    fraction of, so each found the next instalment's absence again; they moved to the capability, and back to
    every slice under `open`, where a merge reaches the actor at once. Converge and the adversary pass run at
    both, in every mode, because what slices get wrong between them no slice's own pass can read. Mutation is
    the capability's alone.
    """

    def rungs(self) -> dict[str, str]:
        return {heading: " ".join(body.split()) for heading, body in rung_bodies(every_rung()).items()}

    def test_the_gates_run_in_order_converge_first(self) -> None:
        self.assertEqual(capability_gates.GATES,
                         ("converge", "gaps", "design review", "adversary", "mutation", "the hand's walk"))
        rung = self.rungs()["Capability gates"]
        positions = [rung.index(f"**{gate}**") for gate in ("Converge", "Gaps", "Design review", "Adversary",
                                                             "Mutation", "The hand's walk")]
        self.assertEqual(positions, sorted(positions))

    def test_the_capability_converge_reuses_the_slice_rung_s_bound_and_levels(self) -> None:
        """One bound and one level list, so the two passes cannot be told different things."""
        rung = self.rungs()["Capability gates"]
        self.assertIn(f"at most {converge_stage.PASSES} passes", rung)
        self.assertIn(converge_stage.levels(), rung)
        self.assertIn("only a `CRITICAL` past the bound", rung)
        self.assertIn("the tree clean after every pass", rung)
        self.assertIn("closing the class rather than the instance", rung)
        self.assertIn("under `## Convergence`", rung)

    def test_the_slice_rung_says_converge_runs_again_over_the_capability(self) -> None:
        self.assertIn("Converge runs once more over the whole capability at *Capability gates*, in every release "
                      "mode", self.rungs()["Convergence"])

    def test_which_readings_go_back_to_the_slice_under_open_and_which_run_at_both(self) -> None:
        self.assertEqual(capability_gates.OPEN_PER_SLICE, ("gaps", "design review", "the hand's walk"))
        self.assertEqual(capability_gates.BOTH, ("converge", "adversary"))
        self.assertEqual(set(capability_gates.GATES) - set(capability_gates.OPEN_PER_SLICE)
                         - set(capability_gates.BOTH), {"mutation"})

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

    def test_converge_no_longer_traces_the_slice_diff_except_under_open(self) -> None:
        rung = self.rungs()["Convergence"]
        self.assertIn("is the capability's, once, at *Capability gates*", rung)
        self.assertIn("under the `open` release mode `/gaps` runs over the slice diff here instead", rung)

    def test_the_demo_rung_proves_examples_by_tests_and_opens_no_browser(self) -> None:
        rung = self.rungs()["Demo"]
        self.assertIn("`## Examples proven`", rung)
        self.assertIn("it stands where the hand's verdict stood", rung)
        self.assertIn("no browser is opened", rung)
        self.assertIn("Under the `open` release mode", rung)

    def test_a_slice_is_attacked_alone_only_where_identity_authority_or_money_widened(self) -> None:
        rung = self.rungs()["Adversary"]
        self.assertIn("widened identity, authority or money, or was given `--full`", rung)
        self.assertIn("a row deferring to its capability", rung)
        self.assertIn("nothing defers", rung)

    def test_the_open_mode_paragraph_says_exactly_which_move(self) -> None:
        rung = self.rungs()["Capability gates"]
        self.assertIn("Under the `open` release mode three of the gates do not wait for the capability", rung)
        self.assertIn("the gaps trace, the design review and the hand's walk run per slice", rung)
        self.assertIn("The *Adversary* rung attacks every slice its trigger table owes a pass, and nothing defers",
                      rung)
        self.assertIn("Converge, the adversary pass and mutation still run here, over the whole capability, in "
                      "every mode", rung)

    def test_the_slice_adversary_rung_keeps_the_capability_pass_under_open(self) -> None:
        self.assertIn("the capability's own pass still runs", self.rungs()["Adversary"])

    def test_the_design_review_rung_points_at_the_capability_and_keeps_open_s_reading(self) -> None:
        rung = " ".join(design_stage.design_review_stage("`apps/web`").split())
        self.assertIn("`Reviewed with capability <name>`", rung)
        self.assertIn("**Under the `open` release mode**", rung)
        self.assertIn("render each screen in `apps/web`", rung)

    def test_the_capability_rung_reviews_screens_only_where_there_is_one(self) -> None:
        with_screen = " ".join(capability_gates.capability_gates_stage(True).split())
        without = " ".join(capability_gates.capability_gates_stage(False).split())
        self.assertIn("`skills/web-interface-guidelines`", with_screen)
        self.assertIn("this project has no browser app", without)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
