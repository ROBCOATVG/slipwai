"""What running the ladder in a generated project taught it, carried back into the text it ships.

Every assertion here is a measured failure: a convergence loop that cost 12.9 times the implementation it
judged, a `/drive` that derived its entry stage from a branch fifty-seven commits behind trunk, a claim lookup
that read an unreachable forge as "every slice unclaimed", two delegates that reached for `git stash` and a
copied-aside backup because the safety page forbade both and named no legal route, and a stopped pass whose
last line became a task and a waiver before anyone re-ran it.
"""
from __future__ import annotations

import tempfile

from support import FactoryTestCase

from slipwai.assets import TOOLKIT_ROOT
from slipwai.project.converge_stage import LEVELS, PASSES


class DriveEvidenceTest(FactoryTestCase):
    def test_convergence_is_bounded_and_a_stopped_pass_leaves_leads_rather_than_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "bounded", "event-modelling", "go")
            drive = (repo / "commands/drive.md").read_text()
            stage = drive.split("**Convergence**")[1].split("**Demo**")[0]
            # The bound, the floor and the level list, all in the rung itself.
            self.assertIn(f"at most {PASSES} passes by default", stage)
            self.assertIn("Only a `CRITICAL` or `HIGH` finding re-opens the loop at all", stage)
            # The bound is a default, and one grade overrides it: a slice never demos carrying a CRITICAL.
            self.assertIn("open `CRITICAL` finding re-opens the loop however many passes have run", stage)
            self.assertIn(", ".join(LEVELS), stage)
            self.assertIn("take what it has found when it reaches it", stage)
            # A pass mutates the tree to prove a finding; a stopped pass leaves the mutation in place.
            self.assertIn("including one that was stopped — the tree is clean before anything else runs", stage)
            self.assertIn("is a lead, not a finding", stage)
            self.assertIn("a stopped pass believed X; verify before acting", stage)
            # The brief the pass runs under asks for the same things from the other side.
            converge = (repo / "agents/drive-converge.md").read_text()
            self.assertIn(", ".join(LEVELS), converge)
            self.assertIn("only a `CRITICAL` re-opens it\npast the ladder's bound", converge)
            self.assertIn("return what you have found marked incomplete", converge)
            self.assertIn("recoverable by construction", converge)
            self.assertIn("or the ladder's bound is reached", converge)
            # And the host treats a stopped delegate's notification as a lead too.
            self.assertIn("everything in its stop notification is a lead, never a result", drive)

    def test_the_entry_stage_checks_the_branch_and_an_unreadable_forge_is_not_an_empty_claim_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for profile in ("event-modelling", "standard"):
                repo = self.generate(directory, f"current-{profile}", profile, "python")
                drive = (repo / "commands/drive.md").read_text()
                entry = drive.split("## Enter at the first incomplete stage")[1].split("\n1. ")[0]
                self.assertIn("check the branch before the artifacts", entry)
                self.assertIn("`git log --oneline HEAD..@{u}`", entry)
                self.assertIn("Behind by anything, stop and say so rather than deriving", entry)
                self.assertIn("*could not verify this checkout is current*", entry)
                # The claim mechanism fails open when the remote is configured and unreachable.
                self.assertIn("*claims could not be read*, never as *unclaimed*", drive)
                for text in (drive, (repo / "commands/where-are-we.md").read_text()):
                    self.assertIn("shows no slice as unclaimed on the strength of a failed read", text)

    def test_a_brief_may_point_and_the_host_reads_manifests_rather_than_waiting_for_a_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            drive = (self.generate(directory, "pointers", "standard", "go") / "commands/drive.md").read_text()
            section = drive.split("## Who runs each stage")[1].split("## What each stage costs")[0]
            self.assertIn("It may give it a map", section)
            self.assertIn("is a pointer and costs a sentence", section)
            self.assertIn("every permission is written into each\nmode that has it", section)
            self.assertIn("a task with no marker whose manifest shares no file with the batch", section)
            self.assertIn("The manifests are the artifact", section)

    def test_a_delegate_has_one_legal_way_to_watch_a_test_fail_and_says_when_it_saw_red(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "teeth", "standard", "typescript")
            implement = (repo / "agents/drive-implement.md").read_text()
            self.assertIn("RED is observed before the code that satisfies it exists", implement)
            self.assertIn("the new test run against the unchanged code", implement)
            self.assertIn("restore that one file with `git checkout -- <exact path>`", implement)
            self.assertIn("Never `git stash`", implement)
            self.assertIn("whether it was observed before the implementation existed", implement)
            safety = (repo / "docs/delegated-agent-safety.md").read_text()
            self.assertIn("`git checkout -- <exact path>`", safety)
            self.assertIn("this is the route", safety)
            self.assertIn("owns leaving it\n  clean on every exit path, including being stopped", safety)
            # A harness reads its agent types once, so the projection says the session has to restart.
            projector = (TOOLKIT_ROOT / "scripts/agents/project.py").read_text()
            self.assertIn("restart the session before", projector)
