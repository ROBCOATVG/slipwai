"""Each axis is one question with one answer: asked on its own, refused on its own, answerable again later."""
from __future__ import annotations

import json
import subprocess
import tempfile

from support import FactoryTestCase

from slipwai.catalog import CATALOG, axis_default
from slipwai.selection import resolve_selection


class AxesTest(FactoryTestCase):
    def test_a_project_that_answers_nothing_carries_nothing(self) -> None:
        """The no-infrastructure answer is still a first-class one, on every axis: asked for it, a project
        has no container, no environment file, and nothing to prune. It is no longer what a bare `./slipwai generate`
        hands you, so it has to be reachable by answering."""
        with tempfile.TemporaryDirectory() as directory:
            for profile in CATALOG["profiles"]:
                repo = self.generate(
                    directory,
                    f"plain-{profile}",
                    profile,
                    "typescript",
                    event_store="memory",
                    http="none",
                    auth="none",
                )
                for absent in (
                    "docker-compose.yml",
                    ".env.example",
                    "docker",
                    "scripts/backing-services.py",
                    "apps/service/migrations",
                    "apps/service/vitest.integration.config.ts",
                    "apps/service/src/adapters/driving",
                ):
                    self.assertFalse((repo / absent).exists(), f"{profile}: {absent}")
                makefile = (repo / "Makefile").read_text()
                for absent in ("services-up:", "services-down:", "migrate:", "backing-service:"):
                    self.assertNotIn(absent, makefile, profile)
                self.assertNotIn(".env", (repo / ".gitignore").read_text())
                self.assertNotIn("backing-services", (repo / "init").read_text())
                self.assertNotIn("postgres", (repo / ".github/workflows/verify.yml").read_text())

                selection = json.loads((repo / "project.json").read_text())["deployables"]["service"]["selection"]
                if profile == "event-modelling":
                    # The event store is not optional for an event-sourced project — only *which* store is.
                    # The in-memory adapter and the contract it answers to arrive with the bare answer.
                    self.assertEqual(
                        selection, {"event-store": "memory", "http": "none", "auth": "none", "users": "none"}
                    )
                    for present in (
                        "apps/service/src/application/ports/events.ts",
                        "apps/service/src/adapters/driven/event-store-memory.ts",
                        "apps/service/tests/contract/event-store-contract.ts",
                        "apps/service/tests/contract/event-store-memory.test.ts",
                    ):
                        self.assertTrue((repo / present).is_file(), f"{profile}: {present}")
                else:
                    # No event store at all: the standard profile has no such port, so the axis
                    # is not a question it is asked.
                    self.assertEqual(selection, {"http": "none", "auth": "none", "users": "none"})
                    self.assertFalse((repo / "apps/service/src/adapters").exists(), profile)

    def test_each_axis_is_asked_and_answered_on_its_own(self) -> None:
        """The axes are independent: answering one must not move another.

        This is the property the old single `--backing-services` list could not express — Postgres and
        Keycloak answer unrelated questions, so choosing one has to leave the other alone.
        """
        with tempfile.TemporaryDirectory() as directory:
            store_only = self.generate(
                directory, "store-only", event_store="postgres", http="none", auth="none"
            )
            selection = json.loads((store_only / "project.json").read_text())["deployables"]["service"]["selection"]
            self.assertEqual(selection, {"event-store": "postgres", "http": "none", "auth": "none", "users": "none"})
            self.assertTrue((store_only / "docker-compose.yml").is_file())
            self.assertNotIn("keycloak", (store_only / "docker-compose.yml").read_text())
            self.assertFalse((store_only / "apps/service/src/adapters/driving").exists())

            transport_only = self.generate(
                directory, "transport-only", event_store="memory", http="fastify"
            )
            selection = json.loads((transport_only / "project.json").read_text())["deployables"]["service"]["selection"]
            self.assertEqual(selection, {"event-store": "memory", "http": "fastify", "auth": "none", "users": "none"})
            # A transport needs no container, so the Compose file this project has holds its own service
            # and nothing to back it: the transport answer did not quietly buy a database.
            compose = self.settings((transport_only / "docker-compose.yml").read_text())
            self.assertIn("command: ['make', 'dev']", compose)
            self.assertNotIn("postgres", compose)
            self.assertNotIn("services-up:", (transport_only / "Makefile").read_text())
            self.assertTrue((transport_only / "apps/service/src/adapters/driving/http/app.ts").is_file())
            self.assertFalse((transport_only / "apps/service/migrations").exists())

            identity = self.generate(
                directory, "identity", event_store="memory", http="fastify", auth="keycloak"
            )
            compose = (identity / "docker-compose.yml").read_text()
            self.assertIn("keycloak", compose)
            self.assertNotIn("postgres:17-alpine", compose)
            # Keycloak needs a container but nothing to migrate, so it gets the generic pair of targets
            # and no `migrate`.
            makefile = (identity / "Makefile").read_text()
            self.assertIn("services-up:", makefile)
            self.assertNotIn("migrate:", makefile)

    def test_an_axis_answer_that_cannot_be_built_is_refused_with_the_flag_that_fixes_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            # The transports are the language-specific answers, one per backend, and asking for one on the
            # wrong backend names the one that fits. Read from the catalog rather than listed: a hand-kept
            # map here is a sweep that silently skips every backend added after it was written — the last
            # one named three backends and covered neither Java one.
            transports = {
                backend: axis_default("http", backend, "none") for backend in CATALOG["backends"]
            }
            for language, transport in transports.items():
                for other, wrong in transports.items():
                    if other == language:
                        continue
                    message = self.refuse(
                        directory, f"gated-{language}-{wrong}", backend=language, http=wrong
                    )
                    self.assertIn(f"--http {wrong} is implemented for the {other} backend", message)
                    self.assertIn("half-ported version is deliberately not emitted", message)
                    # The fix names this project's own transport, not the catalog's first one.
                    self.assertIn(f"--http {transport}", message)

            message = self.refuse(
                directory, "gated-cd-store", profile="standard", event_store="postgres"
            )
            self.assertIn("the standard profile has no such port", message)
            self.assertIn("--profile event-modelling", message)

            self.assertIn(
                "unknown --event-store value 'redis'",
                self.refuse(directory, "gated-redis", event_store="redis"),
            )

            # Cross-axis: an identity provider with no transport is configuration a project cannot
            # use. The suggested fix is this backend's transport.
            for language, transport in transports.items():
                message = self.refuse(
                    directory,
                    f"gated-auth-{language}",
                    backend=language,
                    http="none",
                    auth="keycloak",
                )
                self.assertIn("needs an inbound HTTP entry point", message)
                self.assertIn(f"--http {transport}", message)

            # Naming the no-infrastructure answer is always legal, including where the axis offers
            # nothing else — refusing `--http none` would be refusing "give me nothing".
            self.assertEqual(
                resolve_selection(
                    {"event-store": "memory", "http": "none", "auth": "none", "users": "none"},
                    "standard",
                    "go",
                    "none",
                ).summary,
                {"http": "none", "auth": "none", "users": "none"},
            )

    def test_a_generated_project_answers_each_axis_again_on_its_own(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory,
                "prunable",
                "event-modelling",
                "typescript",
                "none",
                event_store="postgres",
                http="fastify",
                auth="keycloak",
                users="keycloak",
            )
            script = ["python3", "scripts/backing-services.py"]

            listing = subprocess.run(
                script + ["--list"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE
            ).stdout
            # One heading per axis, each showing only the answers this project can still be given.
            for axis in ("--event-store", "--http", "--auth", "--users"):
                self.assertIn(axis, listing)
            self.assertIn("postgres", listing)
            self.assertIn("keycloak", listing)
            # Pruning only subtracts, so an adapter that was never emitted is never offered.
            self.assertNotIn("sqlite", listing)

            # One axis at a time: answering the identity questions must not settle the event-store question.
            both = ["--auth", "none", "--users", "none"]
            subprocess.run(script + both, cwd=repo, check=True, stdout=subprocess.DEVNULL)
            self.assertFalse((repo / "docker").exists())
            self.assertFalse((repo / "apps/service/src/adapters/driving/http/auth").exists())
            self.assertFalse((repo / "apps/service/tests/auth").exists())
            self.assertNotIn("keycloak", (repo / "docker-compose.yml").read_text())
            self.assertIn("postgres:17-alpine", (repo / "docker-compose.yml").read_text())
            self.assertNotIn("OIDC_ISSUER", (repo / ".env.example").read_text())
            self.assertIn("services-up:", (repo / "Makefile").read_text())
            # The transport is a different axis and is untouched by the identity answer.
            self.assertTrue((repo / "apps/service/src/adapters/driving/http/app.ts").is_file())

            subprocess.run(script + ["--event-store", "memory"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
            for absent in (
                "apps/service/migrations",
                "apps/service/src/adapters/driven/event-store-postgres",
                "apps/service/tests/integration",
                "apps/service/vitest.integration.config.ts",
            ):
                self.assertFalse((repo / absent).exists(), absent)
            # The Compose file stays, because the app is in it — but nothing in it is a backing service
            # any more, so there is nothing left for `make services-up` to start.
            compose = self.settings((repo / "docker-compose.yml").read_text())
            self.assertNotIn("postgres", compose)
            self.assertNotIn("keycloak", compose)
            self.assertIn("command: ['make', 'dev']", compose)
            # The fake stays: it is what the port's contract runs against in `make verify`.
            self.assertTrue((repo / "apps/service/src/adapters/driven/event-store-memory.ts").is_file())
            self.assertTrue((repo / "apps/service/tests/contract/event-store-memory.test.ts").is_file())

            makefile = (repo / "Makefile").read_text()
            for absent in ("\nmigrate:", "CI_DATABASE :="):
                self.assertNotIn(absent, makefile)
            # `services-up` survives the prune and is still correct: it tests for the Compose file the
            # prune has just deleted, rather than running `docker compose` against nothing.
            self.assertIn("services-up:", makefile)
            self.assertIn("if [ -f docker-compose.yml ]", makefile)
            # The transport axis is still open, so its markers are still there to be found.
            self.assertNotIn("backing-service:postgres:", makefile)
            # The target survives the prune because its body is a variable with a fallback, not a second
            # copy of the recipe that a subtractive prune could never restore.
            self.assertIn("test-integration:", makefile)
            self.assertIn("INTEGRATION_TEST ?=", makefile)
            self.assertIn("ci: verify audit $(CI_DATABASE) test-integration", makefile)

            service = json.loads((repo / "apps/service/package.json").read_text())
            self.assertNotIn("pg", service.get("dependencies", {}))
            self.assertNotIn("node-pg-migrate", service["devDependencies"])
            for script_name in ("migrate", "migrate:down", "test:integration"):
                self.assertNotIn(script_name, service["scripts"])

            # Nothing marked is left anywhere but the prune script's own explanation of the markers.
            for path in repo.rglob("*"):
                if not path.is_file() or ".git" in path.parts or "node_modules" in path.parts:
                    continue
                if path.name == "backing-services.py":
                    continue
                self.assertNotIn("backing-service:postgres:", path.read_text(errors="ignore"), path.name)

            # The event-store and identity questions are settled; the transport one is not, so it is the
            # only axis still listed.
            remaining = subprocess.run(
                script + ["--list"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE
            ).stdout
            self.assertIn("--http", remaining)
            self.assertNotIn("--event-store", remaining)
            self.assertNotIn("--auth", remaining)

            # A settled axis refuses rather than pretending, and says which of the two reasons it is.
            spent = subprocess.run(
                script + ["--event-store", "postgres"], cwd=repo, text=True, stderr=subprocess.PIPE
            )
            self.assertNotEqual(spent.returncode, 0)
            self.assertIn("not available here", spent.stderr)

            subprocess.run(script + ["--http", "none"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
            exhausted = subprocess.run(
                script + ["--list"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE
            )
            self.assertIn("already settled", exhausted.stdout)

            # Nothing marked survives once every axis is answered.
            for path in repo.rglob("*"):
                if not path.is_file() or ".git" in path.parts or "node_modules" in path.parts:
                    continue
                if path.name == "backing-services.py":
                    continue
                self.assertNotIn("backing-service:", path.read_text(errors="ignore"), path.name)

    def test_a_project_with_npm_tells_it_not_to_ask_the_registry_for_advisories(self) -> None:
        """npm ends every install with one POST to the registry's bulk advisories endpoint, and since
        2026-09-04 that endpoint answers in minutes. It is not a failure — npm waits out `fetch-timeout`,
        prints a summary with no audit in it and carries on — so a generated project's gate simply took five
        silent minutes longer per install, on npm's default timeout, with every job still green.

        A project that has no `npm ci` to govern does not carry the setting, because workflow-level
        environment nothing reads is noise in a file the project's own maintainer has to read.
        """
        with tempfile.TemporaryDirectory() as directory:
            with_npm = self.generate(directory, "with-npm", language="go", frontend="react-vite")
            without = self.generate(directory, "without-npm", language="go", frontend="none")
            workflow = (with_npm / ".github/workflows/verify.yml").read_text()
            self.assertIn("npm_config_audit: 'false'", workflow)
            # And the caps on what any one slow answer costs, since the endpoint is not the only thing
            # that can hang: a minute and five retries rather than npm's five-minute default.
            for capped in ("npm_config_fetch_timeout: '60000'", "npm_config_fetch_retries: '5'",
                           "npm_config_maxsockets: '5'", "npm_config_prefer_offline: 'true'"):
                self.assertIn(capped, workflow)
            # It is workflow-level, so the integration job a store brings inherits it too.
            self.assertLess(workflow.index("npm_config_audit"), workflow.index("jobs:"))
            self.assertNotIn("npm_config", (without / ".github/workflows/verify.yml").read_text())
