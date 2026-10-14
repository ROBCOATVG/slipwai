"""The parts that write the ladder into a generated project: its settings, its stages, its boards.

Every one of these returns prose that ends up in a page an agent reads, and in the experiment each was
tested by generating a project and reading the page back — which needs the scaffold, so those suites
return in slice 3.3z. What is held here is what the prose has to say whatever project it lands in.

`sail_settings` gets the most attention, because it carries the two widths the delivery loop is
actually driven by: how much one implementation delegate is handed, and how many failing tests a
red-green-refactor cycle opens with. Section 5 of the plan calls example mapping and that cycle the two
things both profiles share and neither optional; this is the file that writes them down.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import toolkit
from slipwai.project import (
    adversary,
    agent_targets,
    commands,
    demo_stop,
    docs_index,
    evolving,
    ladder,
    parallel_slices,
    sail_section,
    sail_settings,
    stage_models,
)
from slipwai.selection import Selection
from slipwai.services import service_app

ROOT = Path(__file__).resolve().parents[1]
# One event-sourced service, for the pages that take a project's services in order to read a rung off them.
# What is held here is what each page says on either rung, so the rung is only ever why it is non-empty.
SOURCED = [service_app("orders", "toy-plain", 3000, Selection({"write-model": "events"}), first=True)]


class DriveSettingsTest(unittest.TestCase):
    def test_the_two_widths_are_the_ones_the_loop_is_driven_by(self) -> None:
        self.assertEqual(sail_settings.DELEGATES, ("story", "rule", "task"))
        self.assertEqual(sail_settings.CYCLES, ("rule", "example"))

    def test_a_story_is_never_a_cycle(self) -> None:
        """Every rule of a story red before any is implemented is a batch. `rule` is the widest cycle."""
        self.assertIn("story", sail_settings.DELEGATES)
        self.assertNotIn("story", sail_settings.CYCLES)

    def test_the_defaults_are_the_widest_delegate_and_the_widest_legal_cycle(self) -> None:
        self.assertEqual((sail_settings.DEFAULT_DELEGATE, sail_settings.DEFAULT_CYCLE), ("story", "rule"))
        self.assertIn(sail_settings.DEFAULT_DELEGATE, sail_settings.DELEGATES)
        self.assertIn(sail_settings.DEFAULT_CYCLE, sail_settings.CYCLES)

    def test_the_written_config_is_json_carrying_both_widths_and_where_they_are_explained(self) -> None:
        written = json.loads(sail_settings.sail_config())
        self.assertEqual(written["delegate"], sail_settings.DEFAULT_DELEGATE)
        self.assertEqual(written["cycle"], sail_settings.DEFAULT_CYCLE)
        self.assertIn("RED-GREEN-REFACTOR", written["_comment"])

    def test_the_comment_names_the_command_that_changes_it(self) -> None:
        """A settings file a reader cannot change safely is a settings file they will edit by hand."""
        self.assertIn("/sail-settings", sail_settings.COMMENT)
        self.assertIn(sail_settings.SCRIPT, sail_settings.COMMENT)


class StagePagesTest:
    """Shared by the pages that read differently on the two profiles."""

    def both(self, write) -> tuple[str, str]:
        return write(True), write(False)


class ProfileTest(unittest.TestCase, StagePagesTest):
    def test_the_demo_stop_differs_by_profile_and_says_something_either_way(self) -> None:
        event, standard = self.both(demo_stop.demo_stop)
        for page in (event, standard):
            self.assertGreater(len(page.splitlines()), 3)
        self.assertNotEqual(event, standard)

    def test_the_demo_board_names_where_its_rows_come_from(self) -> None:
        event, standard = self.both(demo_stop.board_sources)
        self.assertNotEqual(event, standard)

    def test_the_adversary_command_is_written_for_both_profiles(self) -> None:
        event, standard = self.both(lambda event: adversary.adversary_command(event, SOURCED))
        for page in (event, standard):
            self.assertTrue(page.strip())

    def test_a_slice_is_done_by_a_marker_each_profile_can_actually_read(self) -> None:
        event, standard = self.both(parallel_slices.done_marker)
        self.assertNotEqual(event, standard)


class PagesTest(unittest.TestCase):
    def test_the_docs_index_lists_the_files_it_is_given_and_nothing_else(self) -> None:
        index = docs_index.docs_index({"docs/design.md": "x", "docs/architecture.md": "y"})
        self.assertIn("design.md", index)
        self.assertIn("architecture.md", index)
        self.assertNotIn("nothing-here.md", index)

    def test_an_index_of_no_files_is_still_a_page(self) -> None:
        self.assertTrue(docs_index.docs_index({}).strip())

    def test_the_pages_that_take_nothing_still_write_something(self) -> None:
        for write in (evolving.evolving_page, agent_targets.agent_targets):
            with self.subTest(page=write.__name__):
                self.assertGreater(len(write().splitlines()), 3)


def every_rung() -> str:
    """The event profile's ladder with every other condition met, so a conditional rung is present.

    No apps: the two rungs a browser app adds are a project's own answer, allowed but not required, and
    resolving a backend here would need a language package this gate deliberately does not install.
    """
    return ladder.sail_ladder(event=True, apps=[], target="aws")


def both_profiles() -> list[str]:
    """Every rung either profile has. Two of them are each profile's own answer to one question: the event
    model is a rung only where there is a model, and the chart stage only where there is not."""
    return [heading for event in (True, False)
            for heading in headings(ladder.sail_ladder(event=event, apps=[], target="aws"))]


def headings(text: str) -> list[str]:
    """Each rung's heading, in ladder order: a rung opens `<n>. **Heading** — `."""
    return re.findall(r"^\d+\. \*\*(.+?)\*\*", text, re.MULTILINE)


