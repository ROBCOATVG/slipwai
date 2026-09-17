"""`slipwai adopt`: the delivery method installed around a repository the factory did not make.

Experimental (`AGENTS.md` says what the word means here), which is why what is gated is the contract a
person relies on rather than the shape of any one file: nothing of the repository's own is written over, and
what it owes them is a marked block appended once; every fact in `project.json` says where it came from;
the gate runs their build's commands and is green on day one; the whole adoption is one commit by the factory
that `replay` reproduces tree for tree — the proof the manifest is a complete record of an adopted
repository too — and that a newer factory later merges over cleanly; and what cannot safely be done is refused
by name. The fixtures are real repositories the tests write, small enough to gate and shaped like the real thing.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_add_service import add_service
from test_migrate import migrate
from test_replay import NEWER, SKILL, git, newer_factory, replay

from slipwai.assets import ROOT, VERSION
from slipwai.ecosystems import TARGETS

OWN = {
    "README.md": "# Shop\n\nA shop.\n",
    "Makefile": "all:\n\t@echo theirs\n",
    ".gitignore": "node_modules/\n",
    "AGENTS.md": "# Agents\n\nBe careful.\n",
}


def slipwai(repo: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(ROOT / "slipwai"), *arguments], cwd=repo, text=True, capture_output=True, stdin=subprocess.DEVNULL
    )


def repository(parent: Path, name: str, files: dict[str, str]) -> Path:
    """A Git repository with one commit of `files`, the way a repository this factory did not make arrives."""
    repo = parent / name
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "theirs")
    return repo


def node_repository(parent: Path) -> Path:
    """A JavaScript service with its own tests, README, Makefile and agent guidance — and no lockfile, so its
    install needs no registry."""
    return repository(parent, "shop", {
        **OWN,
        "package.json": json.dumps({
            "name": "shop", "private": True,
            "scripts": {"test": "node --test", "lint": "node -e \"process.exit(0)\""},
            "dependencies": {"pg": "^8"},
        }),
        ".nvmrc": "20\n",
        # Their CI, on GitHub Actions: what makes the gate an Actions workflow beside it.
        ".github/workflows/ci.yml": "on: push\njobs: {}\n",
        "src/add.js": "exports.add = (a, b) => a + b;\n",
        "test/add.test.js": (
            'const t = require("node:test"); const a = require("node:assert");\n'
            'const { add } = require("../src/add.js");\nt("adds", () => a.equal(add(1, 2), 3));\n'
        ),
    })


def listed_tree(repo: Path, revision: str = "HEAD") -> dict[str, str]:
    """Every blob in a commit's tree, path to object id — what two commits are compared on."""
    lines = git(repo, "ls-tree", "-r", revision).stdout.splitlines()
    return {line.split("\t", 1)[1]: line.split()[2] for line in lines}


