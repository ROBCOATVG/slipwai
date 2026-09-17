"""How a generated project's npm workspace gets installed: once, by one target, for the whole gate.

`[ -f node_modules/.package-lock.json ] || npm ci` used to sit before every npm line of every npm recipe —
sixteen copies of one decision in a default project, and one more with every recipe added. One file target
says it once, and every target that runs this project's own npm code takes it as a prerequisite, directly or
through `build-packages`. What this suite holds is the property, not the spelling: a fresh clone installs
once, a tree that is already installed installs not at all, and no entry point is left without it.

Asserted by asking Make what it *would* do (`make -n`) rather than by matching recipe text, because what has
to hold is the whole prerequisite chain and not one line of it — the same reason `test_shared_packages.py`
checks its own prerequisite that way.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.catalog import axis_default

# Every entry point that runs a generated project's own npm code, including those that reach the install
# through a prerequisite of their own rather than by naming it.
NPM_ENTRY_POINTS = ("verify", "test", "test-integration", "migrate", "dev", "dev-web", "build-service")


def plan(repo: Path, *targets: str) -> str:
    """What Make would run for these targets, without running any of it."""
    return subprocess.run(
        ["make", "-n", *targets], cwd=repo, text=True, capture_output=True, check=True
    ).stdout


class NpmInstallTest(FactoryTestCase):
    def npm_project(self, directory: str) -> Path:
        """A project with every npm entry point above: a Node service, a browser app, migrations to apply
        and, under a production target, an image to build."""
        return self.generate(
            directory, "installed", "event-modelling", "typescript", "react-vite", target="aws",
            event_store="postgres", http=axis_default("http", "typescript", "aws"),
        )

    def test_no_recipe_installs_the_workspace_itself(self) -> None:
        """One target runs `npm ci`, and `make install` — the deliberate one a person types — runs it too.
        Any third is a recipe that has gone back to guarding itself."""
        with tempfile.TemporaryDirectory() as directory:
            makefile = (self.npm_project(directory) / "Makefile").read_text()
            self.assertNotIn("|| npm ci", makefile)
            self.assertIn("\nnode_modules/.package-lock.json: package.json package-lock.json\n", makefile)
            self.assertEqual(2, makefile.count("\n\tnpm ci\n"), makefile)

    def test_every_entry_point_installs_the_workspace_exactly_once(self) -> None:
        """Once, not never: a target that lost the prerequisite would run `npm --workspace` against a tree
        with no `node_modules` and fail with the directory sitting right there."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.npm_project(directory)
            for target in NPM_ENTRY_POINTS:
                with self.subTest(target=target):
                    self.assertEqual(1, plan(repo, target).count("npm ci"), plan(repo, target))

    def test_a_tree_that_is_already_installed_is_not_installed_again(self) -> None:
        """The marker npm writes at the end of a successful install is newer than the manifests it was
        installed from, so Make has nothing to do. This is the half a guard got right and the half a plain
        `.PHONY` install target would get wrong."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.npm_project(directory)
            marker = repo / "node_modules/.package-lock.json"
            marker.parent.mkdir()
            marker.touch()
            self.assertNotIn("npm ci", plan(repo, "verify"))

    def test_a_project_with_no_npm_workspace_is_given_no_install_target(self) -> None:
        """There is no root manifest for `npm ci` to read, so a target naming one could only fail."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "native", "standard", "go", "none")
            self.assertNotIn("npm", (repo / "Makefile").read_text())
