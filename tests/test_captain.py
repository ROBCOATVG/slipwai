"""The captain: what it claims, what it watches, and what parks it.

The one thing proved here over and over is the inversion the first attempt lacked: the captain believes the
deck log and nothing else. A fake `/sail` that writes the expected lines gets a slice through; a fake that
writes nothing is ended and parked, however alive its process is.

It runs inside a generated project, so it is run here as a script against a directory laid out like one.
`captain_fixture.py` beside this holds the project and the fake; `test_captain_gate.py` holds what closes a
slice and what merges it.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

import checkout_packages  # noqa: F401
from captain_fixture import SILENT, SLICES, WORKS, Fixture, fake_drive  # noqa: F401

from slipwai import logs


class ChoosingTest(Fixture):
    def test_it_claims_the_first_slice_of_its_own_fairway(self) -> None:
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertEqual(done.returncode, 0, done.stderr)
        claimed = [e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"]
        self.assertEqual(claimed, ["ORD-01"])

    def test_it_never_claims_another_fairway_s_slice(self) -> None:
        self.grant("ORD-01")
        self.captain("ORD", self.sail(WORKS))
        self.assertEqual([e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"], ["ORD-01"])

    def test_a_slice_whose_mark_is_unset_is_waited_on_and_said(self) -> None:
        """A sibling unblocks by having planned, not by having merged — so BIL waits on Paid being set."""
        done = self.captain("BIL", self.sail(WORKS))
        self.assertIn("BIL-01 waits on", done.stdout)
        self.assertIn("Paid", done.stdout)

    def test_a_mark_set_by_a_sibling_clears_it_without_a_merge(self) -> None:
        """The whole of the parallelism: the clearing line is written at the setting slice's first stage."""
        self.deck("ORD", logs.entry("mark-set", fairway="ORD", slice="ORD-02", mark="Paid"))
        self.grant("BIL-01")
        done = self.captain("BIL", self.sail(WORKS))
        self.assertIn("BIL-01", done.stdout)
        self.assertIn("merged", done.stdout)

    def test_a_claimed_slice_is_not_claimed_twice(self) -> None:
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"))
        self.grant("ORD-02")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertIn("ORD-02", done.stdout)

    def test_a_parked_fairway_stays_parked_and_says_why(self) -> None:
        """A captain that quietly carried on past a park would be the status field all over again."""
        self.deck("ORD", logs.entry("parked", fairway="ORD", why="a person has to look at this"))
        done = self.captain("ORD", self.sail(WORKS))
        self.assertIn("is parked", done.stdout)
        self.assertIn("a person has to look", done.stdout)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "claimed"], [])

    def test_an_answered_park_resumes_its_claimed_slice_rather_than_skipping_it(self) -> None:
        at = "2026-10-12T09:00:00Z"
        self.deck("ORD", logs.entry("claimed", fairway="ORD", slice="ORD-01"),
                  logs.entry("parked", fairway="ORD", why="choose the storage", t=at))
        self.harbour(logs.entry("cleared", harbour=True, fairway="ORD", parked=at, what="use the store"))
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertIn("ORD-01 is through its gate and merged", done.stdout)
        self.assertEqual([e.fields["slice"] for e in self.read("ORD") if e.kind == "merged"], ["ORD-01"])

    def test_a_fairway_the_chart_does_not_name_is_said_rather_than_guessed_at(self) -> None:
        done = self.captain("NOPE", self.sail(WORKS))
        self.assertIn("no slices", done.stdout)