class AdoptTest(FactoryTestCase):
    def test_adopting_a_repository_installs_the_method_beside_its_own_files_and_the_gate_holds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = node_repository(Path(directory))
            before = git(repo, "rev-parse", "HEAD").stdout.strip()

            result = slipwai(repo, "adopt", "--yes", "--why", "EOL runtime", "--purpose", "shop=Sells things.")

            self.assertEqual(result.returncode, 0, result.stderr)
            first, *rest = result.stdout.splitlines()
            self.assertTrue(first.startswith(f"adopted shop with slipwai {VERSION}"), first)
            self.assertIn("experimental", first)
            # `init` first, as a generated project's README has it; the gate after, spelled for a root Makefile
            # of the repository's own.
            self.assertIn("Next: ./delivery/init — installs Spec Kit", result.stdout)
            self.assertIn("Then: make -f delivery/Makefile verify", result.stdout)
            # One commit by the factory, on top of theirs, and nothing left uncommitted.
            self.assertEqual(git(repo, "log", "--format=%ae", "-1").stdout.strip(), "factory@local")
            self.assertEqual(git(repo, "rev-parse", "HEAD^").stdout.strip(), before)
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")
            # Their files: two untouched, two with a marked block appended after their own text.
            for own in ("README.md", "Makefile"):
                self.assertEqual((repo / own).read_text(), OWN[own], own)
            agents = (repo / "AGENTS.md").read_text()
            self.assertTrue(agents.startswith(OWN["AGENTS.md"]))
            self.assertIn("<!-- extension:delivery:begin -->", agents)
            self.assertIn("delivery/docs/adoption.md", agents)
            # The rule every stage reads: fakes over a mocking framework, and the current test framework over the
            # next-oldest one, for new code and old alike.
            self.assertIn("never with a mocking framework", agents)
            self.assertIn("Mockito, Moq, gomock", agents)
            self.assertIn("JUnit 5 through its vintage engine", agents)
            ignore = (repo / ".gitignore").read_text()
            self.assertTrue(ignore.startswith(OWN[".gitignore"]))
            self.assertIn("# slipwai:delivery:begin", ignore)
            self.assertIn(".slipwai/catch-up.md\n", ignore)
            self.assertNotIn(".slipwai/\n", ignore)
            self.assertFalse((repo / ".github/workflows/verify.yml").exists(), "their CI's name is not claimed")
            self.assertFalse((repo / "apps").exists(), "nothing is scaffolded")

            # The manifest: what was there, and where each fact came from.
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["origin"], "adopted")
            self.assertEqual(document["layout"]["delivery"], "delivery")
            self.assertEqual(document["why"], "EOL runtime")
            shop = document["deployables"]["shop"]
            self.assertEqual((shop["generated"], shop["path"], shop["language"]), (False, ".", "javascript"))
            self.assertEqual(tuple(shop["commands"]), TARGETS)
            self.assertEqual(shop["commands"]["test"], "npm run test")
            self.assertIsNone(shop["commands"]["typecheck"])
            self.assertEqual(shop["toolchain"], {"kind": "node", "version": "20", "ecosystem": "node"})
            # No Dockerfile, no start script: what `shop` is for is not established, and the record says exactly that
            # rather than calling it a service.
            self.assertEqual(shop["kind"], "application")
            self.assertEqual(
                shop["provenance"],
                {"language": "detected", "commands": "detected", "kind": "unrecorded", "purpose": "overridden"},
            )
            self.assertEqual(document["database"]["schema"], "unmanaged")
            self.assertEqual(document["database"]["drivers"], ["pg"])
            self.assertEqual(document["infrastructure"]["home"], "unmanaged")
            self.assertEqual(document["survey"]["makefile"], True)
            self.assertEqual(document["ci"], {
                "forge": "github", "gate": ".github/workflows/verify-delivery.yml", "branch": "main",
                "evidence": ".github/workflows",
                "provenance": "detected",
            })
            # Nothing in the tree says how a change reaches production, so nothing is claimed: unknown, unrecorded.
            self.assertEqual(document["release"], {"path": "unknown", "evidence": [], "provenance": "unrecorded"})
            self.assertIn("How a change reaches production: not recorded", result.stdout)

            # What the factory wrote is listed, exactly, so a later factory knows what is its to replace.
            written = set((repo / "delivery/.written").read_text().splitlines())
            changed = set(git(repo, "diff", "--name-only", "HEAD^", "HEAD").stdout.splitlines())
            appended = {
                "AGENTS.md", ".gitignore", ".claude/settings.json", "delivery/survey/survey.md",
                "delivery/survey/structure.md", "delivery/survey/pinned.md", "delivery/survey/running.md",
                "delivery/retirement.md",
            }
            self.assertEqual(written, changed - appended)
            self.assertIn("delivery/.written", written)
            workflow = (repo / ".github/workflows/verify-delivery.yml").read_text()
            self.assertIn("actions/setup-node@v6", workflow)
            self.assertIn("node-version: '20'", workflow)
            self.assertIn("run: make -f delivery/Makefile verify", workflow)
            page = (repo / "delivery/docs/adoption.md").read_text()
            self.assertTrue(page.startswith("# How the delivery method was installed here\n\n> **Experimental.**"))
            self.assertIn("not a language this factory generates", page)
            self.assertIn("| `test` | `npm run test` |", page)
            self.assertIn("## Builds", (repo / "delivery/survey/survey.md").read_text())

            # Green on day one, with their commands and the method's checks.
            verified = subprocess.run(
                ["make", "-f", "delivery/Makefile", "verify"], cwd=repo, text=True, capture_output=True
            )
            self.assertEqual(verified.returncode, 0, verified.stdout[-3000:] + verified.stderr[-3000:])
            self.assertIn("npm run test", verified.stdout)
            self.assertIn("shop: no typecheck command recorded", verified.stdout)
            self.assertIn("verify: all gates passed", verified.stdout)

            # The manifest is a complete record: the same factory replays the same tree over theirs.
            replayed = replay(repo)
            self.assertEqual(replayed.returncode, 0, replayed.stderr)
            twin = Path(directory) / f"shop-at-{VERSION}"
            self.assertEqual(listed_tree(twin), listed_tree(repo))
            base = git(repo, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(git(twin, "rev-parse", "HEAD^").stdout.strip(), base)

            # Adopting again is not a refresh; `migrate` is.
            again = slipwai(repo, "adopt", "--yes")
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("already has a project.json", again.stderr)
            self.assertIn("slipwai migrate", again.stderr)

    def test_an_adopted_repository_grows_and_takes_a_newer_factory_as_one_clean_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = node_repository(Path(directory))
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)

            grown = add_service(repo, "payments", "--language", "python", "--purpose", "Takes payment.")
            self.assertEqual(grown.returncode, 0, grown.stderr)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["origin"], "adopted")
            self.assertEqual(list(document["deployables"]), ["shop", "payments"])
            self.assertTrue((repo / "apps/payments").is_dir())
            self.assertIn("apps/payments", (repo / "delivery/Makefile").read_text())
            self.assertFalse((repo / "Makefile").read_text() != OWN["Makefile"], "their Makefile is still theirs")
            self.assertFalse((repo / ".github/workflows/verify.yml").exists())
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "payments")

            factory = newer_factory(Path(directory), "\n\nA newer factory's sentence.\n")
            migrated = migrate(repo, factory)
            self.assertEqual(migrated.returncode, 0, migrated.stderr)
            self.assertIn(f"migrated shop from {VERSION} to slipwai {NEWER}", migrated.stdout)
            self.assertIn("A newer factory's sentence.", (repo / "delivery" / SKILL).read_text())
            self.assertEqual((repo / "README.md").read_text(), OWN["README.md"])
            self.assertEqual((repo / "Makefile").read_text(), OWN["Makefile"])
            self.assertTrue((repo / "src/add.js").is_file() and (repo / "apps/payments").is_dir())
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")
            self.assertEqual(json.loads((repo / "project.json").read_text())["generator"]["updatedWith"], NEWER)

    def test_a_repository_without_a_makefile_gets_one_that_makes_verify_one_word(self) -> None:
        """Where there is no root Makefile there is nothing of theirs to clash with, so `adopt` writes one that
        includes the delivery Makefile in a marked block — theirs from then on, not the factory's to replace."""
        with tempfile.TemporaryDirectory() as directory:
            repo = node_repository(Path(directory))
            (repo / "Makefile").unlink()
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "no makefile")
            result = slipwai(repo, "adopt", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Wrote Makefile with `-include delivery/Makefile`, since there was none", result.stdout)
            self.assertNotIn("Then: add `-include", result.stdout)
            self.assertIn("Next: ./delivery/init — installs Spec Kit", result.stdout)
            self.assertIn("Then: make verify — the gate", result.stdout)
            self.assertIn("Appended a marked block to AGENTS.md and .gitignore", result.stdout)
            makefile = (repo / "Makefile").read_text()
            self.assertTrue(makefile.startswith("# slipwai:delivery:begin"), makefile)
            self.assertIn("\n-include delivery/Makefile\n", makefile)
            self.assertNotIn("Makefile", (repo / "delivery/.written").read_text().splitlines())
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")
            self.assertFalse(json.loads((repo / "project.json").read_text())["survey"]["makefile"])
            page = (repo / "delivery/docs/adoption.md").read_text()
            self.assertIn("the repository had no `Makefile`, so `adopt` wrote one", page)

            one_word = subprocess.run(["make", "verify"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(one_word.returncode, 0, one_word.stdout[-2000:] + one_word.stderr[-2000:])
            self.assertIn("verify: all gates passed", one_word.stdout)

    def test_flags_override_the_survey_and_the_record_says_so(self) -> None:
        """A .NET repository, in a language the factory cannot generate and with no toolchain here to run it:
        what is recorded is what the flags said, marked `overridden`, and the workflow sets up its runtime."""
        with tempfile.TemporaryDirectory() as directory:
            repo = repository(Path(directory), "ledger", {
                "Ledger.csproj": (
                    '<Project Sdk="Microsoft.NET.Sdk.Web"><PropertyGroup><TargetFramework>net8.0</TargetFramework>'
                    "</PropertyGroup></Project>"
                ),
                "Program.cs": "// hello\n",
                # Their CI is GitLab's, and a deploy job in it says how a change reaches production.
                ".gitlab-ci.yml": "stages: [test, deploy]\ndeploy:\n  stage: deploy\n  script: [./deploy.sh]\n",
            })
            result = slipwai(
                repo, "adopt", "--yes", "--command", "ledger:test=-",
                "--command", "ledger:lint=dotnet format --verify-no-changes", "--language", "ledger=csharp",
                "--database", "elsewhere", "--database-repository", "https://x/schema.git", "--infrastructure", "none",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads((repo / "project.json").read_text())
            ledger = document["deployables"]["ledger"]
            self.assertIsNone(ledger["commands"]["test"])
            self.assertEqual(ledger["commands"]["lint"], "dotnet format --verify-no-changes")
            self.assertEqual(ledger["commands"]["typecheck"], "dotnet build Ledger.csproj --no-restore")
            self.assertEqual(
                ledger["provenance"], {"language": "overridden", "commands": "overridden", "kind": "detected"}
            )
            self.assertEqual(ledger["kind"], "service", "Microsoft.NET.Sdk.Web is a service, and the csproj said so")
            self.assertEqual(ledger["toolchain"]["version"], "8.0")
            self.assertEqual(document["database"], {
                "schema": "elsewhere", "tools": [], "drivers": [], "repository": "https://x/schema.git",
                "provenance": "overridden",
            })
            self.assertEqual(document["infrastructure"]["home"], "none")
            self.assertEqual(document["infrastructure"]["provenance"], "overridden")
            # GitLab runs their CI, so no GitHub workflow is written: the gate is a job to include, and — .NET having no
            # official image that carries `make` — the image is a line to fill, said in place.
            self.assertFalse((repo / ".github").exists(), "no Actions workflow into a GitLab repository")
            self.assertEqual(document["ci"]["forge"], "gitlab")
            self.assertEqual(document["ci"]["gate"], "delivery/ci/verify-delivery.gitlab-ci.yml")
            job = (repo / "delivery/ci/verify-delivery.gitlab-ci.yml").read_text()
            self.assertIn("- local: delivery/ci/verify-delivery.gitlab-ci.yml", job)
            self.assertIn("# image: choose one that carries `make` and dotnet 8.0", job)
            self.assertIn("- make -f delivery/Makefile verify", job)
            self.assertIn("delivery/ci/verify-delivery.gitlab-ci.yml", (repo / "delivery/.written").read_text())
            self.assertEqual(document["release"], {
                "path": "pipeline", "evidence": ["pipeline: .gitlab-ci.yml"], "provenance": "detected",
            })
            self.assertIn("add `include: [local: delivery/ci/verify-delivery.gitlab-ci.yml]`", result.stdout)
            page = (repo / "delivery/docs/adoption.md").read_text()
            self.assertIn("owned by another repository, `https://x/schema.git`", page)
            self.assertIn("csharp` is not a language this factory generates", page)
            self.assertIn("**A pipeline deploys** (`detected`, from `pipeline: .gitlab-ci.yml`)", page)
            self.assertIn("as the GitLab job in `delivery/ci/verify-delivery.gitlab-ci.yml`", page)

    def test_what_cannot_safely_be_adopted_is_refused_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bare = Path(directory) / "bare"
            bare.mkdir()
            (bare / "package.json").write_text("{}")
            refused = slipwai(bare, "adopt", "--yes")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("not a Git repository", refused.stderr)
            self.assertIn("git init", refused.stderr)
            self.assertFalse((bare / "project.json").exists())

            repo = node_repository(Path(directory))
            (repo / "notes.txt").write_text("wip\n")
            dirty = slipwai(repo, "adopt", "--yes")
            self.assertNotEqual(dirty.returncode, 0)
            self.assertIn("uncommitted changes", dirty.stderr)
            (repo / "notes.txt").unlink()

            silent = slipwai(repo, "adopt")
            self.assertNotEqual(silent.returncode, 0)
            self.assertIn("pass --yes", silent.stderr)
            self.assertFalse((repo / "project.json").exists(), "a refusal leaves nothing behind")
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")

            # Nothing the survey can read builds here: said by name, with what it does read, and before any question
            # is asked — where it used to be an IndexError from the first command template.
            prose = repository(Path(directory), "prose", {"README.md": "# Notes\n", "hms.sql": "create table t;\n"})
            nothing = slipwai(prose, "adopt")
            self.assertNotEqual(nothing.returncode, 0)
            self.assertIn("nothing here starts a build the survey can read", nothing.stderr)
            self.assertIn("build.xml", nothing.stderr)
            self.assertNotIn("Traceback", nothing.stderr)
            self.assertFalse((prose / "project.json").exists())
            skipped = slipwai(repo, "adopt", "--yes", "--skip", "shop")
            self.assertNotEqual(skipped.returncode, 0)
            self.assertIn("nothing is left to install around", skipped.stderr)
