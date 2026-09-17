"""`docs/README.md` lists every page a generated project ships — a page not indexed is a page not found."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from support import FactoryTestCase


def indexed(repo: Path) -> set[str]:
    return set(re.findall(r"\]\(([^)]+\.md)\)", (repo / "docs/README.md").read_text()))


def shipped(repo: Path) -> set[str]:
    return {
        str(path.relative_to(repo / "docs"))
        for path in (repo / "docs").rglob("*.md")
        if path != repo / "docs/README.md"
    }


class DocsIndexTest(FactoryTestCase):
    def test_the_index_lists_exactly_the_pages_the_project_ships(self) -> None:
        """Across the profiles and targets, because each adds pages of its own — the event model's, the
        production target's — and the index is built from the files that ship rather than from a list kept
        beside them. Every link resolves, and the deployment drawing sits under its own heading."""
        with tempfile.TemporaryDirectory() as directory:
            cases = (
                ("event-deployed", "event-modelling", "typescript", "aws"),
                ("standard-local", "standard", "go", "none"),
            )
            for name, profile, language, target in cases:
                repo = self.generate(directory, name, profile, language, target=target)
                self.assertEqual(indexed(repo), shipped(repo), name)
                for page in indexed(repo):
                    self.assertTrue((repo / "docs" / page).is_file(), f"{name}: {page}")
                index = (repo / "docs/README.md").read_text()
                readme = (repo / "README.md").read_text()
                production = target != "none"
                self.assertEqual("## Production" in index, production, name)
                self.assertEqual("deployment.md" in index, production, name)
                self.assertEqual("docs/deployment.md" in readme.split("## Documentation")[1], production, name)
                self.assertEqual("## The event model" in index, profile == "event-modelling", name)
                # Nothing fell through to the catch-all: every page this factory ships has a hook of its own.
                self.assertNotIn("## Also here", index, name)
