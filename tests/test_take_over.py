"""A stream taken from a machine that has stopped, and carried on rather than started again.

11.1 left a hole it named: a captain killed outright never releases its claim, so a closed laptop parked a
fairway until somebody ran `claims.py --release` on a machine that may be shut. The lease closes it — but a
lapsed claim on its own leaves the work *unreachable*, because a captain holds no credential and a slice
branch lives only on the machine that built it. So the two halves land together: the lease, and the branch
that travelled under `refs/slipwai/wip/<fairway>` while that machine was still running.

No remote here: this harbour's refs are its own, which is the smaller version of the same rule and the one
that has to work with no network at all. `test_two_machines.py` is the same thing over a forge, with two
clones and a real `/sail` stand-in that resumes where the first machine stopped.
"""
from __future__ import annotations

import os
import subprocess
import unittest
from datetime import UTC, datetime, timedelta

import checkout_packages  # noqa: F401
from captain_fixture import WORKS, Fixture

from slipwai import logs


class TakeOverTest(Fixture):
    def git(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                              cwd=self.root, capture_output=True, text=True, check=False)

    def stopped_four_rungs_in(self, machine: str, seconds_ago: float = 100000) -> str:
        """The state the other machine left: a claim it never released, a log, and a branch it had pushed.

        The claim is backdated through git's own author date, because `since` *is* the commit's author date
        and a fixture that wrote it some other way would be proving something else.
        """
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "the skeleton")
        self.git("checkout", "--quiet", "-b", "slice/ORD-01")
        (self.root / "rungs.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "--quiet", "-m", "four rungs in")
        made = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("update-ref", "refs/slipwai/wip/ORD", made)
        self.git("checkout", "--quiet", "main")
        self.git("branch", "--quiet", "-D", "slice/ORD-01")
        (self.root / "rungs.txt").unlink(missing_ok=True)
        at = (datetime.now(UTC) - timedelta(seconds=seconds_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
        os.environ["GIT_AUTHOR_DATE"] = at
        try:
            self.hold("ORD", machine)
        finally:
            os.environ.pop("GIT_AUTHOR_DATE", None)
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01", t=at))
        return made

    def test_the_stream_is_taken_and_its_in_flight_branch_comes_with_it(self) -> None:
        """The slice's done-when: a machine four rungs into a slice is taken over by another, which
        resumes at rung five instead of starting again."""
        made = self.stopped_four_rungs_in("harbour_one")
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS), machine="harbour_two")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        held = self.git("log", "--format=%an", "refs/slipwai/claims/ORD").stdout.split()
        self.assertEqual(held, ["harbour_two", "harbour_two", "harbour_one"], done.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), made, done.stdout)
        self.assertEqual((self.root / "rungs.txt").read_text(encoding="utf-8"), "one\ntwo\nthree\nfour\n")

    def test_it_resumes_the_slice_that_was_in_flight_rather_than_the_next_one(self) -> None:
        """Four rungs of work discarded in silence is worse than a fairway that stays held, which is why
        the lease was refused on its own. The slice to carry on with is the one the taken log was on."""
        self.stopped_four_rungs_in("harbour_one")
        self.grant("ORD-01")
        self.captain("ORD", self.sail(WORKS), machine="harbour_two")
        self.assertEqual([str(e.fields["slice"]) for e in self.read("ORD") if e.kind == "merged"],
                         ["ORD-01"])

    def test_the_lines_the_other_machine_wrote_are_there_and_still_first(self) -> None:
        """The deck log is one chain per fairway and the claim makes its writer unique at any instant, so
        a takeover takes the pen: the predecessor's lines come over whole and this machine appends."""
        self.stopped_four_rungs_in("harbour_one")
        self.grant("ORD-01")
        self.captain("ORD", self.sail(WORKS), machine="harbour_two")
        found = self.read("ORD")
        kinds = [e.kind for e in found]
        self.assertEqual(kinds[0], "claimed")
        self.assertIn("taken-over", kinds)
        over = [e for e in found if e.kind == "taken-over"][0]
        self.assertEqual(over.fields["from"], "harbour_one")
        self.assertEqual(over.fields["slice"], "ORD-01")

    def test_a_machine_that_is_still_writing_keeps_its_stream(self) -> None:
        """The one thing a lease may never do. The claim is old, and its captain wrote a line a moment
        ago, which is what a long slice looks like from outside."""
        self.stopped_four_rungs_in("harbour_one")
        self.deck("ORD", logs.entry("heartbeat", fairway="ORD"))
        done = self.captain("ORD", self.sail(WORKS), machine="harbour_two")
        self.assertIn("ORD is held by harbour_one", done.stdout)
        self.assertEqual(self.claimed_by("ORD"), "harbour_one")

    def test_a_takeover_with_nothing_to_carry_says_so_rather_than_starting_again(self) -> None:
        """A lapsed claim whose branch never travelled is the case the lease alone would have left: the
        work is unreachable, and carrying on as though it were not would discard it in silence."""
        self.stopped_four_rungs_in("harbour_one")
        self.git("update-ref", "-d", "refs/slipwai/wip/ORD")
        done = self.captain("ORD", self.sail(WORKS), machine="harbour_two")
        self.assertIn("parked", done.stdout.lower())
        self.assertIn("refs/slipwai/wip/ORD", "".join(str(e.fields.get("why", ""))
                                                      for e in self.read("ORD")))


if __name__ == "__main__":
    unittest.main()
