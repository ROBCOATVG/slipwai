"""One `/drive` session runs every ready slice at once, once the contract is settled.

The method promised the parallelism — slices sharing only an event schema are independent — and `/drive`
exploited it only by being run twice. Three primitives make one session able to do it, read from the
reference implementations: a claim, a written shared-surface rule held by a gate, and one slice per delegate.
The tests here read the generated command for the rules and run the gate against a real repository, on a
slice branch and off one.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from support import NO_MAINTENANCE, FactoryTestCase, commit_all

from slipwai.catalog import CATALOG

MODEL = """\
schemaVersion: 1
slices:
  - id: S1
    name: Place an order
    pattern: state-change
    status: planned
    actor: Customer
    service: service
    stream: order-{orderId}
    gwt: specs/001-ordering/slices/S1/examples.md
    frames:
      - { type: cmd, name: PlaceOrder, data: "orderId" }
      - { type: evt, name: OrderPlaced, data: "orderId" }
  - id: S2
    name: See an order
    pattern: state-view
    status: planned
    actor: Customer
    service: service
    reads: [OrderPlaced]
    materialisation: live
    frames:
      - { type: rmo, name: OrderSummary, data: "orderId" }
"""


def git(repo: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@local", *NO_MAINTENANCE, *arguments],
        cwd=repo, text=True, capture_output=True, check=True,
    )


class DriveFansOutTest(FactoryTestCase):
    def test_drive_runs_ready_slices_concurrently_once_the_contract_is_settled(self) -> None:
        """The ready-set rules end in a fan-out, not in "name the rest for another session": claim by branch,
        one delegate per slice in its own worktree, the shared-surface rule, merges in split order, one demo
        per slice. The contract precondition is the profile's — `planned` where there is a model."""
        with tempfile.TemporaryDirectory() as directory:
            for profile in CATALOG["profiles"]:
                repo = self.generate(directory, f"fan-{profile}", profile, "typescript")
                drive = (repo / "commands/drive.md").read_text()
                event = profile == "event-modelling"

                rules = drive.split("**Ready-set selection**")[1].split("### Running ready slices concurrently")[0]
                section = drive.split("### Running ready slices concurrently")[1].split("The stops are")[0]
                self.assertLess(drive.index("**Ready-set selection**"), drive.index("### Running ready slices"))
                # Done is a mark, not a location: the record sits under slices/<id>/ from the day it is planned.
                self.assertIn("A slice with `plan.md` under `slices/<id>/` and no such mark is in\n   flight", rules)
                self.assertIn(
                    "`status: implemented` in `docs/event-model/model.yaml`" if event
                    else "a row in the register at `specs/<feature>/slices/README.md`",
                    rules,
                )
                self.assertIn("**ready** = not done, every `depends_on` done", rules)
                self.assertIn("split into *claimed* and *unclaimed*", rules)
                self.assertIn("run every unclaimed one whose contract is settled concurrently", rules)
                # The four primitives, in the order a driver applies them.
                self.assertIn(
                    "`status` in\n`model.yaml` is `planned`" if event else "`specs/<feature>/contracts/` exist",
                    section,
                )
                self.assertIn(
                    "git push --force-with-lease=refs/heads/slice/<id>: origin HEAD:refs/heads/slice/<id>", section,
                )
                self.assertIn("Rejected means another session got there first", section)
                self.assertIn("reported as\nstale, never silently taken", section)
                self.assertIn("one fresh `drive-slice` delegate", section)
                self.assertIn("with a manifest naming the worktree", section)
                self.assertIn("Inside one slice the stages stay strictly sequential", section)
                self.assertIn("`make check-slice-scope` holds on\nevery `slice/<id>` branch", section)
                self.assertIn("The canonical slot at the feature root is a link, never committed", section)
                self.assertIn("in split order — never in finishing order", section)
                self.assertIn("Demo on the slice branch, then verify, then push", section)
                self.assertIn("unpushed worktree", section)
                self.assertIn("a sibling's demo never waits on another's Phase 4", section)
                self.assertIn("**Where the harness cannot delegate**", section)
                for primitive in ("**The contract is settled.**", "**Each slice is claimed.**",
                                  "**Each slice has its own worktree and one delegate.**",
                                  "**The shared-surface rule**",
                                  "**Demo on the slice branch, then verify, then push.**"):
                    self.assertIn(primitive, section)
                order = [section.index(primitive) for primitive in (
                    "**The contract is settled.**", "**Each slice is claimed.**", "**The shared-surface rule**",
                    "**Demo on the slice branch, then verify, then push.**",
                )]
                self.assertEqual(order, sorted(order))

                # The plan stage links the canonical slot before the Spec Kit commands write, and Phase 4
                # marks rather than moves.
                plan = drive.split("**Plan and tasks**")[1].split("**Implementation**")[0]
                self.assertIn("`ln -sfn slices/<id>/<name> specs/<feature>/<name>`", plan)
                self.assertIn("a regular file where a link was is a harness that\n   replaced the link", plan)
                self.assertIn("mark the finished slice done", drive)
                self.assertNotIn("archive the finished slice", drive)
                # What the summary tests still hold, kept: the loop continues and the ready set is named.
                self.assertIn("select the next slice from the **ready** set", drive)
                self.assertIn("having finished is not one of them", drive)

                # The board splits the ready line, in both commands.
                for command in ("drive.md", "where-are-we.md"):
                    text = (repo / "commands" / command).read_text()
                    self.assertIn("in two groups, *claimed*", text)
                    self.assertIn("every unclaimed ready slice whose\n  contract is settled, concurrently", text)

                # The gate ships, runs in verify, and the links stay out of the history.
                makefile = (repo / "Makefile").read_text()
                self.assertIn("check-slice-scope: ## Fail when a slice/<id> branch touches", makefile)
                self.assertRegex(makefile, r"verify: [^\n]*\bcheck-slice-scope\b")
                self.assertRegex(makefile, r"\.PHONY: [^\n]*\bcheck-slice-scope\b")
                gate = repo / "scripts/check-slice-scope.py"
                self.assertTrue(gate.is_file())
                self.assertTrue(os.access(gate, os.X_OK))
                ignore = (repo / ".gitignore").read_text()
                for slot in ("plan.md", "research.md", "data-model.md", "quickstart.md", "tasks.md"):
                    self.assertIn(f"specs/*/{slot}\n", ignore)
                # And the prose a reader meets first says the same thing.
                self.assertIn("`make check-slice-scope` holds every `slice/<id>` branch to",
                              (repo / "docs/architecture.md").read_text())
                if event:
                    first = (repo / "docs/first-slice.md").read_text()
                    self.assertIn("Finishing a slice marks it done rather than moving it", first)
                    self.assertIn("never committed", first)
                split = (repo / "skills/story-splitting/SKILL.md").read_text()
                self.assertIn("one delegate per slice on a `slice/<id>` branch", split)
                self.assertNotIn("one `/drive` session still takes one\nslice at a time", split)
                if event:
                    reference = (repo / "docs/event-model/README.md").read_text()
                    self.assertIn("Ready is necessary for running alongside a sibling, not sufficient", reference)


