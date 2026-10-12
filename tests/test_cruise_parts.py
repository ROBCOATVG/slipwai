"""The parts that write `/cruise` into a generated project, and the ones `./init` writes.

`/cruise` is the same fleet as `/sail` with nobody at the keyboard: the skipper answers the product
questions a person would have been asked, and the hand runs the demos. These modules write the commands
and the stop table that make that safe — what the skipper may decide, what it must stop for, and what it
must repeat verbatim rather than summarise.

As with the rest of the parts, the experiment's suites generate a project to read the pages back, so
they return in 3.3z. Held here is what the prose must say wherever it lands, and in particular the
places where paraphrase would be a bug.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.project import (
    cruise_seat,
    cruise_stops,
    cruise_told,
    cruise_unblock,
    native_commands,
    whats_next,
    where_are_we,
)


class SeatTest(unittest.TestCase):
    """What the seat is told to pass on, and what it is told not to touch."""

    def test_the_harness_output_is_repeated_unchanged_rather_than_summarised(self) -> None:
        """A summary of what the harness printed is the one thing the reader cannot check."""
        self.assertIn("unchanged", cruise_seat.part("verbatim"))

    def test_each_seat_command_is_written_and_is_not_the_others(self) -> None:
        written = {write(): name for name, write in (
            ("status", cruise_seat.cruise_status_command),
            ("stop", cruise_seat.cruise_stop_command),
            ("tell", cruise_seat.cruise_tell_command),
        )}
        self.assertEqual(len(written), 3, "two seat commands write the same page")
        for page in written:
            self.assertGreater(len(page.splitlines()), 3)


class UnblockTest(unittest.TestCase):
    """What a run may never do to get itself moving again."""

    def test_the_catastrophic_list_is_not_empty(self) -> None:
        """An unblock stage with nothing forbidden is an unblock stage that will delete the repository."""
        self.assertTrue(cruise_unblock.CATASTROPHIC)

    def test_every_catastrophic_action_reaches_the_page_that_forbids_it(self) -> None:
        page = cruise_unblock.catastrophic_list()
        for forbidden in cruise_unblock.CATASTROPHIC:
            with self.subTest(action=forbidden[:40]):
                self.assertIn(forbidden, page)


class StopsTest(unittest.TestCase):
    def test_the_stop_table_differs_by_profile(self) -> None:
        event = cruise_stops.stop_table(True, "none", None)
        standard = cruise_stops.stop_table(False, "none", None)
        self.assertNotEqual(event, standard)

    def test_a_managed_target_adds_stops_an_unmanaged_one_has_not(self) -> None:
        """Somewhere to deploy is somewhere a run can do damage unattended."""
        self.assertNotEqual(cruise_stops.stop_table(True, "none", None),
                            cruise_stops.stop_table(True, "aws", None))

    def test_the_log_and_the_report_are_per_feature_paths(self) -> None:
        self.assertIn("<feature>", cruise_stops.REPORT)


class ToldTest(unittest.TestCase):
    def test_every_section_names_the_script_it_is_written_about(self) -> None:
        """These pages are generated around a script path, and a page naming the wrong one is silent."""
        script = "scripts/agents/cruise.py"
        for write in (cruise_told.told_argument, cruise_told.seat_queues, cruise_told.boundary_asks):
            with self.subTest(section=write.__name__):
                self.assertIn(script, write(script))


class ProfilePagesTest(unittest.TestCase):
    def test_what_is_next_and_where_we_are_both_read_per_profile(self) -> None:
        for write in (whats_next.whats_next_command, where_are_we.where_are_we_command):
            with self.subTest(page=write.__name__):
                self.assertNotEqual(write(True), write(False))


class NativeCommandsTest(unittest.TestCase):
    """A generated Makefile's recipes, and which of them a repository is held to as it is adopted."""

    def test_the_ratcheted_targets_are_targets(self) -> None:
        for target in native_commands.RATCHETED:
            self.assertIn(target, native_commands.TARGETS)

    def test_a_recipe_is_cut_into_the_steps_make_will_run(self) -> None:
        self.assertEqual(native_commands.steps("one\n\ttwo\n\tthree"), ["one", "two", "three"])

    def test_a_recipe_of_one_step_is_one_step(self) -> None:
        self.assertEqual(native_commands.steps("just-one"), ["just-one"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
