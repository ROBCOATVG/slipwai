"""The careen: where work goes when a slice may not carry it and may not drop it.

The first attempt had no such place, so work went two ways and both were wrong. Gaps were carried — 18 from
S08 to S09, 31 from S09 to S13, 46 from S12 to S13, until two whole slices existed only to collect the debt
— and a slice that inherits a gap pays for it without having chosen to. Or findings were argued: 129
adversary findings over 21 rounds, 64 of them LOW and most about wording, with S20 still ending on five
open. Neither is a decision about whether the work matters.

So there is a named destination and a bar. Below the bar a finding is stowed with the slice that found it,
and the slice merges. At or above it, it closes first. A CRITICAL is never stowed at all.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import telegraph
from slipwai.assets import TOOLKIT_ROOT
from slipwai.project import adversary, careen, harbour, mutation
from slipwai.selection import Selection
from slipwai.services import service_app

# One event-sourced service, so the adversary page carries the rows the rung with the most of them has.
# The page is read here for what it says about the bar and the careen, neither of which is per rung.
SOURCED = [service_app("orders", "toy-plain", 3000, Selection({"write-model": "events"}), first=True)]


def flat(text: str) -> str:
    return " ".join(text.split())


class BarTest(unittest.TestCase):
    def test_the_bar_defaults_to_medium(self) -> None:
        """The experiment's LOWs were genuinely wording and its MEDIUMs genuinely were not."""
        self.assertEqual(careen.DEFAULT_BAR, "MEDIUM")

    def test_a_finding_at_or_above_the_bar_closes_before_the_merge(self) -> None:
        for severity in ("MEDIUM", "HIGH", "CRITICAL"):
            with self.subTest(severity=severity):
                self.assertTrue(careen.above_bar(severity))
                self.assertFalse(careen.stowable(severity))

    def test_a_finding_below_the_bar_is_stowed_rather_than_argued(self) -> None:
        self.assertFalse(careen.above_bar("LOW"))
        self.assertTrue(careen.stowable("LOW"))

    def test_a_critical_is_never_stowed_whatever_the_bar_says(self) -> None:
        """Data of one actor reaching another is not a thing to look at later."""
        self.assertFalse(careen.stowable("CRITICAL", bar="CRITICAL"))

    def test_a_raised_bar_stows_more_and_a_lowered_one_stows_less(self) -> None:
        self.assertTrue(careen.stowable("MEDIUM", bar="HIGH"))
        self.assertFalse(careen.stowable("LOW", bar="LOW"))

    def test_the_careen_s_default_is_the_telegraph_s(self) -> None:
        """One default for one number; no position moves it (slipwai#154)."""
        self.assertEqual(careen.DEFAULT_BAR, telegraph.BAR)
        self.assertEqual(careen.SEVERITIES, telegraph.SEVERITIES)

    def test_an_unknown_severity_is_treated_as_above_the_bar(self) -> None:
        """Silently stowing what nobody could classify is the failure this module exists to stop."""
        self.assertTrue(careen.above_bar("probably-fine"))
        self.assertFalse(careen.stowable("probably-fine"))


class NeverStowedTest(unittest.TestCase):
    """The owner's rule (slipwai#154): a finding that leaves a feature unusable or untrustworthy for its actor is
    never deferred. Each kind here was a MEDIUM stowed on a real run at a raised bar."""

    KINDS = ("validation-bypass", "document-forgery", "erasure-leak", "money-arithmetic")

    def test_the_four_kinds_are_named(self) -> None:
        self.assertEqual(tuple(careen.NEVER_STOWED_KINDS), self.KINDS)

    def test_a_never_stowed_kind_is_not_stowed_whatever_the_severity_or_the_bar(self) -> None:
        for kind in self.KINDS:
            for severity in careen.SEVERITIES:
                for bar in careen.SEVERITIES:
                    with self.subTest(kind=kind, severity=severity, bar=bar):
                        self.assertTrue(careen.above_bar(severity, bar, kind=kind))
                        self.assertFalse(careen.stowable(severity, bar, kind=kind))

    def test_the_same_medium_with_no_kind_is_stowed_below_a_high_bar(self) -> None:
        """The kind is what changes the answer, not the severity."""
        self.assertTrue(careen.stowable("MEDIUM", bar="HIGH"))
        self.assertFalse(careen.stowable("MEDIUM", bar="HIGH", kind="money-arithmetic"))

    def test_a_kind_nobody_recognises_is_treated_as_never_stowed(self) -> None:
        """A finding somebody tagged meant it was not to be deferred; a typo is no reason to defer it."""
        self.assertFalse(careen.stowable("LOW", bar="HIGH", kind="money-arithmetc"))
        self.assertTrue(careen.stowable("LOW", bar="HIGH", kind=""))

    def test_every_page_that_states_the_rule_names_every_kind(self) -> None:
        pages = {
            "careen.md": careen.careen_page("ordering"),
            "the budget section": harbour.budget_section(),
            "commands/adversary.md": (TOOLKIT_ROOT / "commands/adversary.md").read_text(encoding="utf-8"),
        }
        for name, page in pages.items():
            with self.subTest(page=name):
                self.assertIn(careen.RULE, flat(page))
                for kind in self.KINDS:
                    self.assertIn(f"`{kind}`", page)


