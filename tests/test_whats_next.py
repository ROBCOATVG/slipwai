"""`/whats-next` says the one next step; `/where-are-we` draws the board. Both read the same artifacts."""
from __future__ import annotations

import tempfile

from support import FactoryTestCase

from slipwai.catalog import CATALOG


class WhatsNextTest(FactoryTestCase):
    def test_whats_next_names_one_slice_one_stage_one_command_from_the_boards_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for profile in CATALOG["profiles"]:
                repo = self.generate(directory, f"next-{profile}", profile, "python")
                command = (repo / "commands/whats-next.md").read_text()
                board = (repo / "commands/where-are-we.md").read_text()
                self.assertRegex(command, r"^---\ndescription: .+\nargument-hint: .+\n---\n")
                for label in ("**Next:**", "**Stage:**", "**Because:**", "**Run:**"):
                    self.assertIn(label, command)
                self.assertIn("at most six lines", command)
                self.assertIn("`/drive <id>`", command)
                self.assertIn("and N more ready in parallel", command)
                self.assertIn("**Blocked:**", command)
                self.assertIn("Runs nothing", command)
                # The same sources as the board, so the two cannot disagree about what is next.
                self.assertIn("`git ls-remote --heads origin 'slice/*'`", command)
                self.assertEqual("`/example-map <id>`" in command, profile == "event-modelling")
                self.assertIn("`/whats-next` reads the same artifacts", board)
                listed = (repo / "docs/skills-and-commands.md").read_text()
                self.assertIn("- `/where-are-we` — `commands/where-are-we.md`\n"
                              "- `/whats-next` — `commands/whats-next.md`", listed)
