"""`describe-service`: what a service already on the list is for, recorded after the scaffold.

A purpose left unsaid at generation, and contexts found later in the model or the specification, had no
command to record them: the architecture page said "no purpose recorded yet" and pointed at scaffold-time
flags, so the choice was editing `project.json` by hand against a file the factory owns. This proves the verb
writes the manifest and every page that prints the two fields, touches nothing scaffolded, and refuses the
same things `add-service` refuses.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase, commit_all

from slipwai.assets import ROOT


def describe(repo: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(ROOT / "slipwai"), "describe-service", *arguments], cwd=repo, text=True, capture_output=True
    )


def porcelain(repo: Path) -> list[str]:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE)
    return sorted(line[3:] for line in out.stdout.splitlines())


class DescribeServiceTest(FactoryTestCase):
    def test_a_purpose_and_contexts_recorded_afterwards_reach_every_page_that_prints_them(self) -> None:
        """The manifest entry gains the two fields, the architecture page and the guidance say them instead of
        "no purpose recorded yet", the service's own tree is untouched, and a second call replaces one field
        while leaving the other as it was."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "described", "standard", "python", "react-vite")
            self.assertIn("no purpose recorded yet", (repo / "docs/architecture.md").read_text())
            first = describe(repo, "service", "--purpose", "Keeps the campaign ledger.", "--context", "campaign",
                             "--context", "ledger")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("recorded for apps/service: it holds the bounded contexts `campaign`, `ledger` and owns: "
                          "Keeps the campaign ledger.", first.stdout)
            self.assertIn("regenerated from it: ", first.stdout)
            entry = json.loads((repo / "project.json").read_text())["deployables"]["service"]
            self.assertEqual((entry["purpose"], entry["contexts"]),
                             ("Keeps the campaign ledger.", ["campaign", "ledger"]))
            architecture = (repo / "docs/architecture.md").read_text()
            self.assertNotIn("no purpose recorded yet", architecture)
            self.assertIn("- `campaign` — `apps/service`: Keeps the campaign ledger.", architecture)
            self.assertIn("- `ledger` — `apps/service`: Keeps the campaign ledger.", architecture)
            self.assertIn("slipwai describe-service <name> --purpose", architecture)
            self.assertIn("Keeps the campaign ledger.", (repo / "commands/add-service.md").read_text())
            changed = porcelain(repo)
            self.assertIn("project.json", changed)
            self.assertIn("docs/architecture.md", changed)
            self.assertFalse([path for path in changed if path.startswith("apps/")], changed)
            commit_all(repo, "described")
            # One field replaced, the other kept.
            second = describe(repo, "service", "--context", "campaign")
            self.assertEqual(second.returncode, 0, second.stderr)
            entry = json.loads((repo / "project.json").read_text())["deployables"]["service"]
            self.assertEqual((entry["purpose"], entry["contexts"]), ("Keeps the campaign ledger.", ["campaign"]))
            self.assertNotIn("- `ledger` —", (repo / "docs/architecture.md").read_text())
            commit_all(repo, "narrowed")
            # The generated project's own gates still hold what was recorded.
            for gate in ("check-imports", "check-agents"):
                result = subprocess.run(["make", gate], cwd=repo, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, f"{gate}: {result.stdout}{result.stderr}")

    def test_every_refusal_says_why_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "refusing", "standard", "python", "react-vite")
            for arguments, reason in (
                (("service",), "nothing to record: say --purpose, --context (once per context), or both"),
                (("payments", "--purpose", "x"),
                 "project.json lists no application named 'payments'; it has service, web"),
                (("web", "--purpose", "x"), "'web' is a browser app; a purpose and bounded contexts are a service's"),
                (("service", "--context", "Not A Name"), "context"),
            ):
                refused = describe(repo, *arguments)
                self.assertEqual(refused.returncode, 2, arguments)
                self.assertIn(reason, refused.stderr, arguments)
                self.assertEqual(porcelain(repo), [], arguments)
            (repo / "scratch").write_text("dirty\n")
            dirty = describe(repo, "service", "--purpose", "x")
            self.assertEqual(dirty.returncode, 2)
            self.assertIn("uncommitted changes", dirty.stderr)
            (repo / "scratch").unlink()
            recorded = describe(repo, "service", "--purpose", "Owns the ledger.")
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            commit_all(repo, "described")
            same = describe(repo, "service", "--purpose", "Owns the ledger.")
            self.assertEqual(same.returncode, 2)
            self.assertIn("'service' already records exactly that; nothing to write", same.stderr)
            self.assertEqual(porcelain(repo), [])
