"""The generated workflow commands: what each slice is required to pass through, and what it may skip."""
from __future__ import annotations

import re
import tempfile

from support import FactoryTestCase

from slipwai.catalog import CATALOG


class CommandsTest(FactoryTestCase):
    def test_the_expensive_pass_is_triggered_by_surface_and_recorded_either_way(self) -> None:
        """An adversarial pass per slice is a cost no gate asks for — `check-constitution.py` names the
        skill as a practice and never asserts a pass happened, and the skill itself calls it an end-of-phase
        pass that nothing in CI should assert. So the trigger is what the diff did to the attack surface, and
        the decision is only trustworthy if the skip has to cite something durable."""
        for profile in ("event-modelling", "standard"):
            with tempfile.TemporaryDirectory() as directory:
                repo = self.generate(directory, "surface-trigger", profile, "go")
                adversary = (repo / "commands/adversary.md").read_text()
                # The pass is scoped to the diff rather than to the whole slice, and a category the
                # surface cannot express is not a hole in it.
                self.assertIn("bounded to the", adversary)
                self.assertIn("driving adapter", adversary)
                self.assertIn("authorisation decision", adversary)
                # The log is the evidence a later slice declines on. A skip that writes nothing leaves the
                # next ready slice with the same judgement call and no record of this one.
                self.assertGreaterEqual(adversary.count("adversary-log.md"), 2)
                self.assertIn("no findings", adversary)
                self.assertIn("--full", adversary)
                self.assertIn("closes a feature's split", adversary)
                self.assertIn("one adversary per widened seam", adversary)
                self.assertIn("explicit file manifest", adversary)
                self.assertIn("docs/delegated-agent-safety.md", adversary)
                self.assertIn("set every delegate's model explicitly through the harness", adversary)
                self.assertIn("before writing any fix", adversary)
                self.assertIn("trigger table", adversary)
                self.assertIn("widened", adversary)
                self.assertIn("already covered", adversary)
                self.assertIn("An hour of agent attack on one slice is generous", adversary)
                self.assertIn("seams=N", adversary)
                guidance = (repo / "AGENTS.md").read_text()
                self.assertIn("## Delegated agents", guidance)
                self.assertTrue((repo / "docs/delegated-agent-safety.md").is_file())
                drive = (repo / "commands/drive.md").read_text()
                self.assertIn("Prefer a fresh\nsub-agent", drive)
                # The manifest is still what a delegate gets — it moved from a sentence about implementation
                # to the one rule for every type, now that the role itself lives in `agents/`.
                self.assertIn("the call adds only the task, its contract and\nthe file manifest", drive)
                self.assertIn("`drive-implement`", drive)
                self.assertIn("report once when the batch completes", drive)
                self.assertIn("Do not re-investigate", drive)
                self.assertIn("concurrent `drive-adversary` siblings", drive)
                self.assertIn("`seams=N`", drive)
                self.assertIn("owns the\ntrigger table", drive)
                # Only the event profile has schemas and streams to attack.
                self.assertEqual("stream identity" in adversary, profile == "event-modelling")
                # Mutation stays per-slice, and the order between them is not arbitrary: the pass adds
                # tests, and mutation measures whatever exists when it runs.
                for path in ("AGENTS.md", "docs/workflow.md"):
                    body = (repo / path).read_text()
                    self.assertIn("/mutation", body)
                    self.assertIn("changed attack surface", body.replace(chr(10), " "))

    def test_every_slice_gets_both_gaps_passes_and_a_convergence_stage(self) -> None:
        """Two different questions, each with the skill that owns it: is the artifact complete before it is
        planned, and is the promise reachable once it is built. The second runs after Spec Kit's converge
        reports converged — ahead of that verdict an unbuilt task reads as a gap and buries the findings
        that need judgement."""
        for profile in ("event-modelling", "standard"):
            with tempfile.TemporaryDirectory() as directory:
                repo = self.generate(directory, "two-gaps", profile, "python")
                gaps = (repo / "commands/gaps.md").read_text()
                self.assertIn("skills/find-gaps/SKILL.md", gaps)
                self.assertIn("skills/acceptance-review/SKILL.md", gaps)
                for skill in ("find-gaps", "acceptance-review"):
                    self.assertTrue((repo / f"skills/{skill}/SKILL.md").is_file())
                self.assertIn("reports converged, never before it", gaps)

                drive = (repo / "commands/drive.md").read_text()
                # Both passes are in the ladder the resumable entry point walks, and the pre-plan one is
                # above plan and tasks rather than after them.
                self.assertLess(drive.index("**Slice gaps**"), drive.index("**Plan and tasks**"))
                self.assertLess(drive.index("**Implementation**"), drive.index("**Convergence**"))
                self.assertLess(drive.index("**Convergence**"), drive.index("**Demo**"))
                # A read-only pass leaves no artifact, so the stage that can be resumed is the one that
                # records a verdict. An install without the command is a stated skip, not a stop.
                self.assertIn("converged verdict for the current commit", drive)
                self.assertIn("no converge command is a skip", drive)
                self.assertIn(
                    "examples.md" if profile == "event-modelling" else "spec.md",
                    drive.split("**Slice gaps**")[1].split("**Plan and tasks**")[0],
                )
                # The demo stop says what it has to contain, because "stop for feedback" alone is
                # satisfiable by a status report — which hands the actor nothing to use and asks nothing.
                # A pause is only distinguishable from a halt by the question at the end of it.
                self.assertIn("the literal command or URL that runs it", drive)
                self.assertIn("asks directly what using it revealed", drive)
                self.assertIn("has not paused for feedback", drive)
                # And a cleared Phase 4 continues rather than waiting to be invoked again: the README
                # already promises the next ready slice starts without another invocation, so drive.md has to
                # be the instruction that does it.
                self.assertIn("continue on the same run", drive)
                self.assertIn("select the next slice from the **ready** set", drive)
                self.assertIn("Ready-set selection", drive)
                self.assertIn("name the full", drive)
                self.assertIn("ready set", drive)
                self.assertIn("having finished is not one of them", drive)

                # The generated diagram is the thing people read first; a loop it does not draw is a loop
                # nobody runs.
                workflow = (repo / "docs/workflow.md").read_text()
                self.assertIn('CV{"/speckit-converge', workflow)
                self.assertIn('CV -->|"appends tasks"| I', workflow)
                self.assertIn('CV -->|"converged"| DG --> D', workflow)
                self.assertIn('D -->|"accepted · new attack surface"| A --> M', workflow)
                self.assertIn('D -->|"accepted · surface already in the log"| M', workflow)
                entry = "EM --> EG" if profile == "event-modelling" else "SG --> P"
                self.assertIn(entry, workflow)
                # Every node the loop's edges name has to be declared, or Mermaid draws a stray box.
                for node in re.findall(r"^\s+([A-Z]{1,3}) -->", workflow, re.MULTILINE):
                    self.assertTrue(
                        re.search(rf"^\s+{node}[\[{{]", workflow, re.MULTILINE),
                        f"{node} is used but never declared",
                    )

    def test_a_converge_finding_closes_the_class_and_the_verdict_records_the_sweep(self) -> None:
        """Six converge passes on one slice, nineteen appended tasks, and about seven of them the sibling
        of the pass before: `characterOutcome` validated at a parser and then `result` in the same
        function, one screen of a pair and then its neighbour, one array cap in a decoder and then the
        other two. Each fix was correct and each was written as the example it was found at, so the next
        pass found the next instance — the same work at six times the price. The template now asks the
        appended task's GREEN to name the sweep and the verdict to record what the sweep found."""
        with tempfile.TemporaryDirectory() as directory:
            drive = (self.generate(directory, "sweeping", "event-modelling", "python")
                     / "commands/drive.md").read_text()
            stage = drive.split("**Convergence**")[1].split("**Demo**")[0]

            self.assertIn("closes the class, not the instance it was found at", stage)
            self.assertIn("the task's GREEN names the sweep rather than the example", stage)
            self.assertIn("the\n   verdict records the sweep that was performed", stage)
            # A sweep larger than the slice is a scope decision, said out loud — not a reason to leave the
            # siblings to be rediscovered one pass at a time.
            self.assertIn("leave a task naming the\n   rest", stage)

    def test_the_demo_stop_requires_the_process_to_outlive_the_turn(self) -> None:
        """A demo whose server is already stopped is a test somebody ran alone.

        This happened: the agent started `make dev` and `make dev-web`, curled the flow itself, killed both,
        and handed back a demo stop naming the address. The actor opened it and found nothing running — the
        thing they were told to open had been torn down by the turn that told them.

        Both documents that shape a demo stop have to say so. `commands/drive.md` sets the shape, and
        `skills/run-the-app/SKILL.md` is where the concrete command lives, so an agent reading only the one
        it needs still reads it.
        """
        with tempfile.TemporaryDirectory() as directory:
            for profile in CATALOG["profiles"]:
                repo = self.generate(directory, f"alive-{profile}", profile, "typescript", "react-vite")

                drive = (repo / "commands/drive.md").read_text()
                stop = drive.split("### What the demo stop has to contain")[1].split("###")[0]
                self.assertIn("long-lived process", stop)
                self.assertIn("leave it running past the end of the turn", stop)
                self.assertIn("in the background", stop)

                skill = (repo / "skills/run-the-app/SKILL.md").read_text()
                handover = skill.split("## What to hand over")[1]
                self.assertIn("still be running when the turn ends", handover)
                # Naming the project's own command, not "a dev server": this skill exists to be pasted from.
                self.assertIn("`make dev`", handover)

    def test_a_slice_with_a_screen_styles_it_and_an_unstyled_screen_is_not_demonstrated(self) -> None:
        """First slices kept arriving at the demo on browser defaults, and a demo must never show a
        completely unstyled page: the actor has been asked whether the thing works, and Times New Roman on
        white answers a different question before they have used it. So styling is one of the slice's own
        tasks rather than a follow-on, it has a place to come from — `docs/design.md`, the design notes in
        the constitution or under `specs/`, or the baseline in `apps/web` extended — and the demo stop
        checks it like it checks a process that outlives the turn.

        Only where there is a browser surface: a service-only project has no screen to style, and a check
        nothing can fail is a paragraph that teaches the reader to skim the rest."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "styled", "event-modelling", "typescript", "react-vite")
            drive = (repo / "commands/drive.md").read_text()

            implementation = drive.split("**Implementation**")[1].split("**Convergence**")[0]
            self.assertIn("A screen this slice\n   adds or changes is styled as part of it", implementation)
            self.assertIn("`docs/design.md`", implementation)
            self.assertIn("the design\n   notes in the constitution or under `specs/`", implementation)
            self.assertIn("extend\n   the baseline stylesheet and design tokens in `apps/web`", implementation)
            tasks = drive.split("**Plan and tasks**")[1].split("**Implementation**")[0]
            self.assertIn("its styling is one of the tasks written here rather\n   than a follow-on", tasks)

            stop = drive.split("### What the demo stop has to contain")[1].split("###")[0]
            self.assertIn("check every screen this slice adds or changes is styled", stop)
            self.assertIn("A screen still on browser defaults is a reason not to demo yet", stop)
            self.assertIn("Record the check with the\nothers", stop)

            bare = (self.generate(directory, "unstyled", "event-modelling", "typescript")
                    / "commands/drive.md").read_text()
            self.assertNotIn("browser defaults", bare)
            self.assertNotIn("docs/design.md", bare)

    def test_the_demo_stop_opens_with_a_progress_board_counted_in_slices(self) -> None:
        """A product owner had to ask how many slices and tasks there were.

        Their report on a generated project: the process protected quality well, and its weakness was that it
        never showed what was usable, what done meant, or how much remained — and fifty-eight tasks over two
        slices read as fifty-eight features. The stop already had to name the command, the seed, the result
        and the stubs; nothing told it to say where the product stands. So the stop opens with a board, in
        the actor's words, marked so it reads at a glance, counted in slices and never in tasks, and derived
        from artifacts the way the entry stage is — in both profiles, and in both places a demo stop is shaped.
        """
        with tempfile.TemporaryDirectory() as directory:
            for profile in CATALOG["profiles"]:
                repo = self.generate(directory, f"board-{profile}", profile, "typescript", "react-vite")
                drive = (repo / "commands/drive.md").read_text()
                stop = drive.split("### What the demo stop has to contain")[1].split("###")[0]

                self.assertIn("It opens with the progress board", stop)
                # The board comes before the command to paste: the actor reads where they are, then acts.
                self.assertLess(stop.index("progress board"), stop.index("the literal command or URL"))
                for marker, part in (
                    ("✅", "Works now"),
                    ("🆕", "New in this demo"),
                    ("⬜", "Still to come"),
                    ("⚠️", "Not working yet"),
                    ("🔀", "Ready (parallel)"),
                    ("➡️", "Next (this session)"),
                    ("⛔", "Blocked"),
                ):
                    self.assertIn(f"{marker} **{part}**", stop)
                # The count that answers the question the owner had to ask, and the one that alarmed them.
                self.assertIn("`N of M slices accepted`", stop)
                self.assertIn("The task count is not on it", stop)
                # Read off disk, like the entry stage, so a resumed session shows the same board.
                self.assertIn("derived from artifacts, not memory", stop)
                self.assertIn("which are the claims", stop)
                self.assertIn(
                    "`implemented` is done" if profile == "event-modelling" else "a row\nmarks a slice accepted",
                    stop,
                )
                if profile == "event-modelling":
                    self.assertIn("`status` in `docs/event-model/model.yaml`", stop)
                else:
                    self.assertNotIn("model.yaml", stop)

                handover = (repo / "skills/run-the-app/SKILL.md").read_text().split("## What to hand over")[1]
                self.assertIn("opens with the progress\nboard", handover)
                self.assertIn("✅ what works now", handover)

    def test_a_project_with_nothing_long_lived_to_start_makes_no_such_promise(self) -> None:
        """The reminder belongs where there is a process. A project with none has a different problem."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "nothing-alive", language="go", frontend="none",
                event_store="memory", http="none", auth="none",
            )
            skill = (repo / "skills/run-the-app/SKILL.md").read_text()
            self.assertNotIn("still be running when the turn ends", skill)
            self.assertIn("nothing to start", skill)

    def test_where_are_we_draws_the_demo_stop_board_on_demand_and_changes_nothing(self) -> None:
        """The board answered the owner's question at the demo stop; the question does not wait for one.

        So every project carries `/where-are-we`: the same board, read off the same artifacts, at any point on
        the ladder. One line differs — between demos there is nothing new to show and something half-built to
        report — and the rest is what it refuses to do: run a stage, count tasks, invent a slice, or demo.
        """
        with tempfile.TemporaryDirectory() as directory:
            for profile in CATALOG["profiles"]:
                repo = self.generate(directory, f"where-{profile}", profile, "typescript", "react-vite")
                command = (repo / "commands/where-are-we.md").read_text()
                stop = (repo / "commands/drive.md").read_text().split("### What the demo stop has to contain")[1]

                self.assertRegex(command, r"^---\ndescription: .+\nargument-hint: .+\n---\n")
                # The same board as the demo stop, in the same order, save the one line a demo owns.
                shared = (
                    ("✅", "Works now"),
                    ("⬜", "Still to come"),
                    ("⚠️", "Not working yet"),
                    ("🔀", "Ready (parallel)"),
                    ("➡️", "Next (this session)"),
                    ("⛔", "Blocked"),
                )
                for marker, part in shared:
                    self.assertIn(f"{marker} **{part}**", command)
                    self.assertIn(f"{marker} **{part}**", stop)
                self.assertIn("🔧 **In progress**", command)
                self.assertNotIn("New in this demo**", command)
                self.assertLess(command.index("Works now"), command.index("In progress"))
                self.assertLess(command.index("In progress"), command.index("Still to come"))
                self.assertIn("`N of M slices accepted`", command)
                # Read off disk, from exactly the artifacts the demo stop names, so the two cannot disagree.
                self.assertIn("derived from artifacts, not memory", command)
                self.assertIn("which are the claims", command)
                self.assertIn("`plan.md` under `slices/<id>/`", command)
                if profile == "event-modelling":
                    self.assertIn("`status` in `docs/event-model/model.yaml`", command)
                    self.assertIn("event model, split", command)
                else:
                    self.assertNotIn("model.yaml", command)
                    self.assertIn("`.specify/feature.json`", command)
                # What it refuses to do: the demo stop's job stays the demo stop's.
                self.assertIn("**Runs nothing.**", command)
                self.assertIn("**Counts slices, never tasks.**", command)
                self.assertIn("**Invents nothing.**", command)
                self.assertIn("**Does not demo.**", command)
                # Under `--target none` there is no flags file to read constraints from.
                self.assertNotIn("flags.auto.tfvars", command)
                # Listed right after the command whose stop it borrows from, and the stop points back at it.
                listed = (repo / "docs/skills-and-commands.md").read_text()
                pair = "- `/drive` — `commands/drive.md`\n- `/where-are-we` — `commands/where-are-we.md`"
                self.assertIn(pair, listed)
                self.assertIn("`/where-are-we`\ndraws the same board on demand", stop)
                started = (repo / "docs/getting-started.md").read_text()
                self.assertIn("`/where-are-we` for the progress board at any point", started)

    def test_where_are_we_reads_release_constraints_off_the_flags_file_under_a_managed_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "where-flagged", "standard", "typescript", "none", target="aws")
            self.assertIn("`infra/service/flags.auto.tfvars`", (repo / "commands/where-are-we.md").read_text())
