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

import importlib.util
import re
import sys
import unittest
from types import ModuleType

import checkout_packages  # noqa: F401
from test_ladder_parts import every_rung

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project import adversary, capability_gates, careen, harbour, mutation
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

    def test_an_unknown_severity_is_treated_as_above_the_bar(self) -> None:
        """Silently stowing what nobody could classify is the failure this module exists to stop."""
        self.assertTrue(careen.above_bar("probably-fine"))
        self.assertFalse(careen.stowable("probably-fine"))


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

    def test_it_runs_once_the_planned_slices_are_merged_whatever_the_release_state(self) -> None:
        """A pre-launch product hoists no flag, so "before its flag is hoisted" alone never came (issue 154)."""
        command = self.command()
        self.assertIn("run as that fairway's last: once every planned slice of it is merged", command)
        self.assertIn("whatever the release state", command)
        self.assertNotIn("before its flag is hoisted", command)

    def test_it_closes_rows_the_harbourmaster_carried_and_says_how_its_demo_is_recorded(self) -> None:
        command = self.command()
        self.assertIn("The harbourmaster wrote those rows there", command)
        self.assertIn("deck_line.py demo --slice <fairway>-careen --verdict accepted", command)

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

    def test_a_finding_below_the_bar_is_stowed_into_the_capability_s_record_for_the_careen(self) -> None:
        """issue 154: the page told a slice to write `fairways/<name>/careen.md`, which `check-slice-scope`
        refuses it, so S62 wrote, was refused, handed back and conflicted for five merge attempts."""
        written = flat(adversary.adversary_command(True, SOURCED))
        self.assertIn("specs/<feature>/capabilities/<capability>/stowed.md", written)
        self.assertIn("the harbourmaster carries the record's rows into `fairways/<name>/careen.md`", written)
        self.assertNotIn("a row in `fairways/<name>/careen.md`", written)
        self.assertIn("Work is never dropped", written)

    def test_stowed_is_a_state_a_finding_can_be_in(self) -> None:
        self.assertIn("`stowed` for the fairway's careen", flat(adversary.adversary_command(True, SOURCED)))


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


def toolkit_careen() -> ModuleType:
    """The careen's writer as a project carries it: `scripts/agents/careen.py`, which has no slipwai to import."""
    spec = importlib.util.spec_from_file_location("toolkit_careen", TOOLKIT_ROOT / "scripts/agents/careen.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


ROW_A = "| 2026-11-23 | S62 | converge | MEDIUM | CV-1: the reminder names a deleted workspace; drop it | open |"
ROW_B = "| 2026-11-23 | S62 | adversary | LOW | A-3: the error copy says `id`; say what was missing | open |"
STOWED = f"# Stowed — reminders\n\n{careen.ROW_HEADER}\n|---|---|---|---|---|---|\n{ROW_A}\n{ROW_B}\n"


class CareenWriterTest(unittest.TestCase):
    """The harbourmaster's half: rows carried from a capability's `stowed.md` into the fairway's careen."""

    def setUp(self) -> None:
        self.module = toolkit_careen()

    def test_a_fairway_with_no_careen_gets_one_with_the_rows_under_the_capability(self) -> None:
        """The modelling fairway on manda had no careen at all, so nothing it stowed was in one."""
        text, added = self.module.appended("", "modelling", "reminders", self.module.rows(STOWED))
        self.assertEqual(added, 2)
        self.assertTrue(text.startswith("# Careen — modelling"))
        after = text.split("## reminders", 1)[1]
        self.assertIn(ROW_A, after)
        self.assertIn(ROW_B, after)

    def test_a_row_already_carried_is_not_added_twice(self) -> None:
        once, _ = self.module.appended("", "intake", "reminders", self.module.rows(STOWED))
        twice, added = self.module.appended(once, "intake", "reminders", self.module.rows(STOWED))
        self.assertEqual(added, 0)
        self.assertEqual(once, twice)

    def test_a_row_the_careen_closed_is_not_reopened_by_the_record_that_stowed_it(self) -> None:
        once, _ = self.module.appended("", "intake", "reminders", self.module.rows(STOWED))
        closed = once.replace(ROW_A, ROW_A.replace("| open |", "| done |"))
        again, added = self.module.appended(closed, "intake", "reminders", self.module.rows(STOWED))
        self.assertEqual(added, 0)
        self.assertEqual(self.module.open_rows(again), [ROW_B])

    def test_a_later_slice_s_new_row_joins_its_capability_s_section(self) -> None:
        once, _ = self.module.appended("", "intake", "reminders", [ROW_A])
        other, _ = self.module.appended(once, "intake", "email-in", [ROW_B.replace("A-3", "C-1")])
        later, added = self.module.appended(other, "intake", "reminders", [ROW_A, ROW_B])
        self.assertEqual(added, 1)
        reminders = later.split("## reminders", 1)[1].split("## email-in", 1)[0]
        self.assertIn(ROW_B, reminders)

    def test_the_header_the_rule_and_the_template_placeholder_are_not_rows(self) -> None:
        self.assertEqual(self.module.rows(careen.careen_page("x") + careen.ROW_HEADER
                                          + "\n| <date> | <slice-id> | review | LOW | one line | open |\n"), [])

    def test_the_page_a_project_is_given_is_the_page_the_keel_describes(self) -> None:
        self.assertEqual(self.module.page("ordering"), careen.careen_page("ordering"))
        self.assertEqual(self.module.careen_path("ordering"), careen.careen_path("ordering"))
        self.assertEqual(self.module.HEADER, careen.ROW_HEADER)

    def test_the_careen_slice_is_named_for_its_fairway(self) -> None:
        self.assertEqual(self.module.careen_slice("intake"), "intake-careen")
        self.assertEqual(self.module.fairway_of("intake-careen"), "intake")
        self.assertEqual(self.module.fairway_of("S62"), "")


class NoSliceWritesTheCareenTest(unittest.TestCase):
    """issue 154: every instruction that told a slice to write `fairways/<name>/careen.md` was refused by
    `check-slice-scope`. A sentence that names `fairways/` now says whose it is, and it is never the slice's."""

    def pages(self) -> dict[str, str]:
        return {
            "the budget section": harbour.budget_section(),
            "commands/sail.md": (TOOLKIT_ROOT / "commands/sail.md").read_text(encoding="utf-8"),
            "commands/adversary.md": adversary.adversary_command(True, SOURCED),
            "commands/mutation.md": mutation.mutation_command(["toy-plain"]),
            "the capability gates": capability_gates.capability_gates_stage(False),
            "the ladder": every_rung(),
            **{f"agents/{path.name}": path.read_text(encoding="utf-8")
               for path in sorted((TOOLKIT_ROOT / "agents").glob("*.md"))},
        }

    def test_every_sentence_naming_fairways_says_the_harbourmaster_writes_it_or_the_slice_never_does(self) -> None:
        for name, text in self.pages().items():
            for sentence in re.split(r"(?<=[.;:])\s+", flat(text)):
                if "fairways/" in sentence and "careen" in sentence:
                    with self.subTest(page=name, sentence=sentence[:120]):
                        self.assertRegex(sentence, r"harbourmaster|[Nn]ever|may not")

    def test_each_stowing_page_names_the_capability_s_record(self) -> None:
        pages = self.pages()
        for name in ("the budget section", "commands/sail.md", "commands/adversary.md", "commands/mutation.md",
                     "the capability gates", "agents/sail-review-mate.md"):
            with self.subTest(page=name):
                self.assertIn("stowed.md", pages[name])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