class ClaimTest(Fixture):
    """One machine holds a fairway at a time, and the ref is what says so.

    Nothing stopped two machines running a captain for one fairway, and the whole log design rests on one
    writer per file: two captains for `ordering` is two processes appending to one `.jsonl` through two
    worktrees. A `claimed` line could never fix it, being the thing protected.
    """

    def test_it_holds_the_claim_ref_while_the_slice_is_being_worked(self) -> None:
        """Asked from inside `/sail`, because that is the only moment the question matters: while this
        machine is writing to the deck log, the ref has to say the fairway is this machine's."""
        watcher = ("import subprocess, pathlib\n"
                   "shown = subprocess.run(['git', 'show', '-s', '--format=%an',"
                   " 'refs/slipwai/claims/ORD'], capture_output=True, text=True)\n"
                   "pathlib.Path('held.txt').write_text(shown.stdout.strip(), encoding='utf-8')\n")
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(watcher + WORKS), machine="harbour_one")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((self.root / "held.txt").read_text(encoding="utf-8"), "harbour_one", done.stdout)

    def test_a_fairway_another_machine_holds_is_refused_by_name(self) -> None:
        """The refusal is the whole point: the silent corruption becomes a message naming who and when."""
        self.hold("ORD", "harbour_one")
        done = self.captain("ORD", self.sail(WORKS), machine="harbour_two")
        self.assertIn("harbour_one", done.stdout)
        self.assertIn("ORD is held by", done.stdout)

    def test_and_writes_nothing_at_all_to_the_other_machine_s_log(self) -> None:
        """Not even a `parked`: the deck log is the file the claim exists to keep one writer on, so a
        captain that was refused the claim and then wrote its reason into it would have done the damage
        while explaining that it must not."""
        self.hold("ORD", "harbour_one")
        self.grant("ORD-01")
        self.captain("ORD", self.sail(WORKS), machine="harbour_two")
        self.assertEqual(self.read("ORD"), [])

    def test_the_claim_is_given_back_when_the_captain_stops(self) -> None:
        """A captain that kept the claim after it stopped would park the fairway for every other machine
        until somebody went looking for a ref."""
        self.grant("ORD-01")
        self.captain("ORD", self.sail(WORKS), machine="harbour_one")
        self.assertEqual(self.claimed_by("ORD"), "")

    def test_the_machine_that_holds_it_runs_again(self) -> None:
        """Re-taking your own claim is the common case: a captain takes it every turn."""
        self.hold("ORD", "harbour_one")
        self.grant("ORD-01")
        done = self.captain("ORD", self.sail(WORKS), machine="harbour_one")
        self.assertIn("ORD-01", done.stdout)
        self.assertEqual([e.fields["slice"] for e in self.read("ORD") if e.kind == "claimed"], ["ORD-01"])


class WatchingTest(Fixture):
    def test_a_drive_that_writes_nothing_is_ended_and_parked_with_the_reason(self) -> None:
        """Not because the agent said it was stuck — a stuck agent cannot say so — but because the log stopped."""
        self.budget(minutes=0.05)
        done = self.captain("ORD", self.sail(SILENT), timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        parked = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1)
        self.assertIn("made no progress", str(parked[0].fields["why"]))

    def test_a_drive_that_writes_lines_is_not_ended(self) -> None:
        self.budget(minutes=0.05)
        keeps_writing = """import sys, json, pathlib, datetime, time
fairway = sys.argv[2]
path = pathlib.Path(".slipwai/logs/ordering") / (fairway + ".jsonl")
path.parent.mkdir(parents=True, exist_ok=True)
for n in range(4):
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"v": 1, "t": now, "kind": "heartbeat", "fairway": fairway}) + "\\n")
    time.sleep(1)
"""
        done = self.captain("ORD", self.sail(keeps_writing), timeout=120)
        # It parks, but on the gate rather than on the watch: this fake writes a line every second and
        # never the ones that close a slice. The assertion is about the watcher, so it is about the
        # watcher's own reason.
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertNotIn("the stage was ended", " ".join(parked), done.stdout)

    def test_with_no_harness_and_no_override_it_says_so_rather_than_naming_a_missing_mark(self) -> None:
        """The two are different faults with different answers. A session nobody could start is not a slice
        that was built badly, and parking on "no `mark-set` was written" would send somebody to read a
        slice that is fine."""
        done = subprocess.run([sys.executable, str(self.script), "ORD", "--once"],
                              capture_output=True, text=True, cwd=self.root, timeout=90,
                              env={key: value for key, value in os.environ.items() if key != "SLIPWAI_SAIL"})
        self.assertEqual(done.returncode, 0, done.stderr)
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1, done.stdout)
        self.assertIn("no harness", parked[0])
        self.assertIn("SLIPWAI_SAIL", parked[0])
        self.assertNotIn("mark-set", parked[0])

    def test_a_drive_that_fails_parks_with_what_it_exited(self) -> None:
        self.captain("ORD", self.sail("import sys\nsys.exit(3)\n"))
        parked = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("exited 3", str(parked[0].fields["why"]))


