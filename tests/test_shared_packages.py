"""Shared packages under `packages/`: what builds them, when, and what a project needs for them to work.

The failure this exists for happened downstream: a project grew a shared workspace package, `packages/` was
built by nothing, and the browser app's build failed on `Cannot find module` — in the staging deploy, after
both applies, with the environment already changed and no release recorded. Two halves are proved here. The
first is `scripts/deploy.py`, which builds the packages the site imports before it builds the site; it is
imported from a generated project and driven with its `run` replaced, so what is asserted is the sequence of
commands a deploy would issue rather than the text of the script. The second is the generated `Makefile` and
the manifests around it: the target that builds them, the targets that take it as a prerequisite, and the
workspace entry without which `npm --workspace packages/<name>` resolves nothing.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from support import FactoryTestCase
from test_add_service import add_service

from slipwai.catalog import axis_default


def deploy_script(repo: Path) -> tuple[Any, list[list[str]]]:
    """A generated project's `scripts/deploy.py`, imported, with every command it runs recorded instead.

    Imported from the project rather than from `assets/`, so its own `ROOT` — `parents[1]` of the script —
    is that project, and the discovery below reads that project's `project.json` and `packages/`.
    """
    path = repo / "scripts/deploy.py"
    specification = importlib.util.spec_from_file_location(f"deploy_{repo.name}", path)
    assert specification is not None and specification.loader is not None
    # `Any` because it is a script loaded by path: its verbs are what this asserts about, and there is
    # no stub for them to be checked against.
    module: Any = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    recorded: list[list[str]] = []

    def record(command: list[str], **_: object) -> str:
        recorded.append(command)
        return ""

    module.run = record
    # `npm` is on the deploy runner's PATH, not necessarily on this one's; what it is asked to do is the
    # subject here, and the check that it exists at all has its own line in the script.
    module.which = lambda tool: None
    return module, recorded


def shared_package(repo: Path, name: str, *, builds: bool) -> None:
    """A shared package in the project, as somebody adding one would write it: a manifest with or without
    the build script that says it emits something."""
    directory = repo / "packages" / name
    directory.mkdir(parents=True)
    manifest: dict = {"name": f"@project/{name}", "version": "0.1.0", "private": True}
    if builds:
        manifest["scripts"] = {"build": "tsc -p tsconfig.json"}
    (directory / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")


class SharedPackageDeployTest(FactoryTestCase):
    def generate_aws(self, directory: str, name: str, frontend: str = "react-vite"):
        return self.generate(
            directory, name, "event-modelling", "typescript", frontend, target="aws",
            event_store="postgres", http=axis_default("http", "typescript", "aws"),
        )

    def test_every_shared_package_is_built_before_the_app_that_imports_it(self) -> None:
        """The whole defect: the browser app imports declarations a package under `packages/` emits, that
        package's `dist/` is not committed, and a fresh CI checkout therefore has none of it."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "shared")
            shared_package(repo, "geo", builds=True)
            shared_package(repo, "money", builds=True)
            module, recorded = deploy_script(repo)

            module.upload_site({"web_bucket": "site-bucket"}, "abc123", {})

            commands = [" ".join(command) for command in recorded]
            built = commands.index("npm --workspace apps/web run build")
            for package in ("packages/geo", "packages/money"):
                self.assertIn(f"npm --workspace {package} run build", commands)
                self.assertLess(
                    commands.index(f"npm --workspace {package} run build"), built,
                    f"{package} is built after the app that imports it",
                )

    def test_the_install_that_creates_the_workspace_links_still_comes_first(self) -> None:
        """`npm --workspace <path>` resolves through the links `npm ci` writes into `node_modules`. A
        package built before the install is a package built out of a tree that has no dependencies yet."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "installed")
            shared_package(repo, "geo", builds=True)
            module, recorded = deploy_script(repo)

            module.upload_site({"web_bucket": "site-bucket"}, "abc123", {})

            commands = [" ".join(command) for command in recorded]
            builds = [
                position for position, command in enumerate(commands)
                if command.startswith("npm --workspace ") and command.endswith(" run build")
            ]
            self.assertEqual(commands[0], "npm ci")
            self.assertTrue(builds, "the site was never built")
            self.assertLess(0, min(builds), "something is built before the install that links the workspace")

    def test_a_project_with_no_packages_directory_asks_for_nothing(self) -> None:
        """Discovery, not a list: a project that has deleted the directory outright builds nothing rather
        than failing on a path that is not there."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "bare")
            module, recorded = deploy_script(repo)
            # The typed client is the one package a project starts with, and it declares a build: it is
            # generated from the service's published document, so a deploy that skipped it would ship a
            # bundle compiled against types nothing wrote.
            self.assertEqual(module.shared_packages(), ["packages/api-client"])

            shutil.rmtree(repo / "packages")
            self.assertEqual(module.shared_packages(), [])

            module.upload_site({"web_bucket": "site-bucket"}, "abc123", {})
            self.assertEqual(
                [" ".join(command) for command in recorded][:2],
                ["npm ci", "npm --workspace apps/web run build"],
            )

    def test_a_package_that_declares_no_build_is_left_alone(self) -> None:
        """A shared package can be plain source its consumers compile themselves. Nothing to build is not
        the same as nothing to install, and running `npm run build` on it would fail the deploy."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "mixed")
            shared_package(repo, "geo", builds=True)
            shared_package(repo, "types-only", builds=False)
            module, recorded = deploy_script(repo)

            self.assertEqual(module.shared_packages(), ["packages/api-client", "packages/geo"])

            module.upload_site({"web_bucket": "site-bucket"}, "abc123", {})
            self.assertNotIn(
                "npm --workspace packages/types-only run build", [" ".join(c) for c in recorded]
            )

    def test_a_project_with_no_browser_app_uploads_nothing_and_builds_nothing(self) -> None:
        """`upload_site` returns before any of this when there is no site to upload."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate_aws(directory, "headless", frontend="none")
            shared_package(repo, "geo", builds=True)
            module, recorded = deploy_script(repo)

            module.upload_site({}, "abc123", {})
            self.assertEqual(recorded, [])


