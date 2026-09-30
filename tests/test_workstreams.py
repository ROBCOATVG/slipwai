"""Slices arranged into workstreams by bounded context, so more than one person or machine delivers at once.

The fan-out gave one session every ready slice; what it did not give was a second runner anything but the
same list, with merges and demos serialised on it. A workstream is one context's slices in split order, held
by one runner at a time, and the tests here read the generated command, board, skill and page for the rules —
where a slice's workstream comes from, per profile; that merges are ordered within one and not across; that a
held workstream is left alone — and run the cruise runner with `--workstream` to see it reach every iteration
and the log.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_cruise_runner import cruise, enable, fake_harness, logged

from slipwai.catalog import CATALOG


class WorkstreamRulesTest(FactoryTestCase):
    def test_drive_arranges_slices_into_workstreams_by_bounded_context(self) -> None:
        """A `### Workstreams` section after the fan-out: what one is, where it is read from — the model's
        `context` on the event profile, the slice graph's column otherwise — who takes one, and that merges are
        ordered within a workstream and not across. The ready-set rules, the board, the skill and the
        architecture page say the same thing."""
        with tempfile.TemporaryDirectory() as directory:
            for profile in CATALOG["profiles"]:
                repo = self.generate(directory, f"ws-{profile}", profile, "typescript")
                drive = (repo / "commands/drive.md").read_text()
                event = profile == "event-modelling"

                self.assertIn("argument-hint: [slice-id-or-feature] [workstream=<name>]", drive)
                self.assertIn("arranged into\n   workstreams by bounded context", drive)
                self.assertLess(drive.index("### Running ready slices concurrently"), drive.index("### Workstreams"))
                self.assertLess(drive.index("### Workstreams"), drive.index("The stops are"))
                section = drive.split("### Workstreams")[1].split("The stops are")[0]
                self.assertIn("one bounded context's slices, in split order, held by one runner at a time", section)
                self.assertIn(
                    "the `context` its block of `docs/event-model/model.yaml` names" if event
                    else "the *Workstream* column of `## Slice graph` in `specs/<feature>/story-split.md`",
                    section,
                )
                self.assertIn("A project with one context has one workstream", section)
                for rule in ("**The split names them.**", "**A session takes one workstream, or every free one.**",
                             "**Merges are ordered within a workstream and not across.**"):
                    self.assertIn(rule, section)
                self.assertIn("never one slice in two workstreams", section)
                self.assertIn("`/drive workstream=<name>`", section)
                self.assertIn("`make cruise WORKSTREAM=<name>`", section)
                self.assertIn("`held_by` is\nrouting, not a lock", section)
                self.assertIn("a conflict there is a contract change: stop both workstreams for the host", section)
                self.assertIn("A workstream's demo never waits on another workstream's demo", section)
                self.assertIn("Phase 4 stays one slice at a time on\n`main`", section)

                # The ready-set rules narrow to a workstream, and leave a held one alone.
                rules = drive.split("**Ready-set selection**")[1].split("### Running ready slices concurrently")[0]
                self.assertIn("grouped by workstream where the split names more\n   than one", rules)
                self.assertIn("7. **A workstream narrows all of the above.**", rules)
                self.assertIn("named as *another workstream's* and left", rules)
                self.assertIn("whose `held_by` names somebody else", rules)
                # The merge rule in the fan-out itself agrees with the section.
                fan_out = drive.split("### Running ready slices concurrently")[1].split("### Workstreams")[0]
                self.assertIn("in split order within its workstream — never in\nfinishing order there", fan_out)
                self.assertIn("across workstreams as each is accepted", fan_out)

                # The board groups by workstream, in both commands, and a held slice is not unclaimed.
                for command in ("drive.md", "where-are-we.md"):
                    text = (repo / "commands" / command).read_text()
                    self.assertIn("⬜, 🔀 and ➡️ are grouped by workstream", text)
                    self.assertIn("is *held*, never *unclaimed*", text)

                # The split writes the column and the table.
                skill = (repo / "skills/story-splitting/SKILL.md").read_text()
                self.assertIn("| Slice | Workstream | depends_on | parallel_ok_with | Notes |", skill)
                self.assertIn("## Workstreams\n| Workstream | Bounded context | Slices (split order) "
                              "| held_by | Notes |", skill)
                self.assertIn("Does every slice sit in exactly one **workstream**", skill)
                self.assertIn("one context is one workstream and needs no\ntable", skill)

                # The page a reader meets first, and the cruise command, carry the same idea.
                self.assertIn("a context is also a **workstream**", (repo / "docs/architecture.md").read_text())
                cruise_command = (repo / "commands/cruise.md").read_text()
                self.assertIn("[--feature <name>] [--workstream <name>]", cruise_command)
                self.assertIn("rides beside the feature as `workstream=<name>` on every iteration", cruise_command)
                self.assertIn("one `drive-gaps` delegate per workstream first", cruise_command)
                self.assertIn("Workstreams widen it further", cruise_command)
                self.assertIn("WORKSTREAM=<name> to take one workstream", (repo / "Makefile").read_text())


class WorkstreamRunnerTest(FactoryTestCase):
    def test_the_runner_carries_the_workstream_on_every_iteration_and_into_the_log(self) -> None:
        """`--workstream billing` reaches every iteration as `workstream=billing`, after the feature where one is
        given, in the spelling `/drive` reads — and each log entry names the workstream, so two runners' logs
        read apart."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "ws-run", "standard", "python")
            enable(repo)
            env = fake_harness(Path(directory), """mkdir -p specs && touch "specs/progress-$n"
if [ "$n" -lt 2 ]; then echo "cruise: continue"; else echo "cruise: done"; fi""")
            run = cruise(repo, "run", "--feature", "001-campaign", "--workstream", "billing", "kick off", env=env)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("each iteration runs `/cruise 001-campaign workstream=billing` in a fresh session",
                          run.stdout)
            self.assertEqual((Path(directory) / "prompts").read_text().splitlines(),
                             ["/cruise 001-campaign workstream=billing kick off",
                              "/cruise 001-campaign workstream=billing"])
            self.assertEqual([entry.get("workstream") for entry in logged(repo)], ["billing", "billing"])

            # A workstream alone, with no feature, is the whole argument; without either, nothing is added.
            (repo / "specs/cruise-log.jsonl").unlink()
            (Path(directory) / "prompts").unlink()
            (Path(directory) / "calls").unlink()
            run = cruise(repo, "run", "--workstream", "fulfilment", env=env)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual((Path(directory) / "prompts").read_text().splitlines(),
                             ["/cruise workstream=fulfilment"] * 2)
            self.assertEqual([entry.get("workstream") for entry in logged(repo)], ["fulfilment", "fulfilment"])
            (repo / "specs/cruise-log.jsonl").unlink()
            (Path(directory) / "prompts").unlink()
            (Path(directory) / "calls").unlink()
            run = cruise(repo, "run", env=env)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual((Path(directory) / "prompts").read_text().splitlines(), ["/cruise"] * 2)
            self.assertNotIn("workstream", logged(repo)[0])
