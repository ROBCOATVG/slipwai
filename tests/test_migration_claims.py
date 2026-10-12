"""The explicit claim CLI cannot bypass a crossing's proposed fairways, and a check only reports."""
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
from slipwai.errors import GenerationError
from slipwai.migration_claims import ahead


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


class AheadTest(unittest.TestCase):
    """`--check` says what the crossing would do; an open claim is the thing it most needs to say."""

    def command(self, *args: str) -> str:
        done = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True)
        return done.stdout.strip()

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.command("init", "-q", "-b", "main")
        self.command("config", "user.name", "proof")
        self.command("config", "user.email", "proof@example.invalid")
        (self.root / "page.md").write_text("first\n", encoding="utf-8")
        self.command("add", "-A")
        self.command("commit", "-qm", "base")
        self.command("checkout", "-qb", "slice/ORD-03")
        (self.root / "page.md").write_text("in flight\n", encoding="utf-8")
        self.command("commit", "-qam", "work in flight")
        self.command("checkout", "-q", "main")

    def test_a_crossing_refuses_an_open_claim_and_names_the_way_round_it(self) -> None:
        with self.assertRaisesRegex(GenerationError, "slice/ORD-03"):
            ahead(self.root)

    def test_a_check_reports_the_open_claim_instead_of_refusing_to_look(self) -> None:
        notes: list[str] = []
        found = ahead(self.root, notes=notes)
        self.assertEqual(list(found), ["refs/heads/slice/ORD-03"])
        self.assertIn("slice/ORD-03", " ".join(notes))
        self.assertIn("--with-claims", " ".join(notes))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
