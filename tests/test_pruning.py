"""Pruning is one implementation, shared with the generated project, and it refuses to orphan an adapter."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import (
    BACKING_SERVICE_ROOT,
    PRUNER,
    ROOT,
)
from slipwai.catalog import CATALOG, axis_options
from slipwai.project.languages.typescript import service_package_json
from slipwai.selection import Selection


class PruningTest(FactoryTestCase):
    def test_no_generated_file_carries_a_marker_the_pruner_never_visits(self) -> None:
        """A marked region in an unlisted file is silently never pruned, so the list is asserted.

        `MARKED_FILES` is a list of paths, globbed the way `owned_paths` globs its own. Its comment says
        what happens when a file is missing from it: nothing, quietly. The region survives the prune, and
        the feature reads as still present in a project that no longer has it — which is the worst shape a
        bug in a prune can take, because `--list` then offers an answer that cannot be given.

        Nothing is missing today. This exists so that the next marked region added to a shared file, in any
        backend, cannot be missing either — and so that a backend whose paths carry a project-derived
        directory name (a Python package, a Java package) finds out here rather than in a generated repo.
        """
        marker = re.compile(r"backing-service:([a-z0-9-]+):(begin|end)")
        with tempfile.TemporaryDirectory() as directory:
            for backend in CATALOG["backends"]:
                transports = [
                    option for option in axis_options("http", backend, "none") if option != "none"
                ]
                stores = [
                    option
                    for option in axis_options("event-store", backend, "none")
                    if option not in ("memory", "none")
                ]
                if not transports or not stores:
                    continue
                # The maximal selection, with the frontend: every axis answered contributes markers, and
                # `apps/web/vite.config.ts` is the one marked file that arrives with the frontend instead.
                repo = self.generate(
                    directory,
                    f"markers-{backend}",
                    "event-modelling",
                    backend,
                    "react-vite",
                    event_store=stores[-1],
                    http=transports[0],
                    auth="keycloak",
                    users="keycloak",
                )
                # Resolved rather than listed by name: a Python service's entry point is inside a package
                # directory named after the project, so its row in the table can only be a pattern.
                listed = {
                    path.relative_to(repo).as_posix()
                    for path in PRUNER.marked_paths(
                        repo, PRUNER.project_services(repo), PRUNER.project_web_apps(repo)
                    )
                }
                unlisted = []
                for path in sorted(repo.rglob("*")):
                    if not path.is_file() or ".git/" in path.as_posix():
                        continue
                    try:
                        text = path.read_text()
                    except (UnicodeDecodeError, OSError):
                        continue
                    relative = path.relative_to(repo).as_posix()
                    if marker.search(text) and relative not in listed:
                        unlisted.append(relative)
                self.assertEqual(
                    [],
                    unlisted,
                    f"{backend}: these files carry a backing-service marker that no prune will ever "
                    f"reach; add each to MARKED_FILES or MARKED_FILES_BY_LANGUAGE in "
                    f"assets/backing-services/prune.py:\n  " + "\n  ".join(unlisted),
                )

    def test_the_pruner_is_one_implementation_shared_with_the_generated_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "shared-pruner", event_store="postgres")
            self.assertEqual(
                (repo / "scripts/backing-services.py").read_text(),
                (BACKING_SERVICE_ROOT / "prune.py").read_text(),
                "the emitted prune script must be the same file the factory imports",
            )

        # What generation adds and what the prune removes are two halves of one fact, per feature. A
        # dependency added here and not named there is a dependency a pruned project keeps forever.
        base = json.loads((ROOT / "assets/languages/typescript/app/package.json").read_text())
        for axis, answer, feature in (
            ("event-store", "postgres", "postgres"),
            ("http", "fastify", "fastify"),
        ):
            added = json.loads(
                service_package_json(
                    (ROOT / "assets/languages/typescript/app/package.json").read_text(),
                    Selection({axis: answer}),
                )
            )
            edits = PRUNER.PACKAGE_EDITS["typescript"][feature]
            installed = {**added.get("dependencies", {}), **added["devDependencies"]}
            self.assertEqual(
                set(edits["packages"]),
                set(installed) - set(base["devDependencies"]) - set(base.get("dependencies", {})),
                feature,
            )
            self.assertEqual(
                set(edits["scripts"]), set(added["scripts"]) - set(base["scripts"]), feature
            )

        # Every file a marked region can live in has to be declared, or a region there is never pruned.
        for relative in PRUNER.MARKED_FILES:
            self.assertIsInstance(relative, str)
        self.assertIn("Makefile", PRUNER.MARKED_FILES)
        self.assertIn("docker-compose.yml", PRUNER.MARKED_FILES)

    def test_the_pruner_refuses_to_orphan_an_adapter_it_would_leave_behind(self) -> None:
        """Dropping the transport while the identity provider stays is the combination the factory
        refuses at generation time, so the prune has to refuse it for the same reason."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "orphan", event_store="memory", http="fastify", auth="keycloak"
            )
            script = ["python3", "scripts/backing-services.py"]

            refused = subprocess.run(
                script + ["--http", "none"], cwd=repo, text=True, stderr=subprocess.PIPE
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("no http to reach it", refused.stderr)
            # Nothing was announced and nothing was removed.
            self.assertTrue((repo / "apps/service/src/adapters/driving/http/app.ts").is_file())
            self.assertTrue(
                (repo / "apps/service/src/adapters/driving/http/auth/oidc-keycloak.ts").is_file()
            )

            subprocess.run(
                script + ["--http", "none", "--auth", "none"],
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            self.assertFalse((repo / "apps/service/src/adapters/driving").exists())

    def test_answering_an_axis_again_through_init_rewrites_the_manifest_and_the_skills_follow(self) -> None:
        """`./init --auth none` leaves a project that reads as one generated with `--auth none`.

        The files were always pruned; the manifest was not, so `project.json` went on recording `keycloak`
        and the `auth-keycloak` capability it gives. That list is what decides which skills a project is
        handed, so `secure-oauth-oidc` — eleven thousand words about a login this project no longer has —
        stayed justified and `make check-agents` had nothing to say about it. `replay` and `migrate`
        regenerate from the same record, and would have put the adapter back.

        Driven through `./init` rather than the pruner directly, because the axis flags are `./init`'s own
        and lifted out of what is forwarded to Spec Kit, which is faked here so nothing reaches the network.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "re-answered", event_store="postgres", http="fastify",
                auth="keycloak", users="none",
            )
            born_without = self.generate(
                directory, "never-had-one", event_store="postgres", http="fastify",
                auth="none", users="none",
            )
            check = ["python3", "scripts/agents/project.py", "--check"]
            before = subprocess.run(check, cwd=repo, text=True, capture_output=True)
            self.assertEqual(before.returncode, 0, before.stderr)
            self.assertNotIn("secure-oauth-oidc", before.stdout)
            generator = json.loads((repo / "project.json").read_text())["generator"]

            fake_bin = Path(directory) / "fake-bin"
            fake_bin.mkdir()
            fake = fake_bin / "specify"
            fake.write_text(
                "#!/bin/sh\nmkdir -p .specify\n"
                "printf '%s\\n' "
                "'{\"installed_integrations\":[\"claude\"],\"default_integration\":\"claude\"}' "
                "> .specify/integration.json\n"
            )
            fake.chmod(0o755)
            environment = os.environ | {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

            subprocess.run(
                ["./init", "--auth", "none", "--integration", "claude"],
                cwd=repo, check=True, env=environment, stdout=subprocess.DEVNULL,
            )

            rewritten = json.loads((repo / "project.json").read_text())
            self.assertEqual(
                rewritten["deployables"],
                json.loads((born_without / "project.json").read_text())["deployables"],
                "a re-answered project must record what a generation with that answer would have",
            )
            # The answer moved; the version that wrote this repository did not. `./init` is the copy of the
            # factory `updatedWith` already names, so carrying it forward would have `migrate` skip the
            # catch-up notes this project still owes.
            self.assertEqual(rewritten["generator"], generator)

            told = subprocess.run(check, cwd=repo, text=True, capture_output=True)
            self.assertEqual(told.returncode, 0, told.stderr + told.stdout)
            self.assertIn("skills/secure-oauth-oidc serves", told.stdout)
