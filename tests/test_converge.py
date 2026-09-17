"""`slipwai converge`: the end of an adoption, as one merge that moves the delivery material to the root.

What this gates: `--check` refuses with every reason while a row is below its target or the root holds a file the
move would write over, and moves nothing; the move itself carries the factory's files to the root, then what the
factory does not list — the survey, the ledgers, a person's ADR — and respells the marked blocks; the record says
`converged` and keeps `origin: adopted`; and `migrate` afterwards measures from the converge commit and finds
nothing to do, which is what makes the repository a generated one from then on. Experimental (experimental).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

from support import FactoryTestCase
from test_adopt import OWN, repository, slipwai
from test_replay import git

from slipwai.assets import VERSION
from slipwai.converge import identity

# What `identity` hands back when the checkout cannot name an author of its own.
FALLBACK = ["-c", "user.name=slipwai converge", "-c", "user.email=converge@local"]

ADR = """# 0002. Leave the architecture where it is

Date: 2026-09-07

## Status

Accepted

## Context

The runtime was the trigger, and it has been upgraded.

## Decision

Strategy: leave-it

## Consequences

The retirement ledger stays empty on purpose.
"""

# The repository's own files, less the Makefile: a Makefile of its own is the usual clash, and the first test
# puts one back to show the refusal.
FILES = {
    **{path: text for path, text in OWN.items() if path != "Makefile"},
    "apps/shop/package.json": json.dumps({
        "name": "shop", "private": True,
        "scripts": {"test": "node --test", "lint": "node -e 0", "typecheck": "node -e 0", "start": "node src/index.js"},
    }),
    "apps/shop/src/index.js": "module.exports = 1;\n",
    "apps/shop/test/a.test.js": 'require("node:test")("a", () => {});\n',
    "apps/shop/Dockerfile": "FROM node:22\nCMD [\"node\", \"src/index.js\"]\n",
    ".github/workflows/deploy.yml": "on: push\njobs:\n  deploy:\n    steps:\n      - run: ./deploy\n",
}


def at_target(repo: Path) -> None:
    """Every row at its target, as a person confirms them once the rungs are established, with the tree agreeing."""
    document = json.loads((repo / "project.json").read_text())
    for row in document["convergence"]:
        row["rung"], row["provenance"], row["planned"] = row["target"], "confirmed", None
    shop = document["deployables"]["shop"]
    shop["kind"], shop["layout"] = "service", "hexagonal"
    shop["commands"]["typecheck"] = "cd apps/shop && npm run typecheck"
    (repo / "project.json").write_text(json.dumps(document, indent=2) + "\n")
    (repo / ".specify/memory").mkdir(parents=True, exist_ok=True)
    (repo / ".specify/memory/constitution.md").write_text("# Constitution\n\nRatified in full.\n")
    (repo / "delivery/docs/adr").mkdir(parents=True, exist_ok=True)
    (repo / "delivery/docs/adr/0002-leave-it.md").write_text(ADR)


class ConvergeTest(FactoryTestCase):
    def test_check_refuses_with_every_reason_and_moves_nothing_until_every_row_is_at_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", FILES)
            self.assertEqual(slipwai(repo, "adopt", "--yes", "--why", "the runtime is end of life").returncode, 0)
            before = git(repo, "rev-parse", "HEAD").stdout
            checked = slipwai(repo, "converge", "--check")
            self.assertEqual(checked.returncode, 1, checked.stdout)
            self.assertIn("not yet", checked.stdout)
            self.assertIn("safety-net stands at `tests-exist`, target `mutation-measured`", checked.stdout)
            self.assertIn("path-to-production stands at `pipeline`", checked.stdout)
            refused = slipwai(repo, "converge")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("safety-net stands at", refused.stderr)
            self.assertEqual(git(repo, "rev-parse", "HEAD").stdout, before, "a refusal moves nothing")
            self.assertTrue((repo / "delivery/Makefile").is_file())
            # A Makefile of the repository's own is the usual clash, and it is named rather than written over.
            (repo / "Makefile").write_text("build:\n\techo theirs\n")
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "our Makefile")
            clash = slipwai(repo, "converge", "--check")
            self.assertIn("`Makefile` exists at the root and the move would write over it", clash.stdout)
            self.assertIn("A `Makefile` of the repository's own is the usual one", clash.stdout)

    def test_converging_moves_the_material_to_the_root_as_one_merge_and_the_repository_is_generated_from_then_on(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", FILES)
            self.assertEqual(slipwai(repo, "adopt", "--yes", "--why", "the runtime is end of life").returncode, 0)
            at_target(repo)
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "every rung established")
            # The refresh redraws the pages from the rows a person moved, so the gate's digest matches the record.
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "pages redrawn")
            checked = slipwai(repo, "converge", "--check")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("ready", checked.stdout)

            converged = slipwai(repo, "converge")
            self.assertEqual(converged.returncode, 0, converged.stdout + converged.stderr)
            self.assertIn(f"converged shop with slipwai {VERSION}", converged.stdout)
            self.assertFalse((repo / "delivery").exists(), "nothing is left behind under the delivery directory")
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")
            makefile = (repo / "Makefile").read_text()
            self.assertIn("verify:", makefile)
            self.assertNotIn("slipwai:delivery:begin", makefile, "the factory's Makefile, not the include adopt wrote")
            listed = (repo / ".written").read_text().split()
            self.assertIn("Makefile", listed)
            self.assertIn("docs/adoption.md", listed)
            self.assertFalse(any(path.startswith("delivery/") for path in listed))
            # What the factory does not list moved with it: the survey, the ledgers, the person's ADR.
            for moved in ("survey/survey.md", "survey/structure.md", "survey/pinned.md", "retirement.md",
                          "docs/adr/0002-leave-it.md"):
                self.assertTrue((repo / moved).is_file(), moved)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["origin"], "adopted", "history, kept")
            self.assertEqual(document["layout"]["delivery"], ".")
            self.assertEqual(document["converged"], {"with": VERSION, "from": "delivery"})
            self.assertTrue(all(row["rung"] == row["target"] for row in document["convergence"]))
            agents = (repo / "AGENTS.md").read_text()
            self.assertTrue(agents.startswith(OWN["AGENTS.md"].rstrip("\n")), "the repository's own text stands")
            self.assertIn("`docs/adoption.md` first", agents)
            self.assertNotIn("delivery/", agents.split("<!-- extension:delivery:begin -->")[1])
            self.assertNotIn("delivery/", (repo / ".gitignore").read_text())
            self.assertIn("**Converged.**", (repo / "docs/adoption.md").read_text())
            self.assertIn(f"**Converged** with slipwai {VERSION}", (repo / "docs/convergence.md").read_text())
            log = git(repo, "log", "--format=%s %ae", "-3").stdout.splitlines()
            self.assertIn("Move what the merge did not carry from delivery/ to the root", log[0])
            self.assertIn("Converge shop: the delivery material moves from delivery/ to the root factory@local", log[1])
            # From then on, a generated project: the next migrate measures from the converge commit, finds
            # `.written` at the root, and has nothing to do.
            migrated = slipwai(repo, "migrate")
            self.assertEqual(migrated.returncode, 0, migrated.stderr)
            self.assertIn("nothing to migrate", migrated.stdout)
            again = slipwai(repo, "converge", "--check")
            self.assertEqual(again.returncode, 1)
            self.assertIn(f"already converged with slipwai {VERSION}", again.stdout)

    def test_the_finishing_commit_falls_back_unless_the_checkout_has_both_a_name_and_an_email(self) -> None:
        """Git refuses a commit that has one and not the other, so half an identity has to count as none.
        A machine whose global config sets `user.email` alone — a CI runner, a fresh container — stood the
        fallback aside on the strength of the email and then exited 128 at the commit."""
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            git(repo, "init", "--quiet")
            # The repository's own config is the only one in play, so the machine running the suite cannot
            # decide the answer.
            with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}):
                self.assertEqual(identity(repo), FALLBACK, "nothing configured is the fallback")
                git(repo, "config", "user.email", "half@local")
                self.assertEqual(identity(repo), FALLBACK, "an email with no name is still the fallback")
                git(repo, "config", "user.name", "Half Configured")
                self.assertEqual(identity(repo), [], "both configured, and the repository's own identity stands")
