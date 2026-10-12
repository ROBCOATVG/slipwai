"""The claim: one git ref per fairway, and what happens to the second machine that wants it.

Two people can run version 2 on two machines today and it looks as though it works — the logs sync, the
marks carry, the board folds. What makes that misleading is that nothing stopped two machines running a
captain for one fairway, and the whole log design rests on one rule: one writer per file. Two captains for
`ordering` is two processes appending to one `.jsonl` through two worktrees, which is a merge conflict in
the file the design promised would never have one and, where one side forces the ref, silently lost lines.

So the claim is a git ref and nothing of ours has to be running to decide it: a push that is not a
fast-forward is refused by every forge there is, which is an atomic compare-and-swap for free. These cases
run two real clones of one real bare repository, because what is being proved is git's behaviour and a fake
of it would prove the fake.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT


def loaded() -> Any:
    """`claims.py` as the module it is inside a project, loaded from where the toolkit keeps it.

    By path rather than by name: it is not importable as `slipwai.claims` and never will be — it ships in a
    generated project, which has no slipwai to import, and it puts its own directory on the path so that
    `logs.py` beside it resolves the same way there as here.
    """
    spec = importlib.util.spec_from_file_location("claims", TOOLKIT_ROOT / "scripts/agents/claims.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    # In `sys.modules` before it runs: `dataclass` resolves a field's annotation through the module its
    # class says it came from, and a module that is not there resolves to nothing at class-creation time.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


claims = loaded()

ONE = "harbour_one"
TWO = "harbour_two"


def git(*argv: str, where: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                          cwd=where, capture_output=True, text=True, check=False)


class Fixture(unittest.TestCase):
    """A bare repository standing in for the forge, and two clones standing in for two machines.

    A bare repository is what a forge is, as far as a push is concerned: `receive-pack` refuses a
    non-fast-forward there for the same reason and with the same words GitHub does. Nothing here reaches a
    network, and nothing here pushes to anywhere real.
    """

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


class TakingTest(Fixture):
    def test_the_first_machine_takes_it_and_the_second_is_refused_by_name(self) -> None:
        """The whole of the slice in one case: the refusal says who holds it and since when, rather than
        both machines appending to one log and finding out at a merge."""
        first = claims.take(self.one, "ordering", ONE)
        self.assertTrue(first.ours, first.why)
        second = claims.take(self.two, "ordering", TWO)
        self.assertFalse(second.ours)
        self.assertIsNotNone(second.holder)
        assert second.holder is not None
        self.assertEqual(second.holder.machine, ONE)
        self.assertIn(ONE, second.why)
        self.assertIn(second.holder.since, second.why)

    def test_the_second_machine_never_gets_the_ref_even_though_it_minted_a_commit(self) -> None:
        """A refused push must leave nothing behind locally, or the next read on that machine answers from
        its own failed attempt and two machines each believe they hold it."""
        claims.take(self.one, "ordering", ONE)
        claims.take(self.two, "ordering", TWO)
        held = claims.holder(self.two, "ordering")
        self.assertIsNotNone(held)
        assert held is not None
        self.assertEqual(held.machine, ONE)

    def test_the_machine_that_holds_it_takes_it_again(self) -> None:
        """A captain's every turn takes the claim, so taking what you already hold is the common case and
        not an error. A restarted captain would otherwise lock itself out of its own fairway."""
        self.assertTrue(claims.take(self.one, "ordering", ONE).ours)
        again = claims.take(self.one, "ordering", ONE)
        self.assertTrue(again.ours, again.why)

    def test_two_fairways_are_two_claims(self) -> None:
        self.assertTrue(claims.take(self.one, "ordering", ONE).ours)
        self.assertTrue(claims.take(self.two, "billing", TWO).ours)


class ReleasingTest(Fixture):
    def test_a_released_fairway_is_taken_by_the_other_machine(self) -> None:
        claims.take(self.one, "ordering", ONE)
        self.assertTrue(claims.release(self.one, "ordering", ONE))
        taken = claims.take(self.two, "ordering", TWO)
        self.assertTrue(taken.ours, taken.why)
        held = claims.holder(self.one, "ordering")
        assert held is not None
        self.assertEqual(held.machine, TWO)

    def test_nothing_is_ever_deleted_so_who_held_it_is_still_readable(self) -> None:
        """A claim that was taken by deleting and recreating a ref is a claim whose history is gone, and
        *who had this fairway last Tuesday* is a question somebody asks after a bad merge."""
        claims.take(self.one, "ordering", ONE)
        claims.release(self.one, "ordering", ONE)
        claims.take(self.two, "ordering", TWO)
        shown = git("log", "--format=%an", claims.ref("ordering"), where=self.two)
        self.assertEqual(shown.stdout.split(), [TWO, ONE, ONE])

    def test_a_machine_cannot_release_a_claim_it_does_not_hold(self) -> None:
        claims.take(self.one, "ordering", ONE)
        self.assertFalse(claims.release(self.two, "ordering", TWO))
        held = claims.holder(self.two, "ordering")
        assert held is not None
        self.assertEqual(held.machine, ONE)

    def test_a_fairway_nobody_has_ever_claimed_is_held_by_nobody(self) -> None:
        self.assertIsNone(claims.held_by(self.one, "ordering"))
        self.assertIsNone(claims.holder(self.one, "ordering"))


class LeaseTest(Fixture):
    """What a claim lapses on, and the one thing a lease may never do.

    A person closing their laptop must not park a stream for ever — a captain killed outright never
    releases its claim, and until there was a lease the only answer was somebody running `claims.py
    --release` on a machine that may be shut. But a stream must never be taken from somebody who is
    mid-slice, so the lease is derived from `stage_bound` and sits above it: a captain that writes nothing
    for `stage_bound` ends that stage itself, so the guarantee falls out rather than being asserted.

    Liveness is judged on the *pushed* log, because what one machine can know about another is exactly what
    the other has pushed. `heard` is that instant, and these cases pass it directly: what is being proved
    here is the arithmetic over it, and `test_travel.py` proves where it comes from.
    """

    def ago(self, seconds: float) -> str:
        return (datetime.now(UTC) - timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def held_since(self, fairway: str, seconds_ago: float) -> None:
        """The first machine took this fairway that long ago, which is what `since` on a real claim says.

        Through git's own author date rather than by editing the ref, because `since` *is* the commit's
        author date and a fixture that wrote it some other way would be proving something else.
        """
        os.environ["GIT_AUTHOR_DATE"] = self.ago(seconds_ago)
        try:
            taken = claims.take(self.one, fairway, ONE)
        finally:
            os.environ.pop("GIT_AUTHOR_DATE", None)
        self.assertTrue(taken.ours, taken.why)

    def test_no_lease_ever_lapses_under_a_captain_that_is_writing(self) -> None:
        """The slice's own done-when, and the half that matters: a lease that took a stream from a working
        captain would lose the work it was built to save. The claim here is an hour old and its captain
        wrote a line a moment ago, which is what every long slice looks like."""
        self.held_since("ordering", 3600)
        second = claims.take(self.two, "ordering", TWO, lease=60.0, heard=self.ago(0))
        self.assertFalse(second.ours)
        self.assertFalse(second.took_over)
        self.assertIn(ONE, second.why)

    def test_a_claim_nobody_has_been_heard_from_within_the_lease_is_taken_over(self) -> None:
        self.held_since("ordering", 3600)
        second = claims.take(self.two, "ordering", TWO, lease=60.0, heard=self.ago(600))
        self.assertTrue(second.ours, second.why)
        self.assertTrue(second.took_over)
        assert second.holder is not None
        self.assertEqual(second.holder.machine, ONE)
        self.assertIn(ONE, second.why)

    def test_a_takeover_leaves_the_fairway_this_machines_and_says_who_it_was(self) -> None:
        """Nothing is deleted, here least of all: *who had this stream when it stopped* is the first
        question somebody asks about a takeover."""
        self.held_since("ordering", 3600)
        claims.take(self.two, "ordering", TWO, lease=60.0, heard=self.ago(600))
        now = claims.held_by(self.one, "ordering")
        assert now is not None
        self.assertEqual(now.machine, TWO)
        shown = git("log", "--format=%an", claims.ref("ordering"), where=self.two)
        self.assertEqual(shown.stdout.split(), [TWO, ONE])

    def test_a_claim_with_no_lease_at_all_is_never_taken_however_old(self) -> None:
        """`0` is off, and off is the default: a lease is a thing the captain works out from the harbour's
        own numbers, and a caller that did not is not one that meant *take it from them*."""
        self.held_since("ordering", 100000)
        second = claims.take(self.two, "ordering", TWO, lease=0.0, heard=self.ago(100000))
        self.assertFalse(second.ours)

    def test_a_claim_nothing_has_been_heard_from_at_all_runs_from_when_it_was_taken(self) -> None:
        """A captain that has taken its claim and not yet written a line is starting, not gone — and a
        lease measured from an empty log would take the stream off it before its first rung."""
        self.held_since("ordering", 10)
        second = claims.take(self.two, "ordering", TWO, lease=60.0, heard="")
        self.assertFalse(second.ours)
        self.assertIn(ONE, second.why)

    def test_an_instant_nothing_can_read_is_not_evidence_that_a_captain_is_gone(self) -> None:
        """An unreadable claim must never read as free, and the same holds for an unreadable instant: the
        safe answer is that somebody holds it."""
        self.held_since("ordering", 100000)
        second = claims.take(self.two, "ordering", TWO, lease=60.0, heard="not a timestamp")
        self.assertFalse(second.ours)


class NoForgeTest(unittest.TestCase):
    """One machine, no remote at all — which is the case that has to keep working with no network, and the
    case where the ref is the claim itself rather than a mirror of the forge's."""

    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "alone"
        self.root.mkdir()
        git("init", "--quiet", "--initial-branch=main", where=self.root)
        (self.root / "project.json").write_text("{}", encoding="utf-8")
        git("add", "-A", where=self.root)
        git("commit", "--quiet", "-m", "the skeleton", where=self.root)

    def test_the_claim_is_taken_locally_and_says_it_is_local(self) -> None:
        taken = claims.take(self.root, "ordering", ONE)
        self.assertTrue(taken.ours, taken.why)
        self.assertFalse(claims.forge(self.root))
        held = claims.held_by(self.root, "ordering")
        assert held is not None
        self.assertTrue(held.local)

    def test_a_second_captain_on_one_machine_is_still_refused(self) -> None:
        """`update-ref` with the value it must already have is the same compare-and-swap the push is, so
        the no-network case is not a weaker rule — it is a smaller one."""
        claims.take(self.root, "ordering", ONE)
        second = claims.take(self.root, "ordering", TWO)
        self.assertFalse(second.ours)
        assert second.holder is not None
        self.assertEqual(second.holder.machine, ONE)


class NoRepositoryTest(unittest.TestCase):
    """A directory that is not a git repository at all. Nothing can hold a fairway there and that has to be
    said rather than crashed on or quietly treated as free."""

    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def test_it_says_nothing_can_hold_a_fairway_here(self) -> None:
        taken = claims.take(self.root, "ordering", ONE)
        self.assertTrue(taken.ours)
        self.assertIn("no git repository", taken.why)
        self.assertIsNone(claims.holder(self.root, "ordering"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