class CareenPageTest(unittest.TestCase):
    def test_the_list_is_per_fairway(self) -> None:
        """Two fairways writing one list is the shared-counter problem that cost 54 renumbering commits."""
        self.assertEqual(careen.careen_path("ordering"), "fairways/ordering/careen.md")

    def test_the_page_says_nothing_critical_is_ever_on_it(self) -> None:
        self.assertIn("Nothing CRITICAL is ever on this list", careen.careen_page("ordering"))

    def test_a_row_says_what_closing_it_would_take(self) -> None:
        """A row that only names a file is a row the careen slice has to rediscover."""
        page = flat(careen.careen_page("ordering"))
        self.assertIn("A row is a decision, not a note", page)
        self.assertIn("a reader who was not there can act on", page)


class CareenSliceTest(unittest.TestCase):
    def command(self) -> str:
        return flat(careen.careen_command())

    def test_it_runs_the_ladder_like_any_other_slice(self) -> None:
        """A hardening slice that skips the ladder is how hardening becomes a second quality standard."""
        self.assertIn("a second quality standard", self.command())

    def test_its_demo_is_that_the_findings_are_closed(self) -> None:
        command = self.command()
        self.assertIn("Its demo is: the findings are closed", command)
        self.assertIn('Not "most of them"', command)

    def test_a_row_nobody_wants_any_more_is_closed_by_saying_so(self) -> None:
        """A decision a reader can disagree with later, where a quietly dropped row is not."""
        self.assertIn("with the reason and who said it", self.command())

    def test_the_careen_may_not_stow(self) -> None:
        """The alternative is a careen that stows into the next careen."""
        self.assertIn("It may not stow", self.command())
        self.assertIn("parks for a person instead", self.command())

    def test_it_is_held_to_its_own_fairway_like_every_other_slice(self) -> None:
        self.assertIn("check-slice-scope` holds it to the paths its fairway owns", self.command())

    def test_closing_the_careen_is_not_a_release_decision(self) -> None:
        """The careen says the work is sound; hoisting a flag says the business wants it live."""
        self.assertIn("hoisting a flag says the business wants it live", self.command())


class AdversaryTest(unittest.TestCase):
    def test_the_pass_runs_once_with_a_bar_rather_than_until_it_converges(self) -> None:
        for event in (True, False):
            with self.subTest(event=event):
                written = flat(adversary.adversary_command(event, SOURCED))
                self.assertIn("One round, and a bar", written)
                self.assertIn("21 rounds", written)

    def test_a_finding_below_the_bar_is_stowed_into_the_fairway_s_careen(self) -> None:
        written = flat(adversary.adversary_command(True, SOURCED))
        self.assertIn("fairways/<name>/careen.md", written)
        self.assertIn("Work is never dropped", written)

    def test_stowed_is_a_state_a_finding_can_be_in(self) -> None:
        self.assertIn("`stowed` into the fairway's careen", flat(adversary.adversary_command(True, SOURCED)))


class MutationGateTest(unittest.TestCase):
    def command(self) -> str:
        return flat(mutation.mutation_command(["toy-plain"]))

    def test_a_slice_merges_at_its_threshold_or_does_not_merge(self) -> None:
        self.assertIn("It is a gate, not a report", self.command())
        self.assertIn("at its threshold or it does not merge", self.command())

    def test_nothing_is_carried_to_the_next_slice(self) -> None:
        """A slice that inherits a gap pays for it without having chosen to."""
        command = self.command()
        self.assertIn("nothing is carried", command.lower())
        self.assertIn("18 from S08 to S09", command)

    def test_a_survivor_has_three_answers_and_not_a_fourth(self) -> None:
        self.assertIn("What is not available is a fourth answer", self.command())

    def test_a_run_that_could_not_happen_is_a_stop_rather_than_a_pass(self) -> None:
        """A gate that is green because it did not run is worse than a red one."""
        self.assertIn("green because it did not run", self.command())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
