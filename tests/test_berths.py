"""A berth's allocation: arithmetic rather than a table somebody maintains.

In the experiment and in MANDA this was an operator's job and lived in their head — five berths on one
machine, the port numbers chosen by hand, a load average of 198 when nobody was counting. What goes wrong
is not dramatic: two berths take one port, one fails to start, and the failure reads as a broken service
rather than as a collision.

So a berth's ports fall out of its index and its database out of its name. Nobody chooses a number, so
nobody chooses the same number twice — and `collisions` checks that, because "by construction" is a claim
like any other.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import berths, logs
from slipwai.backends import SERVICE_PORT, WEB_PORT

#: The machine these berths are allocated on. Passed rather than looked up: `berths.py` is carried into a
#: generated project byte for byte and may import nothing beside it, so the identity arrives from the caller.
MINE = "harbour_one"
THEIRS = "harbour_two"


class AllocationTest(unittest.TestCase):
    def test_two_berths_never_share_a_port(self) -> None:
        allocated = berths.allocate(["orca", "narwhal"], MINE)
        self.assertEqual(berths.collisions(allocated), [])
        self.assertEqual(set(allocated[0].ports) & set(allocated[1].ports), set())

    def test_two_berths_never_share_a_database(self) -> None:
        """A migration that drops a table drops it for everybody in a shared one, and the failure arrives
        in a fairway that changed nothing."""
        allocated = berths.allocate(["orca", "narwhal"], MINE)
        self.assertNotEqual(allocated[0].database, allocated[1].database)

    def test_many_berths_still_collide_nowhere(self) -> None:
        self.assertEqual(berths.collisions(berths.allocate([f"b{n}" for n in range(12)], MINE)), [])

    def test_a_block_starts_above_what_a_project_uses_outside_a_berth(self) -> None:
        """So a berth never collides with a project started the ordinary way."""
        first = berths.allocate(["orca"], MINE)[0]
        self.assertGreater(min(first.ports), max(SERVICE_PORT, WEB_PORT))

    def test_a_block_has_room_for_more_than_today_s_services(self) -> None:
        """A block exactly big enough today is a block too small at the next service."""
        self.assertGreaterEqual(len(berths.allocate(["orca"], MINE)[0].ports), 20)

    def test_everything_but_the_name_and_the_index_is_derived(self) -> None:
        one = berths.berth("orca", 0, MINE)
        self.assertEqual(one.database, berths.database_of("orca", MINE))
        self.assertIn("orca", one.scratch)
        self.assertIn("orca", one.worktree)


class NameTest(unittest.TestCase):
    def test_a_name_is_held_to_what_a_database_and_a_directory_both_allow(self) -> None:
        for bad in ("Orca", "1orca", "orca_one", "orca!", "", "o" * 40):
            with self.subTest(name=bad), self.assertRaises(ValueError):
                berths.named(bad)

    def test_the_refusal_says_why_the_rule_is_what_it_is(self) -> None:
        with self.assertRaises(ValueError) as refused:
            berths.named("Orca")
        self.assertIn("becomes a database name", str(refused.exception))

    def test_a_hyphen_is_allowed_in_a_name_and_not_in_a_database(self) -> None:
        self.assertEqual(berths.named("orca-two"), "orca-two")
        self.assertEqual(berths.database_of("orca-two", MINE), "app_harbour_one_orca_two")


class CollisionTest(unittest.TestCase):
    def test_a_collision_is_reported_with_both_berths_named(self) -> None:
        """The check exists because the arithmetic claim is still a claim."""
        same = [berths.berth("orca", 0, MINE), berths.berth("narwhal", 0, MINE)]
        found = berths.collisions(same)
        self.assertTrue(found)
        self.assertIn("orca", found[0])
        self.assertIn("narwhal", found[0])


class MachineTest(unittest.TestCase):
    """Two machines, one database server. Ports needed nothing — they are local to each machine, so two
    machines allocating independently cannot collide. The database was the whole exposure, and only where
    people point at a shared instance: every generated default is local, being in-memory, a SQLite file or
    a container from the project's own compose file. Putting the machine in the name removes the collision
    rather than refusing the configuration."""

    def test_two_machines_allocating_the_same_berth_get_two_databases(self) -> None:
        mine = berths.berth("orca", 0, MINE)
        theirs = berths.berth("orca", 0, THEIRS)
        self.assertNotEqual(mine.database, theirs.database)
        self.assertEqual(berths.collisions([mine, theirs]), [])

    def test_and_still_get_the_same_ports_because_ports_are_local(self) -> None:
        """Not an oversight. A port is reachable from one machine, so two machines' blocks are not in the
        same space at all, and shifting one by machine would waste the arithmetic that makes blocks safe."""
        self.assertEqual(berths.berth("orca", 0, MINE).ports, berths.berth("orca", 0, THEIRS).ports)

    def test_the_machine_is_in_the_name_rather_than_asked_for(self) -> None:
        self.assertEqual(berths.database_of("orca", MINE), "app_harbour_one_orca")

    def test_a_berth_says_which_machine_it_is_on(self) -> None:
        """The record is read by `berth status` on the machine that made it, and by nothing anywhere else
        — so the field is what says which machine a record found in a shared checkout belongs to."""
        self.assertEqual(berths.berth("orca", 0, MINE).machine, MINE)

    def test_the_longest_name_on_the_longest_machine_is_still_a_database_name(self) -> None:
        """PostgreSQL's identifier limit is 63 bytes and it truncates rather than refusing, which is how
        two berths would silently become one."""
        self.assertLessEqual(len(berths.database_of("o" * 31, "m" * logs.MACHINE_WIDTH)), 63)


class CredentialTest(unittest.TestCase):
    def test_a_berth_record_holds_no_credential_field(self) -> None:
        """A berth that held a token would be a sandbox with a way out of it."""
        fields = set(vars(berths.berth("orca", 0, MINE)))
        for forbidden in ("token", "credential", "secret", "key", "password"):
            with self.subTest(field=forbidden):
                self.assertNotIn(forbidden, fields)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
