"""`--target existing`: a project that deploys to infrastructure it does not own.

The third target row (brownfield adoption; experimental as `AGENTS.md` defines the word). It manages
nothing — no `infra/`, no pipeline, no `make deploy`, no flag mechanism — and offers exactly what `none`
offers, so what is gated is the other half: that the documentation of *where* this goes and the
release-constraint rung of `/drive` turn on, that they say what the adoption recorded about the
infrastructure, and that `adopt` picks the target from where the infrastructure lives.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import node_repository, slipwai


class ExistingTargetTest(FactoryTestCase):
    def test_a_generated_project_going_to_existing_infrastructure_documents_it_and_provisions_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "elsewhere", "standard", "typescript", target="existing", http="fastify"
            )
            self.assertEqual(json.loads((repo / "project.json").read_text())["target"], "existing")
            absent_paths = (
                "infra", ".github/workflows/deploy.yml", ".github/workflows/rollback.yml", "scripts/deploy.py",
            )
            for absent in absent_paths:
                self.assertFalse((repo / absent).exists(), absent)
            makefile = (repo / "Makefile").read_text()
            for target in ("deploy:", "build:", "smoke-image:", "check-flags:", "bootstrap:"):
                self.assertNotIn(f"\n{target}", makefile, target)
            page = (repo / "docs/deployment.md").read_text()
            self.assertTrue(page.startswith("# Where `elsewhere` deploys"))
            self.assertIn("Home: **`unknown`**", page)
            self.assertIn("## How a release reaches production", page)
            drive = (repo / "commands/drive.md").read_text()
            self.assertIn("**Release constraint** — this project deploys to infrastructure the factory does not", drive)
            self.assertNotIn("flags.auto.tfvars", drive)
            self.assertIn("`target: existing`", (repo / "AGENTS.md").read_text())
            readme = (repo / "README.md").read_text()
            self.assertIn("## Production\n\nThis project deploys to infrastructure this factory does not", readme)
            self.assertIn("- Where it deploys: `docs/deployment.md`", (repo / "docs/whats-included.md").read_text())
            self.assertIn("deployment.md", (repo / "docs/README.md").read_text())
            settings = (repo / ".claude/settings.json").read_text()
            self.assertNotIn("tofu", settings)
            verified = subprocess.run(["make", "verify"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(verified.returncode, 0, verified.stdout[-3000:] + verified.stderr[-3000:])
            listed = subprocess.run(
                ["python3", "scripts/backing-services.py", "--list"], cwd=repo, text=True, capture_output=True
            )
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("fastify", listed.stdout, "existing offers what none offers")
            self.assertIn("none      None", listed.stdout)

    def test_adopt_takes_the_target_from_where_the_infrastructure_lives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = node_repository(Path(directory))
            (repo / "infra").mkdir()
            (repo / "infra/main.tf").write_text('resource "aws_s3_bucket" "b" {}\n')
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(
                ["git", "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "tf"],
                cwd=repo, check=True,
            )
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["target"], "existing")
            self.assertEqual(document["infrastructure"]["home"], "here")
            page = (repo / "delivery/docs/deployment.md").read_text()
            self.assertIn("Home: **`here`** (recorded as `detected`)", page)
            self.assertIn("opentofu / terraform", page)
            self.assertIn("never let two places manage one resource", page)
            self.assertIn("Release constraint", (repo / "delivery/commands/drive.md").read_text())

            library = node_repository(Path(directory) / "lib")
            result = slipwai(library, "adopt", "--yes", "--infrastructure", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((library / "project.json").read_text())["target"], "none")
            self.assertFalse((library / "delivery/docs/deployment.md").exists())

            named = node_repository(Path(directory) / "named")
            result = slipwai(
                named, "adopt", "--yes", "--infrastructure", "elsewhere",
                "--infrastructure-repository", "https://x/platform.git", "--target", "existing",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            page = (named / "delivery/docs/deployment.md").read_text()
            self.assertIn("owned by another repository, `https://x/platform.git`", page)
            self.assertIn("(recorded as `overridden`)", page)