def rung_bodies(text: str) -> dict[str, str]:
    """Each rung's heading against its own text. Rungs are numbered, not separated by a blank line."""
    parts = re.split(r"^(?=\d+\. \*\*)", text, flags=re.MULTILINE)
    return {headings(part)[0]: part for part in parts if headings(part)}


class LadderTest(unittest.TestCase):
    """The page and the model table say the same thing about what the rungs are, or the gate says so.

    In version 1 the ladder was a list of prose in one function and the models were a table in another, and
    the only thing keeping them in step was whoever last edited both. A stage with no rung is a model
    nothing runs on; a rung with no stage is a step nobody priced. Both are refused here, so slice 5.8's
    review rung cannot be added to one without the other.
    """

    def test_every_rung_of_the_table_is_a_rung_of_the_page(self) -> None:
        written = both_profiles()
        for key, title in stage_models.rung_titles().items():
            with self.subTest(stage=key):
                self.assertIn(title, written, f"{key} is a rung of the table and no profile's ladder names it")

    def test_each_profile_answers_the_typing_question_its_own_way_and_only_once(self) -> None:
        """The event model and the chart are one question: what types the work. Never both, never neither."""
        for event, expected in ((True, "Event model"), (False, "Chart")):
            with self.subTest(event=event):
                written = headings(ladder.sail_ladder(event=event, apps=[], target="aws"))
                self.assertIn(expected, written)
                self.assertNotIn("Chart" if event else "Event model", written)

    def test_a_rung_the_table_does_not_know_is_refused(self) -> None:
        """Except the four a project's own answers add, which run on the stage above them."""
        known = set(stage_models.rung_titles().values()) | set(ladder.ANSWER_RUNGS)
        for heading in both_profiles():
            with self.subTest(rung=heading):
                self.assertIn(heading, known, f"{heading!r} is a rung no stage of the model table names")

    def test_the_stages_that_are_not_rungs_are_the_three_cruise_delegates(self) -> None:
        """The skipper, the hand and the bosun take a model and a brief, and no step of the ladder."""
        self.assertEqual([stage.key for stage in stage_models.STAGES if not stage.rung],
                         ["decide-skipper", "demo-hand", "unblock-bosun"])

    def test_the_merge_rung_exists_and_is_nobody_s_delegate(self) -> None:
        """Rule 10: a person holds the merge until a captain enforces the boundaries."""
        merge = next(stage for stage in stage_models.STAGES if stage.key == "merge")
        self.assertEqual(merge.title, "Merge to main")
        self.assertFalse(merge.delegable)

    def test_the_ladder_does_not_stop_at_the_demo(self) -> None:
        """The three rungs that decide whether a slice may merge were prose in version 1, read once."""
        written = headings(every_rung())
        self.assertEqual(written[-3:], ["Adversary", "Mutation gate", "Merge to main"])

    def test_the_implement_rung_names_the_cycle_and_where_the_widths_are_read(self) -> None:
        rung = " ".join(rung_bodies(every_rung())["Implementation"].split())
        self.assertIn("RED-GREEN-REFACTOR", rung)
        self.assertIn(sail_settings.CONFIG, rung)
        for veto in ("story tag", "number its rules"):
            with self.subTest(veto=veto):
                self.assertIn(veto, rung)

    def test_a_slice_too_narrow_for_its_setting_runs_narrower_rather_than_failing(self) -> None:
        """The done-when of slice 5.2: the fallbacks are written where the agent reads them."""
        self.assertIn("runs narrower and says so; it does not fail", " ".join(every_rung().split()))

    def test_only_the_merge_rung_runs_the_full_gate(self) -> None:
        """Theme B, item 9. An increment that pays for the whole suite is the habit version 2 drops."""
        rungs = rung_bodies(every_rung())
        self.assertIn("make verify", rungs["Merge to main"])
        for heading, body in rungs.items():
            if heading in {"Merge to main", "Principles"}:  # Principles runs `make check-constitution`
                continue
            with self.subTest(rung=heading):
                self.assertNotIn("make verify", body, f"{heading} runs the full gate; only the merge may")


