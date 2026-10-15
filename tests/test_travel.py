"""What travels between machines: the logs and the in-flight branch, one ref per writer.

Section 14's fourth broken link was that nothing ever *wrote* `refs/slipwai/logs/*`. Both the captain and
the harbourmaster fetched them and neither pushed, so the fetch was ceremony and a second machine saw
nothing the first did. This is the other half, and the shape it takes is the one the harbourmaster settled
on 2026-10-12: **one ref per writer, and nothing is ever merged into one file.**

A deck log's writer is the captain holding that fairway, so the ref is `refs/slipwai/logs/<fairway>`. A
harbour log's writer is that machine's harbourmaster, so the ref is
`refs/slipwai/logs/harbour/<machine>`. Each has exactly one writer, so neither can conflict — and the one
thing that would break the append-only property is folding two writers' lines into one file, which nothing
here does.

The guarantee is checked rather than asserted: **a push that is not an append is refused.** A log whose ref
holds lines the local file does not is a log that is about to lose them, and that is the one failure this
whole design exists to prevent.

These cases run two real clones of one real bare repository, because what is being proved is git's own
behaviour and a fake of it would prove the fake. Nothing here reaches a network and nothing here pushes
anywhere real.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

ONE = "harbour_one"
TWO = "harbour_two"


def loaded(name: str) -> Any:
    """One of the toolkit's agent scripts as the module it is inside a project.

    By path rather than by name: these are not importable as `slipwai.<name>` and never will be — they ship
    in a generated project, which has no slipwai to import, and each puts its own directory on the path so
    that its siblings resolve the same way there as here.
    """
    spec = importlib.util.spec_from_file_location(name, TOOLKIT_ROOT / f"scripts/agents/{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


claims = loaded("claims")
logs = loaded("logs")
travel = loaded("travel")


def git(*argv: str, where: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                          cwd=where, capture_output=True, text=True, check=False)


def line(kind: str, t: str, **fields: object) -> str:
    return json.dumps({"v": 1, "t": t, "kind": kind, **fields}) + "\n"


class Fixture(unittest.TestCase):
    """A bare repository standing in for the forge, and two clones standing in for two machines."""

    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        root = Path(self.scratch.name)
        self.forge = root / "forge.git"
        git("init", "--quiet", "--bare", "--initial-branch=main", str(self.forge), where=root)
        seed = root / "seed"
        seed.mkdir()
        git("init", "--quiet", "--initial-branch=main", where=seed)
        (seed / "project.json").write_text("{}", encoding="utf-8")
        git("add", "-A", where=seed)
        git("commit", "--quiet", "-m", "the skeleton", where=seed)
        git("remote", "add", "origin", str(self.forge), where=seed)
        git("push", "--quiet", "origin", "main", where=seed)
        self.one, self.two = root / "one", root / "two"
        for where in (self.one, self.two):
            git("clone", "--quiet", str(self.forge), str(where), where=root)

    def deck(self, root: Path, fairway: str, *lines: str) -> Path:
        path = root / f".slipwai/logs/model/{fairway}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.writelines(lines)
        return path


class LogRefTest(Fixture):
    def test_a_deck_log_pushed_to_its_ref_is_read_back_on_the_other_machine(self) -> None:
        """The fourth broken link: before this, nothing anywhere wrote these refs and the fetch was
        ceremony."""
        path = self.deck(self.one, "ordering", line("claimed", "2026-10-12T09:00:00Z",
                                                    fairway="ordering", slice="ORD-01"))
        pushed, why = travel.push_log(self.one, path, travel.deck_ref("ordering"), ONE)
        self.assertTrue(pushed, why)
        travel.fetch(self.two)
        self.assertEqual(travel.held(self.two, travel.deck_ref("ordering")),
                         path.read_text(encoding="utf-8"))

    def test_a_push_that_is_not_an_append_is_refused_by_name(self) -> None:
        """The one failure this design exists to prevent. A local log that is not a continuation of what
        the ref holds is one whose push would drop every line the ref has and nobody could tell."""
        path = self.deck(self.one, "ordering", line("claimed", "2026-10-12T09:00:00Z",
                                                    fairway="ordering", slice="ORD-01"))
        self.assertTrue(travel.push_log(self.one, path, travel.deck_ref("ordering"), ONE)[0])
        path.write_text(line("claimed", "2026-10-12T09:30:00Z", fairway="ordering", slice="ORD-02"),
                        encoding="utf-8")
        pushed, why = travel.push_log(self.one, path, travel.deck_ref("ordering"), ONE)
        self.assertFalse(pushed)
        self.assertIn("ordering", why)
        self.assertIn("append", why)

    def test_a_log_that_has_not_changed_is_not_pushed_again(self) -> None:
        """Every pass pushes, and most passes have nothing new. A commit per pass would make the ref's
        history longer than the log it carries."""
        path = self.deck(self.one, "ordering", line("heartbeat", "2026-10-12T09:00:00Z", fairway="ordering"))
        self.assertTrue(travel.push_log(self.one, path, travel.deck_ref("ordering"), ONE)[0])
        was = git("rev-parse", travel.deck_ref("ordering"), where=self.one).stdout.strip()
        self.assertTrue(travel.push_log(self.one, path, travel.deck_ref("ordering"), ONE)[0])
        self.assertEqual(git("rev-parse", travel.deck_ref("ordering"), where=self.one).stdout.strip(), was)

    def test_a_harbour_log_travels_under_its_machines_own_ref(self) -> None:
        """One ref per writer, over two partitions: a fairway's captain writes one, a machine's
        harbourmaster the other, and neither can ever be the other's."""
        path = self.one / f".slipwai/logs/harbour/{ONE}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(line("berth-allocated", "2026-10-12T09:00:00Z", fairway="ordering", berth="1"),
                        encoding="utf-8")
        pushed, why = travel.push_log(self.one, path, travel.harbour_ref(ONE), ONE)
        self.assertTrue(pushed, why)
        self.assertNotEqual(travel.harbour_ref(ONE), travel.harbour_ref(TWO))
        travel.fetch(self.two)
        self.assertEqual(travel.held(self.two, travel.harbour_ref(ONE)), path.read_text(encoding="utf-8"))

    def test_a_ref_nothing_has_written_holds_nothing_rather_than_failing(self) -> None:
        self.assertIsNone(travel.held(self.two, travel.deck_ref("ordering")))
        self.assertEqual(travel.last_heard(self.two, travel.deck_ref("ordering")), "")