class SharedPackageProjectTest(FactoryTestCase):
    def prerequisite_line(self, makefile: str) -> list[str]:
        """The targets the Makefile declares as needing `build-packages`."""
        line = next(
            (
                row for row in makefile.splitlines()
                if row.endswith(": build-packages") and not row.startswith(".PHONY")
            ),
            None,
        )
        self.assertIsNotNone(line, "the Makefile declares no target as needing build-packages")
        assert line is not None
        return line.split(":")[0].split()

    def test_everything_that_compiles_this_project_needs_the_shared_packages_built(self) -> None:
        """Declared as a prerequisite in one line rather than as a step inside each recipe. A step is
        forgotten in one target eventually, and that target then passes wherever `dist/` happens to exist
        and fails on a fresh checkout — which is how the omission was found."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "gated", "event-modelling", "typescript", "react-vite", target="aws",
                event_store="postgres", http=axis_default("http", "typescript", "aws"),
            )
            makefile = (repo / "Makefile").read_text()
            self.assertIn("\nbuild-packages: node_modules/.package-lock.json ##", makefile)

            needed = self.prerequisite_line(makefile)
            self.assertEqual(
                [
                    # `format` beside `lint`: it runs Biome out of the same installed `node_modules`.
                    "typecheck", "lint", "format", "test", "test-integration", "adversarial", "dev",
                    "dev-web",
                    # The image build, per service rather than the `build` aggregate: `build` already has
                    # `build-service` as a prerequisite, and one appended after it would run too late.
                    "build-service",
                ],
                needed,
            )
            # Every one of them is a target this project actually has: a name that has drifted would
            # otherwise sit there defining an empty target nobody notices.
            for target in needed:
                self.assertRegex(makefile, rf"(?m)^{target}:", f"{target} takes a prerequisite but is not a target")

    def integration_job_targets(self, repo: Path) -> list[str]:
        """The targets the generated CI integration job runs, read out of the workflow it runs them from.

        Read rather than restated, so this cannot pass while the job the failure happened in runs something
        else.
        """
        workflow = (repo / ".github/workflows/verify.yml").read_text()
        job = workflow.split("\n  integration:\n", 1)
        self.assertEqual(len(job), 2, "the project generated no integration job to check")
        self.assertIn("    container: ", job[1].split("\n    steps:", 1)[0], "the job takes no container")
        run = next(
            (row for row in job[1].splitlines() if row.strip().startswith("- run: make ")), None
        )
        self.assertIsNotNone(run, "the integration job runs no make target")
        assert run is not None
        return run.split("- run: make ", 1)[1].split()

    def test_a_native_services_integration_job_is_never_sent_looking_for_npm(self) -> None:
        """The downstream failure, exactly: a Go service beside a React app has an npm workspace, so
        `build-packages` exists — and it was made a prerequisite of `test-integration` too, whose CI job runs
        inside `golang:1.26-bookworm`. That image ships no node, so the job died on `npm: command not found`
        before a test ran, while `verify` (which sets Node up) passed. A `packages/` entry is importable by
        TypeScript and by nothing else, so a native service's own targets cannot need one built.

        Asserted by asking Make what it would do, over the targets the workflow itself names, rather than by
        matching the prerequisite line: what broke was the whole prerequisite chain, not one line of it.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "native-integration", "event-modelling", "go", "react-vite", target="aws",
                event_store="postgres", http=axis_default("http", "go", "aws"),
            )
            self.assertIn("build-packages", (repo / "Makefile").read_text(), "no npm workspace to guard")

            targets = self.integration_job_targets(repo)
            self.assertIn("test-integration", targets)
            plan = subprocess.run(
                ["make", "-n", *targets], cwd=repo, text=True, capture_output=True, check=True,
            )
            self.assertNotIn("npm", plan.stdout, "the integration job would run npm inside a node-less image")

            # Only the service's own targets lose it. The browser app's still needs its packages built.
            needed = self.prerequisite_line((repo / "Makefile").read_text())
            self.assertEqual(["typecheck", "lint", "format", "test", "adversarial", "dev-web"], needed)

    def test_each_native_family_keeps_its_own_integration_job_clear_of_npm(self) -> None:
        """One image per family, none of them Node's: whichever native backend is beside a browser app, its
        integration job is a job that cannot run npm."""
        for language in ("python", "java-spring"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                repo = self.generate(
                    directory, f"{language}-integration", "event-modelling", language, "react-vite",
                    target="aws", event_store="postgres",
                    http=axis_default("http", language, "aws"),
                )
                plan = subprocess.run(
                    ["make", "-n", *self.integration_job_targets(repo)],
                    cwd=repo, text=True, capture_output=True, check=True,
                )
                self.assertNotIn("npm", plan.stdout)

    def test_two_families_get_one_job_each_and_only_the_npm_one_builds_the_packages(self) -> None:
        """A TypeScript service and a Go one in the same repository: one integration job per family, each in
        its own image. The Node job's targets do build the packages — that is the whole point of the
        prerequisite — and the Go job's do not."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "two", "event-modelling", "typescript", "react-vite", target="aws",
                event_store="postgres", http="fastify",
            )
            added = add_service(
                repo, "payments", "--backend", "go", "--http", "net-http", "--event-store", "postgres",
            )
            self.assertEqual(added.returncode, 0, added.stderr)

            workflow = (repo / ".github/workflows/verify.yml").read_text()
            for job, image, expected in (
                ("integration-typescript", "node:24-bookworm", True),
                ("integration-go", "golang:1.26-bookworm", False),
            ):
                with self.subTest(job=job):
                    section = workflow.split(f"\n  {job}:\n", 1)
                    self.assertEqual(len(section), 2, f"no {job} job")
                    self.assertIn(f"container: {image}", section[1])
                    targets = next(
                        row.split("- run: make ", 1)[1].split()
                        for row in section[1].splitlines() if row.strip().startswith("- run: make ")
                    )
                    plan = subprocess.run(
                        ["make", "-n", *targets], cwd=repo, text=True, capture_output=True, check=True,
                    )
                    self.assertEqual(expected, "npm" in plan.stdout, plan.stdout)

    def test_a_project_with_no_npm_workspace_is_given_none_of_it(self) -> None:
        """`build-packages` is the npm family's answer. A Go project with no browser app has no root
        manifest for `--workspace` to read, and a target running npm there would be a target that cannot run."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "native", "standard", "go", "none")
            makefile = (repo / "Makefile").read_text()
            self.assertNotIn("build-packages", makefile)
            self.assertFalse((repo / "package.json").exists())
            self.assertNotIn("packages/*/dist/", (repo / ".gitignore").read_text())

    def test_the_workspace_holds_packages_whether_or_not_there_is_a_browser_app(self) -> None:
        """`docs/architecture.md` tells the reader the root `package.json` already lists `packages/*`. It
        did not, in exactly the projects that have a browser app to import one — and `npm --workspace
        packages/<name>` fails outright on a directory npm does not consider a workspace member."""
        with tempfile.TemporaryDirectory() as directory:
            for name, frontend in (("with-web", "react-vite"), ("without-web", "none")):
                with self.subTest(frontend=frontend):
                    repo = self.generate(directory, name, "event-modelling", "typescript", frontend)
                    manifest = json.loads((repo / "package.json").read_text())
                    self.assertIn("packages/*", manifest["workspaces"])
                    # `npm ci` refuses a lock whose root record disagrees with the manifest it was
                    # resolved from, so the lock carries the same list or no install runs at all.
                    lock = json.loads((repo / "package-lock.json").read_text())
                    self.assertEqual(manifest["workspaces"], lock["packages"][""]["workspaces"])
                    self.assertIn("packages/*/dist/", (repo / ".gitignore").read_text())

    def test_the_manifest_says_where_shared_code_lives_and_the_deploy_reads_it_there(self) -> None:
        """`scripts/deploy.py` discovers the packages through `project.json`'s `layout.packages` rather
        than assuming the directory, so the two cannot drift apart."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "recorded", "event-modelling", "typescript", "react-vite", target="aws",
                event_store="postgres", http=axis_default("http", "typescript", "aws"),
            )
            self.assertEqual(json.loads((repo / "project.json").read_text())["layout"]["packages"], "packages")
            self.assertIn('manifest().get("layout", {}).get("packages"', (repo / "scripts/deploy.py").read_text())