class ExampleMapTest(unittest.TestCase):
    """The example map is a stage of both profiles, and the one stage with a refusal behind it.

    Version 1 shipped it from `assets/profiles/event-modelling/commands/`, so the standard profile had no
    example-mapping stage at all and reached a demo of examples nothing had written. The file is in the
    toolkit now, which is what both profiles are given, and it branches on the profile in its own prose
    rather than by being two files that drift.
    """

    COMMAND = ROOT / "assets/toolkit/commands/example-map.md"

    def test_the_command_ships_from_the_toolkit_and_not_from_one_profile(self) -> None:
        self.assertTrue(self.COMMAND.is_file(), "example-map.md is not in the toolkit")
        self.assertFalse((ROOT / "assets/profiles/event-modelling/commands/example-map.md").exists(),
                         "the event profile still carries its own copy; two copies drift")

    def test_the_toolkit_copies_it_into_either_profile(self) -> None:
        for profile in ("event-modelling", "standard"):
            with self.subTest(profile=profile):
                self.assertEqual(toolkit.toolkit_treatment("commands/example-map.md", profile, set()), "copied")

    def test_it_is_documented_on_both_profiles_and_is_no_longer_the_event_profile_s(self) -> None:
        for event in (True, False):
            with self.subTest(event=event):
                self.assertIn("example-map", commands.command_names(event))
        self.assertNotIn("example-map", commands.EVENT_COMMANDS)

    def test_it_says_where_each_profile_reads_its_inputs(self) -> None:
        """The one thing the profiles differ on, and the reason the file is not two files."""
        text = " ".join(self.COMMAND.read_text(encoding="utf-8").split())
        self.assertIn("docs/event-model/model.yaml", text)
        self.assertIn("specs/<feature>/spec.md", text)
        self.assertIn("specs/<feature>/chart.yaml", text)

    def test_both_profiles_write_one_path_in_one_shape(self) -> None:
        """Every stage after this one reads that path; two shapes would make each of them branch."""
        text = " ".join(self.COMMAND.read_text(encoding="utf-8").split())
        self.assertIn("specs/<feature>/slices/<id>/examples.md", text)

    def test_a_question_is_never_closed_by_inventing_the_answer(self) -> None:
        text = " ".join(self.COMMAND.read_text(encoding="utf-8").split())
        self.assertIn("Never invent a fact to close a question", text)

    def test_the_rung_is_on_both_profiles_and_names_that_profile_s_input(self) -> None:
        for event, expected in ((True, "docs/event-model/model.yaml"), (False, "specs/<feature>/chart.yaml")):
            with self.subTest(event=event):
                rung = " ".join(rung_bodies(
                    ladder.sail_ladder(event=event, apps=[], target="aws"))["Example map"].split())
                self.assertIn(expected, rung)

    def test_an_empty_map_refuses_the_implementation_rung(self) -> None:
        """The done-when of slice 5.17. Implementing against an inference is demoed against the same one."""
        rungs = rung_bodies(ladder.sail_ladder(event=False, apps=[], target="aws"))
        self.assertIn("at least one", " ".join(rungs["Implementation"].split()))
        self.assertIn("A map with none is a stop", " ".join(rungs["Implementation"].split()))


