"""The toolchain pin files, and the one place each version they hold is written.

The point of a pin file is that a laptop runs what CI runs, so the assertions that matter compare the pin
file with the workflow rather than with a number typed in here: a second copy of the version would make this
suite pass while the two files disagreed, which is the failure the files exist to prevent.
"""
from __future__ import annotations

import re
import tempfile

from support import FactoryTestCase

from slipwai.backends import NODE_MAJOR, PYTHON_VERSION
from slipwai.project.adopted import OWN
from slipwai.project.pins import pin_files
from slipwai.services import default_apps

SETUP_NODE = re.compile(r"actions/setup-node@v\d+\n\s+with:\n\s+node-version: '?(\d+)'?")
SETUP_PYTHON = re.compile(r"actions/setup-python@v\d+\n\s+with:\n\s+python-version: '?([\d.]+)'?")


class PinsTest(FactoryTestCase):
    def test_a_node_project_is_pinned_to_the_node_its_own_workflow_installs(self) -> None:
        """`.nvmrc` and `setup-node` read one constant, so the two cannot say different things."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "pinned", "event-modelling", "typescript", "react-vite")
            workflow = (repo / ".github/workflows/verify.yml").read_text()
            found = SETUP_NODE.search(workflow)
            self.assertIsNotNone(found, workflow)
            assert found is not None
            self.assertEqual(found.group(1), (repo / ".nvmrc").read_text().strip())
            self.assertEqual(str(NODE_MAJOR), (repo / ".nvmrc").read_text().strip())

    def test_a_python_project_is_pinned_to_the_python_its_own_workflow_installs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "pinned", "standard", "python", "none")
            workflow = (repo / ".github/workflows/verify.yml").read_text()
            found = SETUP_PYTHON.search(workflow)
            self.assertIsNotNone(found, workflow)
            assert found is not None
            self.assertEqual(found.group(1), (repo / ".python-version").read_text().strip())
            self.assertEqual(PYTHON_VERSION, (repo / ".python-version").read_text().strip())

    def test_every_project_has_the_whitespace_conventions_and_only_the_pins_it_needs(self) -> None:
        """A pin file for a toolchain the project does not have would be a version nothing keeps true. Go
        and Java take none at all: `go.mod` and the Maven wrapper are where their own tools look."""
        expected = {
            ("typescript", "none"): {".editorconfig", ".nvmrc"},
            ("python", "react-vite"): {".editorconfig", ".nvmrc", ".python-version"},
            ("go", "none"): {".editorconfig"},
            ("java-spring", "none"): {".editorconfig"},
        }
        with tempfile.TemporaryDirectory() as directory:
            for (backend, frontend), pins in expected.items():
                with self.subTest(backend=backend, frontend=frontend):
                    repo = self.generate(directory, f"pins-{backend}-{frontend}", "standard", backend, frontend)
                    present = {
                        name for name in (".editorconfig", ".nvmrc", ".python-version", ".go-version")
                        if (repo / name).exists()
                    }
                    self.assertEqual(pins, present)
                    self.assertIn("root = true", (repo / ".editorconfig").read_text())

    def test_the_page_that_lists_what_was_generated_names_the_pins_that_shipped(self) -> None:
        """Read off the set that ships rather than restated, so a Go project is not told about an `.nvmrc`."""
        with tempfile.TemporaryDirectory() as directory:
            for name, backend, frontend, absent in (
                ("listed-node", "typescript", "none", ".python-version"),
                ("listed-go", "go", "none", ".nvmrc"),
            ):
                with self.subTest(backend=backend):
                    repo = self.generate(directory, name, "standard", backend, frontend)
                    page = (repo / "docs/whats-included.md").read_text()
                    self.assertIn("`.editorconfig`", page)
                    self.assertNotIn(f"`{absent}`", page)

    def test_an_adopted_repository_keeps_its_own_conventions(self) -> None:
        """A repository that already exists has answered every one of these for itself, and the factory's
        answer would be wrong. `adopted.OWN` is where that is declared."""
        # A project with every pin file there is: a Python service and a browser app.
        for path in pin_files(default_apps("python", "react-vite")):
            self.assertIn(path, OWN, f"an adoption would write {path} over the repository's own")
