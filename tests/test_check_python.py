"""`make verify` names the interpreter it needs, once and first, rather than dying in whichever gate reaches for it.

Every gate is a `python3 scripts/…` line, and which `python3` a shell finds is decided by `PATH` order: a project's
non-interactive macOS shell found `/usr/bin/python3`, 3.9.6, before Homebrew's, and `make verify` died on
`zip() takes no keyword arguments` inside `check-ux-gates`. The scripts are written for 3.10, so `check-python`
says so before any of them runs.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase


class CheckPythonTest(FactoryTestCase):
    def test_an_older_python3_is_named_before_any_gate_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "interpreter", "standard", "python")
            makefile = (repo / "Makefile").read_text()
            self.assertRegex(makefile, r"\nverify: check-python ")
            passed = subprocess.run(["make", "check-python"], cwd=repo, text=True, capture_output=True)
            self.assertEqual((passed.returncode, passed.stdout, passed.stderr), (0, "", ""))
            # An interpreter that reports 3.9.6, the way macOS's system Python does: the version is the only thing
            # the check reads, and `sitecustomize` sets it before the command line runs.
            older = Path(directory) / "older"
            older.mkdir()
            (older / "sitecustomize.py").write_text(
                "import sys\nsys.version_info = (3, 9, 6, 'final', 0)\nsys.version = '3.9.6 (default)'\n")
            failed = subprocess.run(["make", "check-python"], cwd=repo, text=True, capture_output=True,
                                    env={**os.environ, "PYTHONPATH": str(older)})
            self.assertEqual(failed.returncode, 2)
            self.assertIn("is Python 3.9.6, and the gate scripts need 3.10 or newer", failed.stderr)
            self.assertIn("put a newer python3 first on PATH", failed.stderr)