class LandingTest(Fixture):
    """Where another machine's lines go. A harbour log is that machine's file and lands as itself; a deck
    log is one fairway's single chain and lands only where this machine is not the one writing it."""

    def test_another_machines_harbour_log_lands_as_its_own_file(self) -> None:
        path = self.one / f".slipwai/logs/harbour/{ONE}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(line("park", "2026-10-12T09:00:00Z", fairway="ordering", why="a person"),
                        encoding="utf-8")
        travel.push_log(self.one, path, travel.harbour_ref(ONE), ONE)
        mine = self.two / f".slipwai/logs/harbour/{TWO}.jsonl"
        mine.parent.mkdir(parents=True, exist_ok=True)
        mine.write_text(line("telegraph", "2026-10-12T09:01:00Z", position="half-ahead"), encoding="utf-8")
        travel.land(self.two, TWO, held=[])
        landed = self.two / f".slipwai/logs/harbour/{ONE}.jsonl"
        self.assertTrue(landed.is_file())
        self.assertIn("a person", landed.read_text(encoding="utf-8"))
        self.assertIn("telegraph", mine.read_text(encoding="utf-8"))

    def test_this_machines_own_harbour_log_is_never_written_by_the_landing(self) -> None:
        """One writer per file is the rule the whole design rests on, and the landing is a second writer
        wherever it touches a file this machine's own harbourmaster is appending to."""
        mine = self.one / f".slipwai/logs/harbour/{ONE}.jsonl"
        mine.parent.mkdir(parents=True, exist_ok=True)
        mine.write_text(line("telegraph", "2026-10-12T09:00:00Z", position="half-ahead"), encoding="utf-8")
        travel.push_log(self.one, mine, travel.harbour_ref(ONE), ONE)
        with mine.open("a", encoding="utf-8") as handle:
            handle.write(line("park", "2026-10-12T09:02:00Z", fairway="ordering", why="later"))
        travel.land(self.one, ONE, held=[])
        self.assertIn("later", mine.read_text(encoding="utf-8"))

    def test_a_deck_log_this_machine_holds_the_claim_for_is_not_landed_over(self) -> None:
        """The writer never reads its own file back from the ref. A captain that is appending and a landing
        that rewrites the same file are two writers, which is the one thing there may never be."""
        path = self.deck(self.one, "ordering", line("claimed", "2026-10-12T09:00:00Z",
                                                    fairway="ordering", slice="ORD-01"))
        travel.push_log(self.one, path, travel.deck_ref("ordering"), ONE)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line("heartbeat", "2026-10-12T09:01:00Z", fairway="ordering"))
        travel.land(self.one, ONE, held=["ordering"])
        self.assertIn("heartbeat", path.read_text(encoding="utf-8"))

    def test_a_deck_log_of_a_fairway_this_machine_does_not_hold_lands_as_a_cache_of_the_ref(self) -> None:
        """So that every reader of a deck log — the board, the run-state overlay, clearance — reads what
        the other machine wrote without any of them learning about refs."""
        path = self.deck(self.one, "ordering", line("claimed", "2026-10-12T09:00:00Z",
                                                    fairway="ordering", slice="ORD-01"))
        travel.push_log(self.one, path, travel.deck_ref("ordering"), ONE)
        travel.land(self.two, TWO, held=[])
        landed = self.two / ".slipwai/logs/model/ordering.jsonl"
        self.assertEqual(landed.read_text(encoding="utf-8"), path.read_text(encoding="utf-8"))

    def test_a_landing_that_would_not_be_an_append_leaves_the_file_alone(self) -> None:
        """The same rule as the push, from the other side: a ref that is not a continuation of what is here
        is a ref one of us is wrong about, and overwriting would destroy the evidence of which."""
        path = self.deck(self.one, "ordering", line("claimed", "2026-10-12T09:00:00Z",
                                                    fairway="ordering", slice="ORD-01"))
        travel.push_log(self.one, path, travel.deck_ref("ordering"), ONE)
        theirs = self.deck(self.two, "ordering", line("claimed", "2026-10-12T08:00:00Z",
                                                      fairway="ordering", slice="ORD-99"))
        travel.land(self.two, TWO, held=[])
        self.assertIn("ORD-99", theirs.read_text(encoding="utf-8"))
        self.assertNotIn("ORD-01", theirs.read_text(encoding="utf-8"))


