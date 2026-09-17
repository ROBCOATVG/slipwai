"""The Choose and Slice stages of adoption: `docs/change-strategy.md`, `/strangle` and the retirement ledger.

Experimental (`AGENTS.md` says what the word means here). What is gated is that an adopted repository —
and only one — gets the essay with its three strategies and its ladder, a command that refuses to move what
nothing has pinned and decides the seam for the target the project has, and a ledger the factory writes once
and never replaces; and that the essay's one layout-dependent path is spelled for the project.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import node_repository, slipwai


class StrangleTest(FactoryTestCase):
    def test_an_adopted_repository_gets_the_strategy_page_the_command_and_the_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = node_repository(Path(directory))
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            page = (repo / "delivery/docs/change-strategy.md").read_text()
            for heading in ("## Three strategies, not two", "## Separate the layers, and do one at a time", "## Data",
                            "## Every step shippable, every step reversible", "## The retirement ledger"):
                self.assertIn(heading, page)
            self.assertIn("**Strangler fig**", page)
            self.assertIn("**Modular monolith in place**", page)
            self.assertIn("**Dual-write is a trap.**", page)
            self.assertIn("OpenRewrite", page)
            self.assertIn("`delivery/retirement.md`", page, "the one layout-dependent path is spelled for this project")
            self.assertNotIn("__DELIVERY__", page)
            self.assertIn("change-strategy.md", (repo / "delivery/docs/README.md").read_text())

            command = (repo / "delivery/commands/strangle.md").read_text()
            self.assertIn("## Refuse what is not ready", command)
            self.assertIn("run `/characterise` for it first", command)
            self.assertIn("`delivery/survey/pinned.md`", command)
            self.assertIn("`delivery/retirement.md`", command)
            self.assertIn("infrastructure the factory does not manage, so the routing seam is one the", command)
            self.assertNotIn("flag transport it already has", command)
            self.assertIn("`/add-service <name> --language <language>", command)
            self.assertIn("`add-service --from <path>`) is not built", command)

            ledger = (repo / "delivery/retirement.md").read_text()
            self.assertIn("| Date | Capability | From | To | Routed by | Pinned by | Status |", ledger)
            written = (repo / "delivery/.written").read_text().splitlines()
            self.assertIn("delivery/commands/strangle.md", written)
            self.assertIn("delivery/docs/change-strategy.md", written)
            self.assertNotIn("delivery/retirement.md", written, "the ledger is the repository's, never replaced")
            self.assertIn("`/strangle`", (repo / "delivery/docs/adoption.md").read_text())

            generated = self.generate(directory, "made", "standard", "typescript")
            self.assertFalse((generated / "commands/strangle.md").exists())
            self.assertFalse((generated / "docs/change-strategy.md").exists())
