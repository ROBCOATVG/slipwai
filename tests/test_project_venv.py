"""A project whose `./init` made `.delivery-tools/venv` is run with that venv first, by everything the board starts.

Where `python3` refuses pip (PEP 668: Homebrew's, a recent Debian's), `./init` puts PyYAML in a venv and tells
the person to put it first on their `PATH`. A child of the board has nobody to tell, so it found the system
`python3` and stopped at its first `import yaml`. What is proved: a child's environment for a project with
that venv has it first, once; a project without one, or no project, is left as it was; and the fleet's
`project_python` picks the venv's `python3` for that project — and, in the frozen app with no `python3` found,
never the app itself, which took the script's path for a verb (every board control that ran a project script).
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import fleet, shell_environment
from slipwai.shell_environment import in_project, login_environment, project_venv


def venv(root: Path) -> Path:
    folder = root / ".delivery-tools/venv" / ("Scripts" if os.name == "nt" else "bin")
    folder.mkdir(parents=True)
    python = folder / ("python3.exe" if os.name == "nt" else "python3")
    python.write_text("#!/bin/sh\n", encoding="utf-8")
    python.chmod(0o755)
    return folder


class ProjectVenvTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())

    def test_a_project_with_the_venv_has_it_first_once(self) -> None:
        folder = venv(self.root)
        held = in_project({"PATH": os.pathsep.join(["/usr/bin", str(folder)])}, self.root)
        self.assertEqual(held["PATH"].split(os.pathsep), [str(folder), "/usr/bin"])

    def test_without_one_or_without_a_project_nothing_changes(self) -> None:
        self.assertIsNone(project_venv(self.root))
        self.assertEqual(in_project({"PATH": "/usr/bin"}, self.root), {"PATH": "/usr/bin"})
        self.assertEqual(in_project({"PATH": "/usr/bin"}, None), {"PATH": "/usr/bin"})

    def test_the_login_environment_for_a_project_carries_it(self) -> None:
        folder = venv(self.root)
        held = login_environment({"PATH": "/usr/bin"}, shell="/nonexistent/shell", root=self.root)
        self.assertEqual(held["PATH"].split(os.pathsep)[0], str(folder))

    @unittest.skipIf(os.name == "nt", "project_python asks python.exe there")
    def test_the_fleet_reads_the_project_with_the_venvs_python(self) -> None:
        folder = venv(self.root)
        self.assertEqual(fleet.project_python(self.root), str(folder / "python3"))

    @unittest.skipIf(os.name == "nt", "project_python asks python.exe there")
    def test_the_frozen_app_never_starts_a_project_script_with_itself(self) -> None:
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(shell_environment, "login_environment", return_value={"PATH": ""}):
            self.assertNotEqual(shell_environment.project_python(self.root), sys.executable)
            self.assertEqual(shell_environment.project_python(self.root), "python3")

    def test_the_frozen_app_on_windows_starts_a_project_script_with_python_exe(self) -> None:
        """Windows starts only `.exe` files and bash's `python3` is a shim, so there it is the `python.exe` the
        board's children find, or `python` — still never `slipwai.exe` itself."""
        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(sys, "frozen", True, create=True):
            with mock.patch.object(shell_environment, "windows_python", return_value=r"C:\Python313\python.exe"):
                self.assertEqual(shell_environment.project_python(self.root), r"C:\Python313\python.exe")
            with mock.patch.object(shell_environment, "windows_python", return_value=None):
                self.assertEqual(shell_environment.project_python(self.root), "python")


if __name__ == "__main__":
    unittest.main()
