"""The explicit claim CLI cannot bypass a crossing's proposed fairways."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import ROOT


class ClaimGuardTest(unittest.TestCase):
    def test_explicit_take_refuses_a_proposal_before_even_asking_git_and_allows_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            scripts = root / "scripts/agents"
            scripts.mkdir(parents=True)
            for name in ("claims.py", "logs.py"):
                shutil.copyfile(ROOT / "assets/toolkit/scripts/agents" / name, scripts / name)
            (root / "project.json").write_text("{}", encoding="utf-8")
            (root / ".slipwai").mkdir()
            state: dict = {"v": 1, "features": {"ordering": {"proposed": ["ordering"], "unplaced": ["ORD-03"]}}}
            path = root / ".slipwai/migration.json"
            path.write_text(json.dumps(state), encoding="utf-8")
            call = [sys.executable, str(scripts / "claims.py"), "--take", "ordering"]
            refused = subprocess.run(call, cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
            self.assertIn("confirmation", refused.stdout)
            self.assertFalse((root / ".git").exists())
            state["features"]["ordering"] = {"proposed": [], "unplaced": []}
            path.write_text(json.dumps(state), encoding="utf-8")
            accepted = subprocess.run(call, cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
