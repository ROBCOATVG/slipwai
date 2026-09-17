"""The three facts `slipwai adopt` used to assume, now read off the tree or left visibly open.

The first real adoptions found a GitHub workflow written into repositories whose CI was somewhere else, every
buildable directory recorded as a service, and nothing asked about how a change reaches production. What this
suite gates is the rule that replaced the assumptions: each fact is proposed only from a file that says so, the
record says where it came from, what nothing says is `unrecorded` rather than defaulted, the re-survey fills it
the moment a file can say, and a flag says outright. Experimental, with the rest of adoption (experimental).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import repository, slipwai
from test_replay import git


class AdoptFactsTest(FactoryTestCase):
    def test_the_gate_is_written_for_the_forge_found_and_what_the_tree_does_not_say_stays_unrecorded(self) -> None:
        """No CI, no remote, no start script: nothing is written for a forge, `shop` is an application whose role
        is not recorded, and the release path is unknown — each said in the report and the record, none defaulted.
        The tree then learns, and the re-survey fills what was unrecorded; flags say outright, and the record
        says who said."""
        files = {
            "package.json": json.dumps({"name": "shop", "private": True, "scripts": {"test": "node --test"}}),
            "test/a.test.js": 'require("node:test")("a", () => {});\n',
        }
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", files)
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((repo / ".github").exists(), "no CI here, so no workflow is claimed for a forge")
            self.assertFalse((repo / "delivery/ci").exists())
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["ci"], {
                "forge": "none", "gate": None, "branch": "main", "evidence": "no CI configuration in the tree",
                "provenance": "detected",
            })
            self.assertEqual(document["release"], {"path": "unknown", "evidence": [], "provenance": "unrecorded"})
            shop = document["deployables"]["shop"]
            self.assertEqual((shop["kind"], shop["provenance"]["kind"]), ("application", "unrecorded"))
            self.assertIn("CI: none found in this repository, so nothing was written", result.stdout)
            self.assertIn("what it is for is not recorded", result.stdout)
            self.assertIn("How a change reaches production: not recorded", result.stdout)
            page = (repo / "delivery/docs/adoption.md").read_text()
            self.assertIn("an application whose role is not recorded", page)
            self.assertIn("No CI configuration was written: the survey found none", page)
            self.assertIn("**Not recorded** (`unrecorded`)", page)
            self.assertIn("Recorded: **unknown** (`unrecorded`)", (repo / "delivery/docs/deployment.md").read_text())
            # The map: every axis at the rung the record establishes, the page rendered from those rows, and the
            # report's one line about it.
            rows = {row["axis"]: row for row in document["convergence"]}
            self.assertEqual((rows["path-to-production"]["rung"], rows["path-to-production"]["provenance"]),
                             ("unknown", "unrecorded"))
            self.assertEqual(rows["structure"]["rung"], "as-found")
            self.assertEqual(rows["safety-net"]["rung"], "tests-exist")
            page = (repo / "delivery/docs/convergence.md").read_text()
            self.assertTrue(page.startswith("<!-- convergence: "), "the page names the rows it was rendered from")
            self.assertIn("| Path to production | `unknown` | `pipeline-decides` |", page)
            self.assertEqual(rows["data"]["rung"], "settled", "no schema anywhere is one place")
            self.assertIn("Map: delivery/docs/convergence.md — 1 of 9 axes", result.stdout)
            self.assertIn("delivery/docs/convergence.md", (repo / "delivery/.written").read_text())

            # The tree learns: a Dockerfile and a deploying workflow arrive, and the re-survey fills in what was
            # unrecorded — with `detected` provenance, since a file now says — and the gate follows the forge.
            (repo / "Dockerfile").write_text("FROM node:20\n")
            (repo / ".github/workflows").mkdir(parents=True)
            (repo / ".github/workflows/deploy.yml").write_text("on: push\njobs:\n  deploy:\n    steps: []\n")
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "ci and a container")
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertIn("shop: kind refreshed to `service` from `Dockerfile`", refreshed.stdout)
            self.assertIn("ci: forge refreshed to `github`", refreshed.stdout)
            self.assertIn("release: path refreshed to `pipeline`", refreshed.stdout)
            document = json.loads((repo / "project.json").read_text())
            shop = document["deployables"]["shop"]
            self.assertEqual((shop["kind"], shop["provenance"]["kind"]), ("service", "detected"))
            self.assertEqual(document["ci"]["forge"], "github")
            self.assertEqual(document["ci"]["gate"], ".github/workflows/verify-delivery.yml")
            self.assertEqual(document["release"]["path"], "pipeline")
            self.assertEqual(document["release"]["provenance"], "detected")
            self.assertTrue((repo / ".github/workflows/verify-delivery.yml").is_file(), "the gate follows the forge")
            self.assertIn(".github/workflows/verify-delivery.yml", (repo / "delivery/.written").read_text())
            self.assertIn("convergence: path-to-production refreshed from `unknown` to `pipeline`", refreshed.stdout)
            self.assertIn("convergence: structure refreshed from `as-found` to `named`", refreshed.stdout)
            rows = {row["axis"]: row for row in document["convergence"]}
            self.assertEqual(rows["path-to-production"]["rung"], "pipeline")
            self.assertIn("| Structure | `named` |", (repo / "delivery/docs/convergence.md").read_text())

        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", files)
            result = slipwai(
                repo, "adopt", "--yes", "--forge", "gitea", "--release", "manual", "--kind", "shop=library"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual((document["ci"]["forge"], document["ci"]["provenance"]), ("gitea", "overridden"))
            self.assertTrue((repo / ".github/workflows/verify-delivery.yml").is_file(), "Gitea runs Actions workflows")
            self.assertEqual((document["release"]["path"], document["release"]["provenance"]), ("manual", "overridden"))
            shop = document["deployables"]["shop"]
            self.assertEqual((shop["kind"], shop["provenance"]["kind"]), ("library", "overridden"))
            self.assertIn("a library", result.stdout)
            self.assertIn("Gitea Actions", result.stdout)
            self.assertIn("How a change reaches production: by hand (overridden)", result.stdout)
            other = repository(Path(directory), "other", files)
            refused = slipwai(other, "adopt", "--yes", "--kind", "other=thing")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("--kind takes one of", refused.stderr)
            self.assertFalse((other / "project.json").exists())

    def test_the_gate_holds_the_map_to_the_tree_and_the_page_to_the_record(self) -> None:
        """A row a person moves above what the tree allows fails `verify` by name; a page rendered from other rows
        than the record holds is stale and fails; an unrecorded row passes with a line."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps({"name": "shop", "private": True, "scripts": {"test": "node --test"}}),
                "test/a.test.js": (
                    'const t = require("node:test"); const a = require("node:assert");\n'
                    't("adds", () => a.equal(1 + 1, 3));\n'
                ),
            })
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            clean = {key: value for key, value in os.environ.items() if key not in ("CI", "RATCHET_TIGHTEN")}
            # The suite is red on purpose, and a red suite is quarantined only when a person asks for it by name
            # (`test_ratchet` holds the stop itself); here the person has read it and asks.
            quarantined = subprocess.run(
                ["make", "-f", "delivery/Makefile", "ratchet-tighten"], cwd=repo, text=True, capture_output=True,
                env=clean,
            )
            self.assertEqual(quarantined.returncode, 0, quarantined.stdout[-3000:] + quarantined.stderr[-3000:])
            verified = subprocess.run(
                ["make", "-f", "delivery/Makefile", "verify"], cwd=repo, text=True, capture_output=True, env=clean
            )
            self.assertEqual(verified.returncode, 0, verified.stdout[-3000:] + verified.stderr[-3000:])
            self.assertIn("integration: `unknown` — unrecorded", verified.stdout)
            self.assertIn("check-convergence: 1 of 9 axes at target", verified.stdout)
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "day one")

            # A person moves the safety net to `tests-pass` while the ratchet quarantines the suite. First the page
            # is stale — the record changed under it — and once /survey has redrawn it, the row is contradicted.
            document = json.loads((repo / "project.json").read_text())
            for row in document["convergence"]:
                if row["axis"] == "safety-net":
                    row.update(rung="tests-pass", provenance="confirmed", planned="slice 2: make the suite green")
            (repo / "project.json").write_text(json.dumps(document, indent=2) + "\n")
            stale = subprocess.run(
                ["make", "-f", "delivery/Makefile", "check-convergence"],
                cwd=repo, text=True, capture_output=True, env=clean,
            )
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("docs/convergence.md is stale", stale.stderr)
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-qam", "a person's row")
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            page = (repo / "delivery/docs/convergence.md").read_text()
            self.assertIn("| Safety net | `tests-pass` | `mutation-measured` |", page)
            self.assertIn("slice 2: make the suite green", page)
            contradicted = subprocess.run(
                ["make", "-f", "delivery/Makefile", "check-convergence"],
                cwd=repo, text=True, capture_output=True, env=clean,
            )
            self.assertNotEqual(contradicted.returncode, 0)
            self.assertIn("safety-net is recorded at `tests-pass` (confirmed), but the ratchet quarantines",
                contradicted.stderr)

    def test_the_record_stays_still_between_surveys_and_says_when_the_platform_moved(self) -> None:
        """A `/survey` that finds nothing changed rewrites nothing that a fact did not move: the platform keeps the day
        it was last dated, the architecture view counts the commits before the method arrived rather than the last N,
        and a row a person placed keeps their words as its evidence. A version that did move is said — as a
        disagreement, until the Platform row or an ADR owns the move — because one adoption moved Spring a major
        version inside a slice about Docker and nothing said so."""
        with tempfile.TemporaryDirectory() as directory:
            manifest = {"name": "shop", "private": True, "scripts": {"test": "node --test"}, "engines": {"node": "18"}}
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps(manifest),
                "test/a.test.js": 'require("node:test")("a", () => {});\n',
            })
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual([p["version"] for p in document["platform"]["products"]], ["18"])
            document["platform"]["dated"] = "2026-01-01"
            for row in document["convergence"]:
                if row["axis"] == "integration":
                    row.update(rung="trunk", provenance="confirmed", evidence="we merge daily, the person said")
            (repo / "project.json").write_text(json.dumps(document, indent=2) + "\n")
            (repo / "src.js").write_text("// the repository's own commit, after the method arrived\n")
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-qm", "theirs, after adoption")
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertNotIn("disagrees:", refreshed.stdout)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["platform"]["dated"], "2026-01-01", "nothing moved, so nothing is re-dated")
            integration = next(r for r in document["convergence"] if r["axis"] == "integration")
            self.assertEqual(integration["evidence"], "we merge daily, the person said")
            view = (repo / "delivery/survey/structure.md").read_text()
            self.assertIn("1 commit(s) in the history", view, "the commit after adoption is not counted")
            # A version that moved without the Platform row planning it is a disagreement, and re-dates the platform.
            (repo / "package.json").write_text(json.dumps({**manifest, "engines": {"node": "20"}}))
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-qam", "node 20, inside a slice")
            moved = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(moved.returncode, 0, moved.stderr)
            self.assertIn("disagrees: platform: Node.js moved 18 → 20 for shop, and the Platform row planned nothing",
                          moved.stdout)
            self.assertIn("a platform move is a slice of its own on that row", moved.stdout)
            self.assertNotEqual(json.loads((repo / "project.json").read_text())["platform"]["dated"], "2026-01-01")

    def test_a_strangler_with_no_new_home_is_said_on_the_gate(self) -> None:
        """A strangler fig decided, slices archived, the ledger empty and every deployable one that was here: the gate
        says nothing has moved to a new home — said, not failed, since the map's row is truthfully `decided`."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps({"name": "shop", "private": True, "scripts": {"test": "node --test"}}),
                "test/a.test.js": 'require("node:test")("a", () => {});\n',
            })
            self.assertEqual(slipwai(repo, "adopt", "--yes", "--why", "a new feature the system cannot accommodate")
                             .returncode, 0)
            (repo / "delivery/docs/adr/0002-strangle.md").write_text(
                "# 0002. Strangle it\n\nDate: 2026-09-09\n\n## Status\n\nAccepted\n\nStrategy: strangler-fig\n"
            )
            (repo / "specs/001-ratings/slices/P1").mkdir(parents=True)
            (repo / "specs/001-ratings/slices/P1/plan.md").write_text("# P1\n")
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-qm", "decided, and one slice in")
            clean = {key: value for key, value in os.environ.items() if key not in ("CI", "RATCHET_TIGHTEN")}
            checked = subprocess.run(
                ["make", "-f", "delivery/Makefile", "check-convergence"],
                cwd=repo, text=True, capture_output=True, env=clean,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("strategy: `strangler-fig` is decided, 1 slice(s) are archived, the retirement ledger "
                          "reads *removed* for nothing, and every deployable is one that was here — nothing has moved "
                          "to a new home", checked.stdout)

    def test_the_gate_runs_on_the_branch_the_repository_lands_on_and_a_file_taken_over_stays_taken(self) -> None:
        """The third real adoption was on `master`, and a workflow hardcoded to `main` never ran on a push; it could
        not edit the file, since `.written` listed it, and added a second workflow beside it. Now the workflow names
        the branch `.git` says, and deleting a file's line from `.written` makes it the repository's own: `/survey`
        leaves it alone and says so, and the next `.written` no longer lists it."""
        files = {
            "package.json": json.dumps({"name": "shop", "private": True, "scripts": {"test": "node --test"}}),
            "test/a.test.js": 'require("node:test")("a", () => {});\n',
        }
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "shop"
            for relative, content in files.items():
                (repo / relative).parent.mkdir(parents=True, exist_ok=True)
                (repo / relative).write_text(content)
            git(repo, "init", "-q", "-b", "master")
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "theirs")
            self.assertEqual(slipwai(repo, "adopt", "--yes", "--forge", "gitea").returncode, 0)
            workflow = repo / ".github/workflows/verify-delivery.yml"
            self.assertIn("branches: [master]", workflow.read_text())
            self.assertEqual(json.loads((repo / "project.json").read_text())["ci"]["branch"], "master")
            # Taking the workflow over: its line leaves `.written`, the person edits it, and the survey respects both.
            listing = repo / "delivery/.written"
            listing.write_text(listing.read_text().replace(".github/workflows/verify-delivery.yml\n", ""))
            workflow.write_text(workflow.read_text() + "      - run: echo theirs\n")
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-qm", "the workflow is ours now")
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertIn("owned: `.github/workflows/verify-delivery.yml` — not in .written, so it is yours",
                          refreshed.stdout)
            self.assertIn("- run: echo theirs", workflow.read_text(), "left alone")
            self.assertNotIn(".github/workflows/verify-delivery.yml", listing.read_text(), "and not re-listed")

    def test_the_forge_stands_while_the_gate_is_the_only_ci_in_the_tree(self) -> None:
        """The survey leaves out what the factory wrote, so once the repository's own workflow is gone a fresh
        reading says `none` — and a detected forge walked to `none`, deleted the gate, and walked back when a
        workflow appeared. The gate is CI configuration in the tree: the forge it was written for stands."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps({"name": "shop", "private": True, "scripts": {"test": "node --test"}}),
                "test/a.test.js": 'require("node:test")("a", () => {});\n',
                ".github/workflows/ci.yml": "on: push\njobs:\n  test:\n    steps: []\n",
            })
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual((document["ci"]["forge"], document["ci"]["provenance"]), ("github", "detected"))
            (repo / ".github/workflows/ci.yml").unlink()
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-qm", "their CI retired")
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertNotIn("forge refreshed to `none`", refreshed.stdout)
            self.assertNotIn("removed:", refreshed.stdout)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["ci"]["forge"], "github")
            self.assertEqual(document["ci"]["evidence"],
                             "the delivery gate this factory wrote, .github/workflows/verify-delivery.yml")
            self.assertTrue((repo / ".github/workflows/verify-delivery.yml").is_file())
            self.assertNotIn("no CI configuration in the tree", (repo / "delivery/docs/adoption.md").read_text())

    def test_a_recorded_command_that_names_the_repositorys_own_scripts_is_not_repointed(self) -> None:
        """`Layout.repoint` respelled every `scripts/` in every assembled file, the person's recorded command
        included, so a repository-owned `scripts/check-secrets.py` reached `project.json` and the Makefile as
        `delivery/scripts/check-secrets.py`, which the gate then ran and could not find."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "shop", {
                "package.json": json.dumps({"name": "shop", "private": True, "scripts": {"test": "node --test"}}),
                "test/a.test.js": 'require("node:test")("a", () => {});\n',
                "scripts/check-secrets.py": "import sys\nsys.exit(0)\n",
            })
            adopted = slipwai(repo, "adopt", "--yes", "--command", "shop:lint=python3 scripts/check-secrets.py")
            self.assertEqual(adopted.returncode, 0, adopted.stderr)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["deployables"]["shop"]["commands"]["lint"], "python3 scripts/check-secrets.py")
            makefile = (repo / "delivery/Makefile").read_text()
            self.assertIn("python3 delivery/scripts/ratchet.py shop lint -- 'python3 scripts/check-secrets.py'",
                          makefile)
            page = (repo / "delivery/docs/adoption.md").read_text()
            self.assertIn("| `lint` | `python3 scripts/check-secrets.py` |", page)
            clean = {key: value for key, value in os.environ.items() if key not in ("CI", "RATCHET_TIGHTEN")}
            linted = subprocess.run(["make", "-f", "delivery/Makefile", "lint"], cwd=repo, text=True,
                                    capture_output=True, env=clean)
            self.assertEqual(linted.returncode, 0, linted.stdout + linted.stderr)
