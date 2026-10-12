"""Provisioning a berth: two sandbox kinds, and a status that reads disk rather than the record.

The four-way sandbox matrix this slice originally carried — sandbox-exec on macOS, bwrap on Linux, Windows
Sandbox on native Windows, a container elsewhere — is gone. Four implementations of one idea is four things
to keep working, and Apple deprecating sandbox-exec had already blocked the slice once.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import berths
from slipwai.project import berth_commands


def flat(text: str) -> str:
    return " ".join(text.split())


class KindTest(unittest.TestCase):
    def test_there_are_two_kinds_and_the_matrix_is_gone(self) -> None:
        self.assertEqual(berth_commands.KINDS, ("none", "sbx"))

    def test_none_is_the_default(self) -> None:
        """One captain on a trusted machine is most laptops most of the time."""
        self.assertEqual(berth_commands.DEFAULT_KIND, "none")

    def test_the_page_offers_none_rather_than_tolerating_it(self) -> None:
        """A tool that pretends a boundary is always needed gets worked around rather than used."""
        page = flat(berth_commands.berth_command())
        self.assertIn("`none` is a real answer, not a fallback", page)
        self.assertIn("paying a Docker dependency for a boundary they have not got", page)

    def test_the_page_says_what_a_sandbox_actually_buys(self) -> None:
        self.assertIn("isolation *between concurrent fairways on one machine*",
                      flat(berth_commands.berth_command()))

    def test_no_berth_holds_a_credential_under_either_kind(self) -> None:
        page = flat(berth_commands.berth_command())
        self.assertIn("holds no credential", page)
        self.assertIn("a sandbox with a way out", page)


class RemoveTest(unittest.TestCase):
    def test_remove_undoes_all_four_things_add_made(self) -> None:
        page = flat(berth_commands.berth_command())
        self.assertIn("The worktree, the record, the scratch directory and the sandbox", page)

    def test_a_half_existing_berth_is_named_as_the_thing_to_avoid(self) -> None:
        """The next add takes the next index, the stale one keeps its ports, and nothing reconciles them."""
        page = flat(berth_commands.berth_command())
        self.assertIn("half-exists is worse than no berth", page)
        self.assertIn("reports what it could not remove rather than exiting quietly", page)


class StatusTest(unittest.TestCase):
    def line(self, sandbox: str, worktree: bool, running: bool) -> str:
        return berth_commands.status_line(berths.berth("orca", 0, "harbour_one", sandbox), worktree, running)

    def test_a_healthy_berth_shows_its_ports_and_database(self) -> None:
        written = self.line("none", True, False)
        self.assertIn("orca", written)
        self.assertIn("8100-8119", written)
        self.assertIn("app_harbour_one_orca", written)

    def test_a_missing_worktree_is_shouted_rather_than_omitted(self) -> None:
        self.assertIn("NO WORKTREE", self.line("none", False, False))

    def test_a_record_saying_sbx_with_no_sandbox_running_is_the_case_this_is_for(self) -> None:
        """A line that read the record alone would call that berth healthy."""
        self.assertIn("SANDBOX DOWN", self.line("sbx", True, False))

    def test_a_running_sandbox_reads_as_up(self) -> None:
        self.assertIn("sandbox up", self.line("sbx", True, True))

    def test_a_berth_with_no_sandbox_says_so_rather_than_looking_broken(self) -> None:
        """`none` is a choice, so it must not read like a sandbox that failed to start."""
        written = self.line("none", True, False)
        self.assertIn("no sandbox", written)
        self.assertNotIn("DOWN", written)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
