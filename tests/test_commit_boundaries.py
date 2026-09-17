"""RED-GREEN-REFACTOR stays fast; the full gate protects the slice boundary."""
from __future__ import annotations

import tempfile

from support import FactoryTestCase


class CommitBoundaryTest(FactoryTestCase):
    def test_local_cycles_and_slice_boundaries_have_different_evidence_costs(self) -> None:
        """Each cycle is a local commit; the full gate runs once, immediately before the first push."""
        for profile in ("event-modelling", "standard"):
            with tempfile.TemporaryDirectory() as directory:
                repo = self.generate(directory, f"commit-boundary-{profile}", profile, "python")
                drive = (repo / "commands/drive.md").read_text()
                implement = (repo / "agents/drive-implement.md").read_text()
                tdd = (repo / "skills/tdd/SKILL.md").read_text()
                planning = (repo / "skills/planning/SKILL.md").read_text()
                constitution = (
                    repo / f".specify/presets/{profile}/templates/constitution-template.md"
                ).read_text()
                flat_drive = drive.replace("\n", " ")
                flat_implement = implement.replace("\n", " ")
                flat_constitution = constitution.replace("\n", " ")

                self.assertIn("quickest relevant tests in the same file or area", flat_drive)
                self.assertIn("commit that increment locally", flat_drive)
                self.assertIn("Do not push increment commits", flat_drive)
                self.assertIn("accepted the demo", flat_drive)
                self.assertIn("first push of those increment commits", flat_drive)
                self.assertIn("runs `codegraph sync`", flat_drive)
                self.assertNotIn(
                    "start from a green `make verify`, take one RED-GREEN-REFACTOR increment per task",
                    drive,
                )

                self.assertIn(
                    "quickest relevant test command scoped to the same file or area",
                    flat_implement,
                )
                self.assertIn("Commit the increment locally", flat_implement)
                self.assertIn("do not push", flat_implement)
                self.assertIn("after demo acceptance", flat_implement)
                self.assertNotIn("affected one-shot", flat_implement)
                self.assertNotIn("leave one behind", flat_implement)

                inner_loop = tdd.split("### GREEN:")[1].split("## End-of-Phase")[0]
                self.assertIn("same file or area", inner_loop)
                self.assertNotIn("related/affected", inner_loop)
                self.assertNotIn("focused and affected", inner_loop)
                discipline = planning.split("## Commit Discipline")[1].split("## Plan File")[0]
                self.assertIn("same file or area", discipline)
                self.assertIn("After demo acceptance", discipline)

                self.assertIn("Commit each completed cycle locally", flat_constitution)
                self.assertIn("immediately before that first implementation push", flat_constitution)
                self.assertNotIn("suite MUST be green at every commit boundary", flat_constitution)

                if profile == "event-modelling":
                    root = repo / ".specify/presets/event-modelling/templates"
                    plan = (root / "plan-template.md").read_text()
                    tasks = (root / "tasks-template.md").read_text()
                    for artifact in (plan, tasks):
                        flat_artifact = artifact.replace("\n", " ")
                        self.assertIn("after demo acceptance", flat_artifact)
                        self.assertNotIn("one RED-GREEN-REFACTOR cycle per commit", flat_artifact)
                    self.assertNotIn("current increment is green and committed", tasks)