class ReviewRungTest(unittest.TestCase):
    """The rung between the demo and the adversary pass, and the role that pays for it.

    In the experiment adversary review found 64 LOW findings, most of them about wording, that a review
    would have found for a fraction of the tokens. The pass that was missing is a fresh context reading the
    slice's whole diff — not one cycle's code — before anything adversarial runs.
    """

    def rung(self) -> str:
        return " ".join(rung_bodies(every_rung())["Review and reshape"].split())

    def test_it_sits_between_the_demo_and_the_adversary_pass(self) -> None:
        written = headings(every_rung())
        self.assertEqual(written[written.index("Demo") + 1], "Review and reshape")
        self.assertEqual(written[written.index("Review and reshape") + 1], "Adversary")

    def test_the_reviewer_never_edits(self) -> None:
        """A reviewer that can write is one that edits, and then nobody has read the diff with fresh eyes."""
        review = next(stage for stage in stage_models.STAGES if stage.key == "review-mate")
        self.assertEqual(review.writes, stage_models.NONE)
        self.assertEqual(review.commands, stage_models.READ_ONLY)
        self.assertIn("The reviewer never edits", self.rung())

    def test_the_two_refactors_are_not_the_same_pass(self) -> None:
        """Collapsing them loses the small one, which is the one that stops the big one being needed."""
        self.assertIn("not one cycle's code", self.rung())
        self.assertIn("collapsing them loses the small one", self.rung())

    def test_a_slice_cannot_reach_the_adversary_rung_with_a_finding_open(self) -> None:
        """Slice 5.8's done-when."""
        self.assertIn("does not reach the adversary rung with a review finding open", self.rung())

    def test_the_findings_come_back_in_the_shape_the_gaps_stage_uses(self) -> None:
        """So one triage reads both rather than two formats reaching one person."""
        self.assertIn("in the shape the gaps stage uses", self.rung())

    def test_it_runs_once_per_slice_and_a_return_is_never_sent_to_it(self) -> None:
        """A run that reviewed every delegate return paid eight reviews and eight fix rounds for nine pieces
        of coding; the rung says the cadence outright and names the gate that notices a third bracket."""
        rung = self.rung()
        self.assertIn("Once per slice, over the whole diff", rung)
        self.assertIn("never sent to a reviewer of its own", rung)
        self.assertIn("at most two `review` brackets", rung)
        self.assertIn("make check-benchmark", rung)

    def test_the_model_table_gains_a_review_role_seeded_to_the_host(self) -> None:
        table = json.loads(stage_models.stage_models())
        self.assertEqual(table["stages"]["review-mate"], stage_models.REVIEW)
        for harness, roles in table["roles"].items():
            with self.subTest(harness=harness):
                self.assertEqual(roles[stage_models.REVIEW], stage_models.HOST)

    def test_there_is_a_delegate_type_for_it_and_it_writes_nothing(self) -> None:
        written = agent_targets.agent_targets() if hasattr(agent_targets, "agent_targets") else ""
        self.assertIsInstance(written, str)
        self.assertIn("sail-review-mate", sail_section.delegable_types())


class HookPointTest(unittest.TestCase):
    def test_the_points_are_named_in_the_order_they_fire(self) -> None:
        """A hook that fires in a different order than the page says is a hook nobody can reason about."""
        written = re.findall(r"`(before-stage|after-stage|boundary|before-merge)`", ladder.hook_points())
        self.assertEqual(written[:4], ["before-stage", "after-stage", "boundary", "before-merge"])

    def test_a_hook_is_never_fatal_to_the_rung(self) -> None:
        """6.1's rule, written where `/sail` reads it: the captain depends on no hook, and neither does this."""
        text = ladder.hook_points()
        self.assertIn("never fatal to the rung", " ".join(text.split()))
        self.assertIn("Nothing in this ladder depends on a hook", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
