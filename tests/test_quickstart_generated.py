"""The whole of a quickstart's promise, end to end: a second project from one name and no remembering.

Slow, and in the `SLOW` list for it: this generates two projects. The fast suite holds everything about the
document, the words and the flags; this holds the one claim that can only be made by doing it.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages
from support import FactoryTestCase, command

from slipwai import quickstart

NEEDS_A_LANGUAGE = "generates a project, so it needs a language installed; the keel ships none"


@unittest.skipUnless(checkout_packages.pinned(), NEEDS_A_LANGUAGE)
class SecondProjectTest(FactoryTestCase):
    def run_slipwai(self, *arguments: str, where: Path, cwd: Path | None = None) -> subprocess.CompletedProcess:
        environment = {**os.environ, quickstart.VARIABLE: str(where),
                       "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        done = subprocess.run(command(*arguments), text=True, capture_output=True, env=environment, cwd=cwd)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done

    def test_the_second_project_has_the_same_languages_axes_and_extensions_as_the_first(self) -> None:
        """The done-when of 13.1, and nothing else proves it: the answers a person gave once, given again
        from a name. What is compared is `project.json`, which is every answer the first was generated
        from — so a quickstart that dropped one would show up here as a difference in the record itself."""
        with tempfile.TemporaryDirectory() as area:
            where = Path(area) / "quickstarts"
            first = self.generate(area, "first", language="toy-plain", persistence="memory")
            self.run_slipwai("quickstart", "save", "ours", "--suits", "The way we start one here.",
                             "--from", str(first), where=where)
            self.run_slipwai("generate", "second", "--quickstart", "ours", "--output", area,
                             "--skip-checks", where=where)
            second = Path(area) / "second"
            self.assertEqual(self.answers(first), self.answers(second))

    @staticmethod
    def answers(project: Path) -> dict:
        """Every answer a project was generated from, as its own manifest records them — its name aside."""
        document = json.loads((project / "project.json").read_text(encoding="utf-8"))
        return {
            "profile": document["profile"],
            "target": document["target"],
            "frontend": document["frontend"],
            "deployables": {name: {key: row[key] for key in ("kind", "language", "selection") if key in row}
                            for name, row in document["deployables"].items()},
        }

    def test_the_project_carries_the_record_of_the_quickstart_it_came_from(self) -> None:
        """So `./init` elects without showing the menu, and the guard question is not asked a second time."""
        with tempfile.TemporaryDirectory() as area:
            where = Path(area) / "quickstarts"
            first = self.generate(area, "one", language="toy-plain")
            self.run_slipwai("quickstart", "save", "ours", "--suits", "The way we start one here.",
                             "--from", str(first), where=where)
            self.run_slipwai("generate", "two", "--quickstart", "ours", "--output", area,
                             "--skip-checks", where=where)
            record = json.loads((Path(area) / "two" / quickstart.RECORD).read_text(encoding="utf-8"))
            self.assertEqual(record["name"], "ours")
            self.assertEqual(record["suits"], "The way we start one here.")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
