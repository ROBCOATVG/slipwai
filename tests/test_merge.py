"""The merge the harbourmaster performs: a real repository, because a merge is entirely git.

`granted` was written and read by nothing, and no `merged` line was written by anything, so the board said
`merged: 0` for ever while slices were being accepted at their demos. This is the suite that holds the other
half: the rebase, the gate, the advance, and each of the four ways it can refuse instead.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from datetime import UTC, datetime, timedelta

import checkout_packages  # noqa: F401
from harbourmaster_fixture import Fixture, MergeFixture  # noqa: F401

from slipwai import logs


class MergeTest(MergeFixture):
    def test_a_granted_merge_advances_trunk_and_the_answer_names_the_commit(self) -> None:
        """`granted` was written and read by nothing, and no `merged` line was written by anything, so the
        board said `merged: 0` for ever while slices were being accepted at their demos."""
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        done = self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "granted", f"{answer.fields}\n{done.stderr}")
        self.assertEqual(answer.fields["commit"], self.head("main"))
        self.assertNotEqual(self.head("main"), self.trunk_was)
        self.assertEqual(self.git("show", "main:service.txt").stdout, "one\ntwo\n")

    def test_the_slice_is_rebased_onto_trunk_rather_than_merged_over_it(self) -> None:
        """One at a time onto a trunk that already holds every merge before it, so the gate's result is
        evidence about the trunk the commit actually lands on."""
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.git("checkout", "--quiet", "main")
        (self.root / "another.txt").write_text("somebody else\n", encoding="utf-8")
        self.commit("a commit trunk gained meanwhile")
        self.git("checkout", "--quiet", "parked-elsewhere")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted")
        # One parent: a rebase, not a merge commit.
        self.assertEqual(len(self.git("rev-list", "--parents", "-1", "main").stdout.split()) - 1, 1)
        self.assertEqual(self.git("show", "main:another.txt").stdout, "somebody else\n")

    def test_a_conflict_is_aborted_and_refused_naming_the_paths(self) -> None:
        """Resolving it is work on code, which belongs in the berth where the context is. This process stays
        credentials-and-gate only, because it is the one thing in a harbour with push rights."""
        self.slice_branch("ORD-01", "service.txt", "one\nfrom the slice\n")
        self.git("checkout", "--quiet", "main")
        (self.root / "service.txt").write_text("one\nfrom trunk\n", encoding="utf-8")
        self.commit("trunk moved under it")
        self.git("checkout", "--quiet", "parked-elsewhere")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused")
        self.assertIn("service.txt", str(answer.fields["why"]))
        self.assertTrue(answer.fields["resolve"], "a conflict is something a berth can fix")
        self.assertEqual(self.head("main"), self.head("main"))
        self.assertNotIn("rebase", self.git("status", "--porcelain=v2", "--branch").stdout)

    def test_a_failing_gate_refuses_and_leaves_trunk_where_it_was(self) -> None:
        """The gate is the project's own `make verify` — the same one the two-gate rule names, so a project
        that adds a check gets it at the merge for nothing."""
        self.slice_branch("ORD-01", "Makefile", "verify:\n\t@echo 'check-imports: a layer violation'; exit 1\n")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused")
        self.assertIn("the full gate failed", str(answer.fields["why"]))
        self.assertTrue(answer.fields["resolve"])
        self.assertEqual(self.head("main"), self.trunk_was)

    def test_a_branch_that_is_not_there_is_refused_and_is_not_a_berth_s_to_fix(self) -> None:
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused")
        self.assertIn("no branch slice/ORD-01", str(answer.fields["why"]))
        self.assertFalse(answer.fields["resolve"])

    def test_the_scratch_worktree_is_gone_afterwards_either_way(self) -> None:
        """It is made for one merge and removed either way, so a failure leaves no half-rebased branch
        anywhere a captain or a person is working."""
        self.slice_branch("ORD-01", "Makefile", "verify:\n\texit 1\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertFalse((self.root / ".slipwai/merge").exists())
        self.assertNotIn("merge", self.git("worktree", "list").stdout)

    def test_two_merges_are_done_one_at_a_time_in_the_order_they_were_asked(self) -> None:
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.slice_branch("BIL-01", "billing.txt", "billing\n")
        # Distinct instants, because that is what orders them: a timestamp is to the second, so two asked
        # inside one second are in whatever order the logs are read, and either is a correct answer to
        # "the order they were asked".
        self.ask("ORD-01", t="2026-10-08T09:00:00Z")
        self.ask("BIL-01", fairway="BIL", t="2026-10-08T09:00:01Z")
        self.run_once()
        answers = [e for e in self.harbour() if e.kind in ("granted", "refused")]
        self.assertEqual([e.fields.get("slice") for e in answers], ["ORD-01", "BIL-01"])
        self.assertEqual(self.git("show", "main:ordering.txt").stdout, "ordering\n")
        self.assertEqual(self.git("show", "main:billing.txt").stdout, "billing\n")

    def test_a_merge_answer_says_where_its_time_went(self) -> None:
        """Integration looked slow and nothing could say whether it was the queue, the merge ref or the gate.
        Each answer now carries the three, in whole seconds, and which attempt it was."""
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.ask("ORD-01", t="2026-10-08T09:00:00Z")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "granted", answer.fields)
        self.assertGreater(answer.fields["waited_s"], 0, "asked well before this pass took it up")
        for spent in ("lock_s", "gate_s"):
            self.assertIsInstance(answer.fields[spent], int)
            self.assertGreaterEqual(answer.fields[spent], 0)
        self.assertEqual(answer.fields["attempt"], 1)

    def test_asking_again_under_a_new_id_is_counted_as_the_next_attempt(self) -> None:
        """A captain asks again as `merge-<slice>-<n>`, so the attempt is counted from the answers the slice
        has had, not from the id — and a refusal that never reached the gate has no `gate_s` to report."""
        self.ask("ORD-01")
        self.run_once()
        refused = self.answer()
        self.assertEqual(refused.kind, "refused")
        self.assertEqual(refused.fields["attempt"], 1)
        self.assertNotIn("gate_s", refused.fields)
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.deck("ordering", "ORD", logs.entry(
            "request", fairway="ORD", id="merge-ORD-01-1", what="merge", slice="ORD-01",
            detail="merge slice/ORD-01 into trunk after the full gate"))
        self.run_once()
        granted = [e for e in self.harbour() if e.kind == "granted"]
        self.assertEqual(len(granted), 1, [e.fields for e in self.harbour()])
        self.assertEqual(granted[0].fields["attempt"], 2)

    def test_a_merge_request_that_names_no_slice_is_refused_rather_than_guessed_at(self) -> None:
        self.deck("ordering", "ORD", logs.entry(
            "request", fairway="ORD", id="please", what="merge", detail="merge it"))
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused")
        self.assertIn("which slice", str(answer.fields["why"]))

    def test_uncommitted_changes_the_merge_does_not_touch_are_fast_forwarded_around(self) -> None:
        """A person's edit on trunk is not a reason to stop a run: the voyage that parked behind an
        uncommitted `AGENTS.md` had a slice that touched nothing of it."""
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.git("checkout", "--quiet", "main")
        (self.root / "service.txt").write_text("edited and not committed\n", encoding="utf-8")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "granted")
        self.assertEqual(self.head("main"), answer.fields["commit"])
        self.assertNotIn("note", answer.fields)
        self.assertTrue((self.root / "ordering.txt").is_file())
        self.assertEqual((self.root / "service.txt").read_text(encoding="utf-8"), "edited and not committed\n")
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD").stdout.strip(), "main")

    def test_uncommitted_changes_the_merge_would_overwrite_are_left_where_they_are(self) -> None:
        """Where the fast-forward would overwrite them, the checkout is detached with them untouched and
        trunk moves on regardless; the granted line says so, because that is where a person looks."""
        self.slice_branch("ORD-01", "service.txt", "the slice's version\n")
        self.git("checkout", "--quiet", "main")
        (self.root / "service.txt").write_text("edited and not committed\n", encoding="utf-8")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "granted")
        self.assertEqual(self.head("main"), answer.fields["commit"])
        self.assertIn("detached", str(answer.fields["note"]))
        self.assertEqual((self.root / "service.txt").read_text(encoding="utf-8"), "edited and not committed\n")
        self.assertEqual(self.head(), self.trunk_was)

    def test_a_clean_checkout_sitting_on_trunk_is_fast_forwarded_with_its_working_tree(self) -> None:
        self.slice_branch("ORD-01", "ordering.txt", "ordering\n")
        self.git("checkout", "--quiet", "main")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted")
        self.assertTrue((self.root / "ordering.txt").is_file(),
                        "the working tree moved with the ref, rather than being left behind it")


class SerialisedTest(MergeFixture):
    """One merge at a time across every machine, and the one that loses queues.

    The harbour log became one file per machine so the single writer could be removed rather than elected,
    and the plan named the cost when it guessed that: the merge is the one thing that genuinely needs a
    decider. Two harbourmasters rebasing onto one trunk at once is two gates each measured against a trunk
    the other is about to move. So it is serialised by `refs/slipwai/merge`, taken and released exactly the
    way a claim on a fairway is — no election, no failover, nothing of ours running.
    """

    def setUp(self) -> None:
        super().setUp()
        # Seconds rather than the hour a real harbour allows: this case is about the refusal when the wait
        # runs out, and the wait running out is the thing being tested rather than something to sit through.
        (self.root / "harbour.json").write_text(json.dumps({"trunk": "main", "wait_bound": 0.02}),
                                                encoding="utf-8")

    def hold_the_merge(self, machine: str, since: str = "") -> None:
        """Take the merge ref as another machine would, renewed at `since` where one is given.

        The ref has a lease of half the wait, so a hold taken now would lapse inside this suite's wait of
        a second and be taken over — which is right for a dead holder and wrong for this case, which is
        about a live one. A `since` ahead of now is a holder that has only just renewed, as a live one
        keeps doing while its gate runs.
        """
        dated = {"GIT_AUTHOR_DATE": since} if since else {}
        done = subprocess.run([sys.executable, str(self.root / "scripts/agents/claims.py"),
                               "--take", "refs/slipwai/merge"], cwd=self.root, capture_output=True,
                              text=True, env={**os.environ, "SLIPWAI_MACHINE": machine, **dated})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_machine_that_loses_the_race_waits_and_then_says_who_has_it(self) -> None:
        ahead = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.hold_the_merge("harbour_two", since=ahead)
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        answer = self.answer()
        self.assertEqual(answer.kind, "refused", answer.fields)
        self.assertIn("harbour_two", str(answer.fields["why"]))
        self.assertEqual(self.head("main"), self.trunk_was, "trunk moved while another machine held it")

    def test_the_merge_ref_is_given_back_so_the_next_machine_gets_it(self) -> None:
        """Held for the rebase and the gate and no longer, or the first merge of a run would be the last."""
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted")
        self.hold_the_merge("harbour_two")

    def test_nobody_else_holding_it_merges_as_before(self) -> None:
        self.slice_branch("ORD-01", "service.txt", "one\ntwo\n")
        self.ask("ORD-01")
        self.run_once()
        self.assertEqual(self.answer().kind, "granted")
        self.assertNotEqual(self.head("main"), self.trunk_was)


if __name__ == "__main__":
    unittest.main()