class MergeTest(Fixture):
    def test_the_merge_is_asked_of_the_harbourmaster_and_never_done(self) -> None:
        """A captain holds no credential: a berth with a token in it is a sandbox with a way out."""
        self.grant("ORD-01")
        self.captain("ORD", self.sail(WORKS))
        asked = [e for e in self.read("ORD") if e.kind == "request"]
        self.assertEqual(len(asked), 1)
        self.assertEqual(asked[0].fields["what"], "merge")
        self.assertEqual(asked[0].fields["id"], "merge-ORD-01")
        self.assertEqual(asked[0].fields["slice"], "ORD-01")

    def test_merged_is_written_against_the_commit_the_answer_names(self) -> None:
        """For a long while `granted` was read by nothing and no `merged` line was written by anything, so
        the board said `merged: 0` for ever while slices were being accepted at their demos."""
        self.grant("ORD-01", commit="deadbee")
        done = self.captain("ORD", self.sail(WORKS))
        landed = [e for e in self.read("ORD") if e.kind == "merged"]
        self.assertEqual(len(landed), 1, done.stdout)
        self.assertEqual(landed[0].fields["commit"], "deadbee")
        self.assertEqual(landed[0].fields["slice"], "ORD-01")

    def test_an_answer_that_never_comes_parks_at_the_wait_bound(self) -> None:
        """A wait with no end is indistinguishable from a run that has stopped, which is the whole of why
        `wait_bound` exists."""
        done = self.captain("ORD", self.sail(WORKS))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("did not answer", parked[0], done.stdout)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "merged"], [])

    def test_a_harbourmaster_that_is_writing_is_waited_for_past_the_bound(self) -> None:
        """The bound is on the harbourmaster's silence, not on the clock since the request.

        This is the inversion the rest of this file is built on, applied to the one wait a captain has: a
        harbour that is writing lines is a harbour that is working, and a bound measured from the request
        parks a slice whose merge is being gated at that moment. It cost
        `test_loop.test_the_whole_loop_reaches_trunk_with_no_person_in_the_path` one Windows run in two — the
        captain reached `request`, the harbourmaster's pass took longer than a bound chosen for the cases
        that have no harbourmaster at all, and a slice that merged was reported parked.

        Here the harbour writes a line a second for four seconds against a bound of three, then answers. A
        clock from the request gives up at the fourth second; silence is what has to run out.
        """
        import threading
        import time
        answered = threading.Event()

        def harbourmaster() -> None:
            for _ in range(2000):
                if any(e.kind == "request" for e in self.read("ORD")):
                    break
                time.sleep(0.02)
            else:
                return
            for mark in ("Shipped", "Invoiced", "Refunded", "Settled"):
                time.sleep(1.0)
                self.harbour(logs.entry("mark-set", harbour=True, fairway="BIL", slice="BIL-09", mark=mark))
            self.grant("ORD-01", commit="latecom")
            answered.set()

        keeper = threading.Thread(target=harbourmaster, daemon=True)
        keeper.start()
        done = self.captain("ORD", self.sail(WORKS))
        keeper.join(30)
        self.assertTrue(answered.is_set(), "the answer was never written, so this proved nothing")
        landed = [e for e in self.read("ORD") if e.kind == "merged"]
        self.assertEqual(len(landed), 1, done.stdout + done.stderr)
        self.assertEqual(landed[0].fields["commit"], "latecom")

    def test_a_refusal_nothing_in_a_berth_can_fix_parks_at_once(self) -> None:
        self.refuse("ORD-01", "there is no branch slice/ORD-01 to merge")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertEqual(len([e for e in self.read("ORD") if e.kind == "request"]), 1, done.stdout)
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("no branch", parked[0])

    def test_a_conflict_sends_the_captain_back_into_its_berth_and_it_asks_again(self) -> None:
        """Resolving a conflict is work on code, which belongs where the context is. The harbourmaster stays
        credentials-and-gate only, because it is the one thing in a harbour with push rights."""
        self.refuse("ORD-01", "slice/ORD-01 conflicts with origin/main in package-lock.json", resolve=True)
        self.grant("ORD-01", commit="fixed01", asked=1)
        done = self.captain("ORD", self.sail(WORKS))
        asked = [str(e.fields["id"]) for e in self.read("ORD") if e.kind == "request"]
        self.assertEqual(asked, ["merge-ORD-01", "merge-ORD-01-1"], done.stdout)
        landed = [e for e in self.read("ORD") if e.kind == "merged"]
        self.assertEqual(landed[0].fields["commit"], "fixed01")

    def test_a_conflict_that_outlasts_the_attempts_parks_saying_so(self) -> None:
        self.budget(minutes=5, attempts=1)
        for asked in (0, 1):
            self.refuse("ORD-01", "it conflicts in package-lock.json", resolve=True, asked=asked)
        done = self.captain("ORD", self.sail(WORKS))
        parked = [str(e.fields["why"]) for e in self.read("ORD") if e.kind == "parked"]
        self.assertIn("2 attempt(s)", parked[0], done.stdout)

    def test_an_unanswered_message_from_a_person_parks_the_fairway_at_the_boundary(self) -> None:
        self.deck("ORD", logs.entry("told", fairway="ORD", message="stop and talk to me",
                                    t="2020-01-01T00:00:00Z"))
        self.captain("ORD", self.sail(WORKS))
        parked = [e for e in self.read("ORD") if e.kind == "parked"]
        self.assertEqual(len(parked), 1)
        self.assertEqual([e for e in self.read("ORD") if e.kind == "request"], [])


class LogTest(Fixture):
    def test_a_deck_log_it_cannot_read_stops_it_rather_than_being_carried_past(self) -> None:
        """The log is the state. Carrying on past a line nobody can read is answering wrongly."""
        path = self.root / logs.deck_path("ordering", "ORD")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json\n", encoding="utf-8")
        done = self.captain("ORD", self.sail(WORKS))
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("cannot be read", done.stderr)


if __name__ == "__main__":
    unittest.main()
