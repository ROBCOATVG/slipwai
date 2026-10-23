"""A package may ship services, browser apps or both, and a project combines one of each.

The keel ships no frontend, so the proof that the two halves are separable is a project generated from two
packages that each have only one: the toy (a family with one backend and no browser app) and the `toy-web`
fixture (a family with no backend and one browser app, `toy-vite`). Run through `slipwai` itself, against a
package directory holding just those two, because what is being held is the catalogue the command builds and
the registry it loads — not a fake of either (`docs/frontend-protocol.md`).

And what the loader refuses a frontend-only family for, each on the publisher's machine: a browser app the
`frontends` block does not declare, one it declares and the Python does not answer, one kept anywhere but
`assets/frontends/<name>`, and one shipped without the `shared_code` paragraph its project's pages read.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages

TESTS = Path(__file__).resolve().parent
FIXTURE = TESTS / "fixtures/frontend-family/toy-web"


def slipwai(languages: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    path = os.pathsep.join(filter(None, [str(TESTS), os.environ.get("PYTHONPATH", "")]))
    environment = {**os.environ, "SLIPWAI_LANGUAGES": str(languages), "PYTHONPATH": path,
                   "SLIPWAI_INDEX": checkout_packages.NO_INDEX}
    return subprocess.run([sys.executable, "-m", "slipwai", *arguments], capture_output=True, text=True,
                          env=environment, check=False)


class Packages(unittest.TestCase):
    """A package directory with the toy in it, and the fixture beside it unless a test says otherwise."""

    def setUp(self) -> None:
        self.languages = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.languages, True)
        shutil.copytree(checkout_packages.PACKAGES / "toy", self.languages / "toy")

    def with_fixture(self) -> Path:
        home = self.languages / "toy-web"
        shutil.copytree(FIXTURE, home, ignore=shutil.ignore_patterns("__pycache__"))
        return home


class OneOfEachTest(Packages):
    def test_a_backend_only_install_offers_no_browser_app_and_writes_none(self) -> None:
        listed = slipwai(self.languages, "list")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertNotIn("toy-vite", listed.stdout)
        parent = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, parent, True)
        output = parent / "plain"
        made = slipwai(self.languages, "generate", "plain", "--backend", "toy-plain", "--output", str(parent))
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertFalse((output / "apps/web").exists())
        self.assertEqual(json.loads((output / "project.json").read_text(encoding="utf-8"))["frontend"], "none")

    def test_the_toys_service_and_the_fixtures_browser_app_are_one_project(self) -> None:
        self.with_fixture()
        listed = slipwai(self.languages, "list")
        self.assertIn("toy-vite — written in toy-web", listed.stdout)
        parent = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, parent, True)
        output = parent / "both"
        made = slipwai(self.languages, "generate", "both", "--backend", "toy-plain", "--output", str(parent))
        self.assertEqual(made.returncode, 0, made.stderr)
        manifest = json.loads((output / "project.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["frontend"], "toy-vite", "the one frontend installed is the default")
        deployables = {name: (row["language"], row.get("framework")) for name, row in manifest["deployables"].items()}
        self.assertEqual(deployables, {"service": ("toy", "plain"), "web": ("toy-web", "toy-vite")})
        self.assertIn("<title>both</title>", (output / "apps/web/index.html").read_text(encoding="utf-8"))
        self.assertTrue((output / "apps/web/src/flags.ts").is_file())

    def test_a_frontend_nobody_ships_is_refused_by_generate_in_a_sentence(self) -> None:
        parent = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, parent, True)
        made = slipwai(self.languages, "generate", "nope", "--backend", "toy-plain", "--frontend", "svelte-kit",
                       "--output", str(parent))
        self.assertNotEqual(made.returncode, 0)
        self.assertIn("--frontend svelte-kit needs a language that ships a browser app", made.stderr)


class WhatTheLoaderRefusesTest(Packages):
    """Each fault named by the package, at load, with the toy still loading beside it."""

    def refused(self) -> str:
        listed = slipwai(self.languages, "list")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertNotIn("toy-vite — written in", listed.stdout)
        return listed.stderr

    def test_a_browser_app_the_frontends_block_does_not_declare(self) -> None:
        home = self.with_fixture()
        fragment = json.loads((home / "language.json").read_text(encoding="utf-8"))
        fragment["frontends"] = {}
        fragment["default_framework"] = "none"
        (home / "language.json").write_text(json.dumps(fragment), encoding="utf-8")
        self.assertIn("does not declare it", self.refused())

    def test_a_declared_frontend_the_python_does_not_answer(self) -> None:
        home = self.with_fixture()
        module = home / "slipwai_language_toy_web/__init__.py"
        module.write_text(module.read_text(encoding="utf-8").replace(
            "protocol.BROWSER_APPS: BROWSER_APPS,", ""), encoding="utf-8")
        self.assertIn("answers no browser_apps for it", self.refused())

    def test_a_browser_app_kept_outside_assets_frontends(self) -> None:
        home = self.with_fixture()
        (home / "assets/frontends/toy-vite").rename(home / "assets/toy-vite")
        module = home / "slipwai_language_toy_web/__init__.py"
        module.write_text(module.read_text(encoding="utf-8").replace(
            'ROOT / FRONTENDS_DIRECTORY / "toy-vite"', 'ASSETS / "toy-vite"'), encoding="utf-8")
        self.assertIn("outside assets/frontends/toy-vite", self.refused())

    def test_a_browser_app_without_the_shared_code_paragraph(self) -> None:
        home = self.with_fixture()
        module = home / "slipwai_language_toy_web/__init__.py"
        module.write_text(module.read_text(encoding="utf-8").replace(
            '        protocol.SHARED_CODE: "a placeholder: the toy frontend shares nothing",\n', ""),
            encoding="utf-8")
        self.assertIn("answers no shared_code", self.refused())


if __name__ == "__main__":
    unittest.main()