class SliceScopeGateTest(FactoryTestCase):
    def check(self, repo: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", "scripts/check-slice-scope.py"], cwd=repo, text=True, capture_output=True,
            env={**os.environ, "GITHUB_HEAD_REF": "", "CI_COMMIT_REF_NAME": ""},
        )

    def test_the_gate_holds_a_slice_branch_to_what_one_slice_may_touch(self) -> None:
        """Off a slice branch there is nothing to hold — except a regular file where a canonical link should
        be. On one, its own record and code pass; another slice's record or model block, a numbered or edited
        migration, a removed line in the events module and a file outside every deployable are refused, each
        with what to do instead."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "scope", "event-modelling", "typescript", event_store="postgres")
            (repo / "docs/event-model/model.yaml").write_text(MODEL)
            feature = repo / "specs/001-ordering"
            (feature / "slices/S1").mkdir(parents=True)
            (feature / "slices/S1/examples.md").write_text("# S1\n")
            (feature / "spec.md").write_text("# Ordering\n")
            events = repo / "apps/service/src/domain/ordering/events.ts"
            events.parent.mkdir(parents=True)
            events.write_text("export const OrderPlaced = 'OrderPlaced';\nexport const OrderPaid = 'OrderPaid';\n")
            commit_all(repo, "generated")

            # Off a slice branch: nothing to hold, and the gate says so rather than pretending to check.
            result = self.check(repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("on `main`, not a `slice/<id>` branch", result.stdout)
            # ...except the one thing that is wrong on every branch: a record the ignore rule is about to hide.
            (feature / "plan.md").write_text("# a plan the harness wrote as a file\n")
            result = self.check(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("specs/001-ordering/plan.md: a regular file at the canonical slot", result.stderr)
            (feature / "plan.md").unlink()
            (feature / "plan.md").symlink_to("slices/S1/plan.md")
            self.assertEqual(self.check(repo).returncode, 0)

            git(repo, "checkout", "-q", "-b", "slice/S1")
            result = self.check(repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("slice/S1 touches only what one slice may", result.stdout)

            # Its own record, its own service's code, a new stamped migration, an added event: allowed.
            (feature / "slices/S1/plan.md").write_text("# Plan\n")
            (feature / "spec.md").write_text("# Ordering\n\nAmended by S1.\n")
            decider = repo / "apps/service/src/domain/ordering/decider.ts"
            decider.write_text("export const decide = () => [];\n")
            migrations = repo / "apps/service/migrations"
            (migrations / "202609151030_orders.sql").write_text("CREATE TABLE orders (id text);\n")
            events.write_text(events.read_text() + "export const OrderShipped = 'OrderShipped';\n")
            result = self.check(repo)
            self.assertEqual(result.returncode, 0, result.stderr)

            # Each refusal, one at a time, and each says what to do instead.
            def refused(path: str, content: str | None, *expected: str) -> None:
                target = repo / path
                previous = target.read_text() if target.exists() else None
                if content is None:
                    target.unlink()
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content)
                result = self.check(repo)
                self.assertNotEqual(result.returncode, 0, f"{path} was allowed:\n{result.stdout}")
                for text in expected:
                    self.assertIn(text, result.stderr)
                if previous is None:
                    target.unlink()
                else:
                    target.write_text(previous)
                self.assertEqual(self.check(repo).returncode, 0, self.check(repo).stderr)

            refused("specs/001-ordering/slices/S2/plan.md", "# S2\n", "slice `S2`'s record", "question for the host")
            # Ignored, so never in the diff: the working-tree check catches it on this branch as on `main`.
            refused("specs/001-ordering/tasks.md", "- [ ] T001\n", "a regular file at the canonical slot",
                    "link the slot to it")
            refused("apps/service/migrations/005_orders_status.sql",
                    "ALTER TABLE orders ADD COLUMN status text;\n",
                    "a new migration on a slice branch is timestamped", "202609151030_orders_status")
            refused("apps/service/migrations/001_events.js", "// edited\n", "an existing migration was edited",
                    "Add a new, timestamped migration instead")
            refused("Makefile", "all:\n", "outside every deployable", "Land it on `main` before the fan-out")
            refused("docs/event-model/README.md", "# mine\n", "the docs are the host's")
            refused("apps/service/src/domain/ordering/events.ts", "export const OrderPlaced = 'OrderPlaced';\n",
                    "the events module is the contract and grows additively", "a line was removed")
            refused("docs/event-model/model.yaml", MODEL.replace("name: See an order", "name: See an order, renamed"),
                    "slice `S2`'s block changed on `S1`'s branch", "hand the change back to the host")
            refused("docs/event-model/model.yaml", MODEL.split("  - id: S2")[0], "slice `S2` is gone")
            # Its own block may change: S1 advancing is exactly what a slice branch does.
            advanced = MODEL.replace("status: planned\n    actor: Customer\n    service: service\n    stream",
                                     "status: implemented\n    actor: Customer\n    service: service\n    stream")
            self.assertNotEqual(advanced, MODEL)
            (repo / "docs/event-model/model.yaml").write_text(advanced)
            result = self.check(repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            # And the CI shape: a detached checkout with the head ref in the environment is the same branch.
            git(repo, "checkout", "-q", "--detach")
            result = subprocess.run(
                ["python3", "scripts/check-slice-scope.py"], cwd=repo, text=True, capture_output=True,
                env={**os.environ, "GITHUB_HEAD_REF": "slice/S1"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("slice/S1 touches only", result.stdout)

    def test_a_second_context_is_another_slices_code(self) -> None:
        """Where the owning service holds several bounded contexts, a slice writes under its own only."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "contexts", "event-modelling", "typescript")
            manifest = repo / "project.json"
            text = manifest.read_text()
            self.assertIn('"kind": "service"', text)
            text = re.sub(r'("kind": "service",)', r'\1 "contexts": ["ordering", "billing"],', text, count=1)
            manifest.write_text(text)
            (repo / "docs/event-model/model.yaml").write_text(
                MODEL.replace("service: service\n    stream", "service: service\n    context: ordering\n    stream")
            )
            commit_all(repo, "generated")
            git(repo, "checkout", "-q", "-b", "slice/S1")
            own = repo / "apps/service/src/domain/ordering/decider.ts"
            own.parent.mkdir(parents=True)
            own.write_text("export const decide = () => [];\n")
            self.assertEqual(self.check(repo).returncode, 0, self.check(repo).stderr)
            other = repo / "apps/service/src/application/billing/invoice.ts"
            other.parent.mkdir(parents=True)
            other.write_text("export const invoice = () => [];\n")
            result = self.check(repo)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bounded context `billing` is not slice `S1`'s (`context: ordering`)", result.stderr)


class StampedMigrationsTest(FactoryTestCase):
    def test_check_migrations_reads_a_timestamped_contract_the_same_as_a_numbered_one(self) -> None:
        """Every stamp sorts after every shipped number, and a contraction may name a stamped expand."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "stamped", "event-modelling", "typescript", event_store="postgres")
            migrations = repo / "apps/service/migrations"
            expand = migrations / "202609151030_orders_add_status.sql"
            expand.write_text("ALTER TABLE orders ADD COLUMN status text;\n")
            commit_all(repo, "expand")
            (migrations / "202609151031_orders_drop_state.sql").write_text(
                "-- contract: 202609151030_orders_add_status\nALTER TABLE orders DROP COLUMN state;\n"
            )
            result = subprocess.run(
                ["python3", "scripts/check-migrations.py"], cwd=repo, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess("004_event_tags.js", expand.name)
