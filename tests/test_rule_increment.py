"""The increment is one rule, not one test, and a red build is not a red test.

Measured downstream: the tasks command emitted proof-only tasks — GREEN: none expected — that passed the
moment they were written, which the constitution template called a defect. Both came from here. The fix is
the unit: one rule of the example map with its examples, stubbed first so each example fails for its own
reason. The template, the example-map command, the tasks template and the two briefs have to say the same
thing, which is what this holds.
"""
from __future__ import annotations

import tempfile

from support import FactoryTestCase

from slipwai.assets import PROFILE_ROOT


class RuleIncrementTest(FactoryTestCase):
    def test_both_constitution_templates_make_the_rule_the_unit_and_the_build_not_the_red(self) -> None:
        for profile in ("event-modelling", "standard"):
            preset = PROFILE_ROOT / f"{profile}/.specify/presets/{profile}/templates"
            template = (preset / "constitution-template.md").read_text()
            self.assertIn("The unit of an increment is **one rule**", template)
            self.assertIn("an increment MUST\n  NOT span rules", template)
            self.assertIn("**RED is a failing assertion, not a failing build.**", template)
            self.assertIn("failing for its own stated reason, distinct from its\n  siblings'", template)
            self.assertIn("is a rule cut too small", template)
            # The batch prohibition survives at the level it was aimed at.
            self.assertIn("scenarios up front as a batch and then implementing against them is\n  prohibited", template)
        standard = (PROFILE_ROOT / "standard/.specify/presets/standard/templates/constitution-template.md").read_text()
        self.assertIn("or one acceptance criterion where there is no map", standard)

    def test_the_map_groups_scenarios_under_their_rule_and_the_briefs_cut_and_drive_by_rule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "rules", "event-modelling", "typescript")
            example_map = (repo / "commands/example-map.md").read_text()
            self.assertIn("## Rules own their examples", example_map)
            self.assertIn("`R1`…`Rn`", example_map)
            self.assertIn("Never renumber a rule once a task or a verdict cites it", example_map)
            self.assertIn("Do not retrofit this shape onto a map that is\nalready agreed and implemented", example_map)
            tasks_template = (repo / ".specify/presets/event-modelling/templates/tasks-template.md").read_text()
            self.assertIn("one rule per RED-GREEN-REFACTOR cycle", tasks_template)
            self.assertIn("each citing its `R<n>`", tasks_template)
            self.assertIn("A\ntask whose GREEN would be empty", tasks_template)
            tasks = (repo / "agents/drive-tasks.md").read_text()
            self.assertIn("cut one task per rule and cite it", tasks)
            self.assertIn("A task whose GREEN would be\nempty", tasks)
            self.assertIn("whether or not it adds production code", tasks)
            implement = (repo / "agents/drive-implement.md").read_text()
            self.assertIn("or every rule of one user story", implement)
            self.assertIn("stub whatever an\nexample names", implement)
            # Sub-delegation, and the constraint a harness gets wrong by default.
            self.assertIn("**You may fan your own increment out**", implement)
            self.assertIn("a sub-delegate's manifest is a subset of yours, never wider", implement)
            self.assertIn("nothing you spawn writes `tasks.md`", implement)
            self.assertIn("one cycle's evidence", implement)
            drive = (repo / "commands/drive.md").read_text()
            self.assertIn("one rule of the example map with its examples, where the map numbers its rules", drive)
