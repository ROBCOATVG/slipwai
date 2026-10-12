"""A project, generated, and read back off the disk.

This is the first test that runs the whole keel end to end: the catalogue merged with a package, the
registry built from it, the scaffold assembling a tree, and the files written. Until slice 3.8 put the
toy package in the directory there was nothing to generate with, and until 4.1 brought `generate` there
was no verb to do it.

It is slow — it writes seven hundred files — so it is in the Makefile's `SLOW` list and runs in
`make verify` rather than `make unit`. That is the two-gate split working as intended: the fast gate
stays worth running and the expensive proof still happens before anything merges.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages

from slipwai import native
from slipwai.assets import ADOPTION_ROOT
from slipwai.project import prose

REPOSITORY = Path(__file__).resolve().parents[1]
TOY = "toy-plain"


@unittest.skipUnless(checkout_packages.installed("toy"), "needs the toy package: slice 3.8")
class GeneratedProjectTest(unittest.TestCase):
    """One generation, read several ways. Generated once for the class: it is the slow part."""

    project: Path
    scratch: tempfile.TemporaryDirectory[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.scratch = tempfile.TemporaryDirectory()
        done = subprocess.run(
            [sys.executable, "-m", "slipwai", "generate", "demo", "--backend", TOY,
             "--frontend", "none", "--target", "none", "--output", cls.scratch.name],
            cwd=REPOSITORY, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(REPOSITORY / "src"),
                 "SLIPWAI_LANGUAGES": str(checkout_packages.PACKAGES)},
        )
        if done.returncode != 0:
            raise AssertionError(done.stdout + done.stderr)
        cls.project = Path(cls.scratch.name) / "demo"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.scratch.cleanup()

    def test_nothing_the_keel_renders_still_carries_a_placeholder(self) -> None:
        """The third rule of `docs/generated-prose.md`, and the one its other two cannot make: a token can be
        provided, named, and still arrive unresolved if a page is copied by a path that does not render it.

        Read over what the keel renders rather than every file a project receives, because `{{name}}` is not
        the keel's spelling alone — `scripts/agents/registry.json` ships `"argPlaceholder": "{{args}}"` and a
        skill ships `{{badges}}`, both another system's substitution that a harness fills itself. `TEMPLATED`
        names each rendered tree and where it lands — a directory of rendered files, or a single page — and a
        slice of phase 16 that templates another adds its row.
        """
        from test_generated_prose import TEMPLATED

        carried: dict[str, list[str]] = {}
        for directory, lands, _provider in TEMPLATED:
            if directory.is_relative_to(ADOPTION_ROOT):
                # A tree only a repository the method was installed around receives, and some of it lands
                # at a path a generated project has not got at all. `test_adopt_page.py` adopts a real
                # repository and reads these there, which is where they can actually be read.
                continue
            for landing in lands:
                where = self.project / landing
                self.assertTrue(where.exists(), f"{landing} is not in a generated project")
                found = sorted(where.rglob("*")) if where.is_dir() else [where]
                for path in found:
                    if path.is_file() and (left := prose.unresolved(path.read_text(encoding="utf-8"))):
                        carried[str(path.relative_to(self.project))] = left
        self.assertEqual(carried, {}, f"rendered files still carrying a placeholder: {carried}")

    def test_a_project_is_written(self) -> None:
        self.assertTrue((self.project / "project.json").is_file())
        self.assertGreater(len(list(self.project.rglob("*"))), 100)

    def test_codex_project_and_standalone_install_project_the_same_command_skills(self) -> None:
        done = subprocess.run([sys.executable, "scripts/agents/project.py", "codex"],
                              cwd=self.project, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue((self.project / ".agents/skills/sail/SKILL.md").is_file())
        self.assertFalse((self.project / ".codex/prompts").exists())
        standalone = native.files("codex")
        for name in ("chart", "example-map", "mockups"):
            path = f".agents/skills/{name}/SKILL.md"
            self.assertEqual((self.project / path).read_text(encoding="utf-8"), standalone[path], path)

    def test_every_file_written_is_utf_8(self) -> None:
        """Generation wrote in the platform's locale codec until slice 4.1 — cp1252 on Windows, which
        cannot encode the first em dash in the toolkit and failed the generation outright. An asset is
        bytes the keel copies into somebody's repository, and the machine must not change them."""
        for path in sorted(self.project.rglob("*")):
            if path.is_file() and path.suffix in (".md", ".py", ".json", ".yml", ".yaml", ".txt"):
                with self.subTest(file=str(path.relative_to(self.project))):
                    path.read_text(encoding="utf-8")

    def test_something_written_actually_carries_a_non_ascii_character(self) -> None:
        """Otherwise the check above passes on a tree of pure ASCII and proves nothing."""
        found = [path for path in self.project.rglob("*.md") if path.is_file()
                 and any(ord(ch) > 127 for ch in path.read_text(encoding="utf-8"))]
        self.assertTrue(found, "no generated file has a character cp1252 would have choked on")

    def test_the_manifest_records_the_keel_and_the_package_that_made_it(self) -> None:
        recorded = json.loads((self.project / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(recorded["generator"]["generatedWith"],
                         (REPOSITORY / "VERSION").read_text(encoding="utf-8").strip())
        self.assertIn("toy", recorded["generator"]["languages"])

    def test_no_script_the_keel_ships_reads_or_writes_in_the_machines_locale(self) -> None:
        """Every one of these runs on somebody else's machine, under whatever locale it has. Python
        without an explicit encoding uses that locale's codec — cp1252 on Windows — and the pruner
        failed every generation there until this was swept. A shipped script is the worst place for it:
        the keel's own copy is one machine's problem, and a shipped one is every project's."""
        for path in sorted(self.project.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if ".read_text(" in line or ".write_text(" in line:
                    with self.subTest(file=str(path.relative_to(self.project)), line=line.strip()[:70]):
                        self.assertIn("encoding=", line)

    def test_the_keel_left_no_placeholder_behind(self) -> None:
        """`__APP__`, `__VERIFY__`, `__IMAGE__` and the rest are substituted, never shipped."""
        for path in sorted(self.project.rglob("*")):
            if path.is_file() and path.suffix in (".md", ".py", ".json", ".yml"):
                text = path.read_text(encoding="utf-8")
                for placeholder in ("__APP__", "__VERIFY__", "__IMAGE__", "__REPOSITORY__"):
                    with self.subTest(file=str(path.relative_to(self.project)), placeholder=placeholder):
                        self.assertNotIn(placeholder, text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