class WipTest(Fixture):
    """The in-flight branch. A captain holds no credential, so a slice branch lives only on the machine that
    built it — and a lapsed claim then leaves the work not merely unclaimed but unreachable."""

    def branch(self, root: Path, name: str, path: str, body: str) -> str:
        git("checkout", "--quiet", "-b", name, where=root)
        (root / path).write_text(body, encoding="utf-8")
        git("add", "-A", where=root)
        git("commit", "--quiet", "-m", name, where=root)
        return git("rev-parse", "HEAD", where=root).stdout.strip()

    def test_the_in_flight_branch_travels_and_the_other_machine_checks_it_out(self) -> None:
        made = self.branch(self.one, "slice/ORD-01", "rungs.txt", "one\ntwo\nthree\nfour\n")
        pushed, why = travel.push_wip(self.one, "slice/ORD-01", travel.wip_ref("ordering"))
        self.assertTrue(pushed, why)
        landed, why = travel.land_wip(self.two, travel.wip_ref("ordering"), "slice/ORD-01")
        self.assertTrue(landed, why)
        self.assertEqual(git("rev-parse", "HEAD", where=self.two).stdout.strip(), made)
        self.assertEqual((self.two / "rungs.txt").read_text(encoding="utf-8"), "one\ntwo\nthree\nfour\n")

    def test_a_branch_that_is_not_there_is_said_rather_than_pushed(self) -> None:
        pushed, why = travel.push_wip(self.one, "slice/ORD-01", travel.wip_ref("ordering"))
        self.assertFalse(pushed)
        self.assertIn("slice/ORD-01", why)

    def test_a_wip_ref_nothing_has_pushed_cannot_be_landed(self) -> None:
        landed, why = travel.land_wip(self.two, travel.wip_ref("ordering"), "slice/ORD-01")
        self.assertFalse(landed)
        self.assertIn("ordering", why)

    def test_a_dirty_checkout_is_refused_rather_than_overwritten(self) -> None:
        """A person's uncommitted work is not this process's to discard, and a takeover that did it once
        would be a takeover nobody let near a real machine again."""
        self.branch(self.one, "slice/ORD-01", "rungs.txt", "one\n")
        travel.push_wip(self.one, "slice/ORD-01", travel.wip_ref("ordering"))
        (self.two / "project.json").write_text('{"edited": true}', encoding="utf-8")
        landed, why = travel.land_wip(self.two, travel.wip_ref("ordering"), "slice/ORD-01")
        self.assertFalse(landed)
        self.assertIn("project.json", why)


class DepartTest(Fixture):
    """The pass `/sail` runs at every boundary, and the two sets inside it that are not the same set.

    `travel.depart` is what a plain session calls and what the harbourmaster calls, which is the point of
    it being here: a credentialled process and a person's `/sail` travelling by two different rules would
    be two answers to what travels.
    """

    #: What `depart` calls itself in this process. The fixture's ONE and TWO name two *clones*; the
    #: machine identity is whatever `logs.machine()` answers here, and `depart` pushes what that wrote.
    HERE = ""

    def setUp(self) -> None:
        super().setUp()
        self.HERE = logs.machine()

    def push(self, where: Path, fairway: str, machine: str = "") -> tuple[list[str], list[str]]:
        claims.take(where, fairway, machine or self.HERE)
        return travel.depart(where)

    def test_it_pushes_the_log_of_a_fairway_this_machine_holds(self) -> None:
        self.deck(self.one, "ordering", line("claimed", "2026-10-12T09:00:00Z",
                                             fairway="ordering", slice="ORD-01"))
        went, refused = self.push(self.one, "ordering")
        self.assertIn(travel.deck_ref("ordering"), went)
        # The one refusal here is the in-flight branch: the log names a claimed slice and no `slice/ORD-01`
        # was ever made, which is exactly what `push_wip` is meant to say rather than invent.
        self.assertTrue(all("wip" in why or "slice/ORD-01" in why for why in refused), refused)
        travel.fetch(self.two)
        self.assertIn("ORD-01", travel.held(self.two, travel.deck_ref("ordering")) or "")

    def test_a_released_fairway_still_owes_its_final_line(self) -> None:
        """A captain writes `merged` or `parked` and *then* releases, so the last line is always written
        one pass before the release. A set built from held claims alone drops it, and nobody sees it
        again: the log is on one machine and the ref is a line behind for ever."""
        path = self.deck(self.one, "ordering", line("claimed", "2026-10-12T09:00:00Z",
                                                    fairway="ordering", slice="ORD-01"))
        self.push(self.one, "ordering")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line("merged", "2026-10-12T10:00:00Z", fairway="ordering", slice="ORD-01",
                              commit="abc1234"))
        claims.release(self.one, "ordering", self.HERE)
        went, _ = travel.depart(self.one)
        self.assertIn(travel.deck_ref("ordering"), went)
        travel.fetch(self.two)
        self.assertIn("merged", travel.held(self.two, travel.deck_ref("ordering")) or "")

    def test_it_never_pushes_the_log_of_a_fairway_another_machine_holds(self) -> None:
        """One ref per writer is the invariant the whole design rests on."""
        self.deck(self.one, "ordering", line("claimed", "2026-10-12T09:00:00Z", fairway="ordering"))
        claims.take(self.one, "ordering", TWO)
        went, _ = travel.depart(self.one)
        self.assertNotIn(travel.deck_ref("ordering"), went)

    def test_arrive_lands_what_the_other_machine_pushed(self) -> None:
        path = self.deck(self.one, "ordering", line("mark-set", "2026-10-12T09:00:00Z",
                                                    fairway="ordering", slice="ORD-01", mark="OrderPlaced"))
        self.push(self.one, "ordering")
        self.assertEqual(travel.arrive(self.two), [".slipwai/logs/model/ordering.jsonl"])
        self.assertEqual((self.two / ".slipwai/logs/model/ordering.jsonl").read_text(encoding="utf-8"),
                         path.read_text(encoding="utf-8"))

    def test_a_project_with_no_forge_departs_nothing_and_is_not_an_error(self) -> None:
        """One machine, no remote. Everything still works; nothing travels, and that is not a failure."""
        git("remote", "remove", "origin", where=self.one)
        self.assertEqual(travel.depart(self.one), ([], []))


class LeaseTest(unittest.TestCase):
    """What a claim lapses on. Derived from `stage_bound` and never chosen — and above it, so that the
    guarantee falls out rather than being asserted: a captain that writes nothing for `stage_bound` ends
    that stage itself, so a lease above it can never take a stream from a captain that is working."""

    def test_the_lease_is_always_longer_than_the_stage_it_is_derived_from(self) -> None:
        for minutes in (1, 15, 30, 90, 240):
            self.assertGreater(travel.lease(minutes * 60.0), minutes * 60.0, minutes)

    def test_it_always_clears_the_round_trip_a_pushed_log_takes(self) -> None:
        """Liveness is judged on the *pushed* log, so what a taker reads is older than what was written by
        a heartbeat, a push interval and a fetch interval. A lease under that sum could lapse on a captain
        that is writing, which is the one thing a lease may never do."""
        for minutes in (0, 1, 15, 90):
            self.assertGreater(travel.lease(minutes * 60.0), travel.ROUND_TRIP, minutes)

    def test_it_moves_with_the_telegraph_because_the_stage_bound_does(self) -> None:
        self.assertGreater(travel.lease(90 * 60.0), travel.lease(45 * 60.0))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
