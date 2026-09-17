"""A selected adapter arrives with the contract that keeps it honest, and with the gate that runs it."""
from __future__ import annotations

import json
import os
import shutil
import tempfile

from support import FactoryTestCase

from slipwai.assets import BACKING_SERVICE_ROOT
from slipwai.catalog import CATALOG, axis_default, family_of
from slipwai.naming import java_package_segment, python_package_name
from slipwai.project.service_layouts import SERVICE_FILES


class BackingServicesTest(FactoryTestCase):
    def test_the_sqlite_store_is_proved_inside_the_docker_free_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "with-sqlite", event_store="sqlite", http="none")
            for relative in (
                "apps/service/src/adapters/driven/event-store-sqlite.ts",
                "apps/service/tests/contract/event-store-sqlite.test.ts",
            ):
                self.assertTrue((repo / relative).is_file(), relative)

            # A file database needs no container and no migration step, so neither appears.
            self.assertFalse((repo / "docker-compose.yml").exists())
            self.assertFalse((repo / "apps/service/migrations").exists())
            makefile = (repo / "Makefile").read_text()
            for absent in ("services-up:", "migrate:", "DATABASE_URL"):
                self.assertNotIn(absent, makefile)
            # Its suite is in the default one, not the excluded integration directory.
            self.assertNotIn("tests/integration", (repo / "apps/service/vitest.config.ts").read_text())
            self.assertFalse((repo / "apps/service/vitest.integration.config.ts").exists())

            # It adds no dependency, which is the reason node:sqlite was chosen over a native binding.
            service = json.loads((repo / "apps/service/package.json").read_text())
            self.assertEqual(service.get("dependencies", {}), {})

            # An event log is data: committing one is committing somebody's history.
            ignored = (repo / ".gitignore").read_text()
            for pattern in ("*.sqlite3", "*.sqlite3-wal", "*.sqlite3-shm"):
                self.assertIn(pattern, ignored)

            adapter = (repo / "apps/service/src/adapters/driven/event-store-sqlite.ts").read_text()
            # The append-only rule belongs to the database, not to the adapter that happens to write to it.
            self.assertIn("events_reject_update", adapter)
            self.assertIn("events_reject_delete", adapter)
            self.assertIn("CONSTRAINT events_stream_version_unique UNIQUE (stream_id, version)", adapter)
            # And the thing it cannot do is said out loud, next to the thing it can.
            self.assertIn("CANNOT prove concurrent behaviour", adapter)

    def test_the_envelopes_two_ids_are_uuids_in_types_of_their_own(self) -> None:
        """Correlation and causation are UUIDs, and two types rather than one used twice.

        Both halves matter, and they are checked here rather than in one backend's own suite because the
        answer has to be the same in all of them. A free string invites an id that means one thing in one
        service and something else in the next; a *shared* type lets correlation be written where causation
        belongs, which compiles, runs, and produces a causal tree in which everything caused itself.
        """
        for backend in CATALOG["backends"]:
            with self.subTest(backend=backend), tempfile.TemporaryDirectory() as directory:
                repo = self.generate(
                    directory,
                    "envelope",
                    "event-modelling",
                    backend,
                    "none",
                    event_store="postgres",
                    http="none",
                    auth="none",
                )
                sources = [
                    path.read_text()
                    for path in sorted((repo / "apps/service").rglob("*"))
                    if path.is_file() and path.suffix in {".go", ".java", ".js", ".py", ".sql", ".ts"}
                ]
                service = "\n".join(sources)
                # Named types, not one alias twice. Spelled `...ID` in Go and `...Id` elsewhere, which is
                # each language's own convention and not a difference worth asserting.
                lowered = service.lower()
                self.assertIn("correlationid", lowered, backend)
                self.assertIn("causationid", lowered, backend)
                # And the column says UUID too, so Postgres rejects a malformed one at the door rather
                # than storing it for a reader to trip over years later.
                self.assertIn("correlation_id  UUID", service, backend)
                self.assertIn("causation_id    UUID", service, backend)
                self.assertNotIn("correlation_id  TEXT", service, backend)
                shutil.rmtree(repo)

    def test_the_transport_carries_a_default_correction_and_no_business_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "with-http", event_store="memory", http="fastify")
            app = (repo / "apps/service/src/adapters/driving/http/app.ts").read_text()
            # The framework's own 404 echoes the requested path into the response body, and from there
            # into every access log downstream. The correction is the reason this file is not empty.
            self.assertIn("setNotFoundHandler", app)
            self.assertIn("{ error: 'notFound' }", app)
            self.assertTrue((repo / "apps/service/tests/edge/http-app.test.ts").is_file())

            # What the transport pins is asserted in `test_schema_edge.py`, beside the schemas it is for.

            # Fastify's logger reaches a package whose published types name a type @types/node removed.
            # Nothing in a generated project can fix a dependency's own .d.ts, so the escape hatch is
            # scoped to this one selection, marked, and pruned away with it.
            tsconfig = (repo / "apps/service/tsconfig.json").read_text()
            self.assertIn('"skipLibCheck": true', tsconfig)
            self.assertIn("backing-service:fastify:begin", tsconfig)
            plain = self.generate(directory, "no-http", http="none")
            self.assertNotIn('"skipLibCheck"', (plain / "apps/service/tsconfig.json").read_text())

    def test_the_selected_adapters_arrive_with_the_contract_that_keeps_them_honest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory,
                "with-services",
                "event-modelling",
                "typescript",
                "none",
                event_store="postgres",
                http="fastify",
                auth="keycloak",
                users="keycloak",
            )
            for relative in (
                "docker-compose.yml",
                ".env.example",
                "scripts/backing-services.py",
                "docker/keycloak/realms/app.json",
                "apps/service/migrations/001_events.js",
                "apps/service/migrations/002_events_append_only.js",
                "apps/service/src/application/ports/events.ts",
                "apps/service/src/adapters/driven/event-store-memory.ts",
                "apps/service/src/adapters/driven/event-store-postgres/index.ts",
                "apps/service/src/adapters/driving/http/auth/oidc-keycloak.ts",
                "apps/service/tests/contract/event-store-contract.ts",
                "apps/service/tests/integration/event-store-postgres.test.ts",
                "apps/service/tests/auth/oidc-keycloak.test.ts",
                "apps/service/vitest.integration.config.ts",
            ):
                self.assertTrue((repo / relative).is_file(), relative)
            self.assertTrue(os.access(repo / "scripts/backing-services.py", os.X_OK))

            metadata = json.loads((repo / "project.json").read_text())
            self.assertEqual(
                metadata["deployables"]["service"]["selection"],
                {"event-store": "postgres", "http": "fastify", "auth": "keycloak", "users": "keycloak"},
            )
            for capability in ("event-store-postgres", "auth-keycloak", "users-keycloak"):
                self.assertIn(capability, metadata["deployables"]["service"]["capabilities"])

            compose = (repo / "docker-compose.yml").read_text()
            # The design of this file is its comments as much as its services, so the keys are checked
            # against the settings alone. A machine-global container name would make two checkouts on one
            # machine fight over it; a fixed host port would do the same.
            self.assertNotIn("container_name", self.settings(compose))
            self.assertIn("No `container_name` anywhere, deliberately", compose)
            self.assertIn("${POSTGRES_PORT:-5433}:5432", compose)
            self.assertIn("${KEYCLOAK_PORT:-8081}:8080", compose)
            self.assertIn("postgres:17-alpine", compose)
            self.assertIn("quay.io/keycloak/keycloak:26.7", compose)
            # Postgres, Keycloak, and the service itself: `make demo` waits on all three, so "up" means
            # "answering" rather than "started".
            self.assertEqual(compose.count("healthcheck:"), 3)
            self.assertIn("pg_isready -U app -d app", compose)
            self.assertIn("--import-realm", compose)
            self.assertIn("volumes:\n  postgres-data:", compose)

            # The append-only guard is a trigger rather than a REVOKE, because the application role owns
            # the table and an owner keeps its privileges through a REVOKE.
            guard = (repo / "apps/service/migrations/002_events_append_only.js").read_text()
            self.assertIn("events_reject_mutation", guard)
            self.assertIn("BEFORE UPDATE ON events", guard)
            self.assertIn("BEFORE TRUNCATE ON events", guard)
            self.assertIn("REVOKE UPDATE, DELETE, TRUNCATE ON events FROM PUBLIC", guard)
            self.assertIn("CONSTRAINT events_stream_version_unique UNIQUE (stream_id, version)",
                          (repo / "apps/service/migrations/001_events.js").read_text())

            # Both adapters implement the one port, and the one contract runs against both.
            contract = (repo / "apps/service/tests/contract/event-store-contract.ts").read_text()
            port = "application/ports/events.js"
            self.assertIn(f"../../src/{port}", contract)
            for adapter, up in (("event-store-memory", "../.."), ("event-store-postgres/index", "../../..")):
                self.assertIn(
                    f"{up}/{port}",
                    (repo / f"apps/service/src/adapters/driven/{adapter}.ts").read_text(),
                )
            self.assertIn(
                "eventStoreContract",
                (repo / "apps/service/tests/contract/event-store-memory.test.ts").read_text(),
            )
            self.assertIn(
                "eventStoreContract",
                (repo / "apps/service/tests/integration/event-store-postgres.test.ts").read_text(),
            )

            # The gate stays Docker-free: the db-backed directory is excluded from the default suite.
            self.assertIn("tests/integration/**", (repo / "apps/service/vitest.config.ts").read_text())
            self.assertIn(
                "tests/integration/**/*.test.ts",
                (repo / "apps/service/vitest.integration.config.ts").read_text(),
            )

            makefile = (repo / "Makefile").read_text()
            for target in ("services-up:", "services-down:", "migrate:"):
                self.assertIn(target, makefile)
            self.assertIn("DATABASE_URL ?= postgres://app:app@localhost:5433/app", makefile)
            self.assertIn("ci: verify audit $(CI_DATABASE) test-integration", makefile)
            self.assertIn("CI_DATABASE := migrate", makefile)
            # One recipe per target, whichever way the services are later pruned.
            self.assertEqual(makefile.count("\ntest-integration:"), 1)
            self.assertEqual(makefile.count("\nci:"), 1)

            service = json.loads((repo / "apps/service/package.json").read_text())
            # node-pg-migrate is a runtime dependency: the production image runs `make migrate` as a task.
            # What the store adds on top of the transport's own, which `test_schema_edge.py` pins.
            self.assertEqual(
                {name: service["dependencies"].get(name) for name in ("node-pg-migrate", "pg")},
                {"node-pg-migrate": "9.0.0", "pg": "8.23.0"},
            )
            self.assertIn("@types/pg", service["devDependencies"])
            self.assertEqual(service["scripts"]["migrate"], "node-pg-migrate up -m migrations")
            self.assertIn(".env\n", (repo / ".gitignore").read_text())
            self.assertIn("DATABASE_URL=postgres://app:app@localhost:5433/app", (repo / ".env.example").read_text())
            self.assertIn("OIDC_ISSUER=http://localhost:8081/realms/app", (repo / ".env.example").read_text())

            # `./init` takes the pruning flags and keeps them away from Spec Kit.
            init = (repo / "init").read_text()
            for axis in ("--event-store", "--http", "--auth", "--users"):
                self.assertIn(axis, init)
            self.assertIn("scripts/backing-services.py $backing_flags", init)

    def test_the_db_backed_gate_is_separate_and_reachable_on_any_runner(self) -> None:
        """`verify` never needs Docker; the db-backed job addresses Postgres the way both runner kinds
        agree on."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "ci-services", "event-modelling", "typescript", "none", event_store="postgres"
            )
            ci = (repo / ".github/workflows/verify.yml").read_text()
            verify_job, integration_job = ci.split("# backing-service:postgres:begin")
            self.assertNotIn("postgres", verify_job)
            self.assertIn("  integration:", integration_job)
            # Containerised, so the label resolves — `localhost` reaches the service on a bare-VM runner only.
            # And no `needs:`: Gitea blocks a dependent job forever on `push`, so `main` stops gating itself.
            self.assertIn("container: node:24-bookworm", integration_job)
            self.assertNotIn("\n    needs:", integration_job)
            self.assertIn("DATABASE_URL: postgres://app:app@postgres:5432/app", integration_job)
            self.assertNotIn("5433:5432", integration_job)
            self.assertNotIn("localhost", self.settings(integration_job))
            # The probe is the same for every backend, so it cannot assume the language's runtime is a
            # usable scripting tool. /dev/tcp is a bash feature and a job with `container:` runs its steps
            # under plain sh, where it silently does nothing — which reads as "unreachable" whether or not
            # it is. Hence the explicit `shell: bash`, which is the load-bearing line here.
            self.assertIn("Wait for Postgres", integration_job)
            self.assertIn("shell: bash", integration_job)
            self.assertIn("/dev/tcp/postgres/5432", integration_job)
            self.assertIn("make migrate test-integration", integration_job)

    def test_one_event_log_schema_is_shared_by_every_backend_that_needs_it(self) -> None:
        """The Python and Go backends apply the same `.sql` files, and TypeScript's `.js` migrations
        must not drift from them.

        TypeScript keeps `.js` for a stated reason — node-pg-migrate executes a whole `.sql` file as
        the up migration, including anything after a `-- Down Migration` comment — so the schema
        exists in two forms. These are the clauses that carry the guarantees, and a change to one
        form that misses the other is the failure this catches.
        """
        shared = "\n".join(
            (BACKING_SERVICE_ROOT / "sql" / name).read_text()
            for name in ("001_events.sql", "002_events_append_only.sql")
        )
        typescript = "\n".join(
            (BACKING_SERVICE_ROOT / "typescript/migrations" / name).read_text()
            for name in ("001_events.js", "002_events_append_only.js")
        )
        for clause in (
            "CONSTRAINT events_stream_version_unique UNIQUE (stream_id, version)",
            "CONSTRAINT events_version_non_negative CHECK (version >= 0)",
            "global_position BIGSERIAL PRIMARY KEY",
            "events_reject_mutation",
            "BEFORE UPDATE ON events",
            "BEFORE DELETE ON events",
            "BEFORE TRUNCATE ON events",
            "REVOKE UPDATE, DELETE, TRUNCATE ON events FROM PUBLIC",
        ):
            self.assertIn(clause, shared, f"shared SQL lost: {clause}")
            self.assertIn(clause, typescript, f"TypeScript migrations lost: {clause}")

        # And the file-backed store enforces the same append-only rule in its own dialect, in every
        # language that offers it.
        for relative in (
            "typescript/event-store-sqlite.ts",
            "python/event_store_sqlite.py",
            "go/event_store_sqlite.go",
            "java/event_store_sqlite.java",
        ):
            adapter = (BACKING_SERVICE_ROOT / relative).read_text()
            self.assertIn("events_reject_update", adapter, relative)
            self.assertIn("events_reject_delete", adapter, relative)
            self.assertIn("UNIQUE (stream_id, version)", adapter, relative)

    def test_every_backend_gets_the_same_port_and_the_same_contract(self) -> None:
        """One event-store port per backend, and one contract suite run against every adapter.

        Driven by the layout table and the catalog rather than by a hand-kept map of paths: the last map
        here named three backends and silently covered neither Java one. Every file the in-memory store, the
        SQLite store and this backend's own transport declare in `SERVICE_FILES` has to arrive in a
        generated project, and the in-memory feature — the one every selection ships — has to be the one
        carrying the port and the contract suite the other adapters are held to.
        """
        with tempfile.TemporaryDirectory() as directory:
            for backend in CATALOG["backends"]:
                transport = axis_default("http", backend, "none")
                repo = self.generate(
                    directory,
                    "store",
                    "event-modelling",
                    backend,
                    "none",
                    event_store="sqlite",
                    http=transport,
                )
                layout = SERVICE_FILES[backend]
                always = [path.lower() for path in layout["memory"]]
                self.assertTrue(
                    any("contract" in path for path in always), f"{backend}: no contract suite in memory"
                )
                self.assertTrue(any("events" in path for path in always), f"{backend}: no port in memory")
                for feature in ("memory", "sqlite", transport):
                    for destination in layout[feature]:
                        path = repo / "apps/service" / self.generated_path(backend, "store", destination)
                        self.assertTrue(path.is_file(), f"{backend}: {path}")
                shutil.rmtree(repo)

    @staticmethod
    def generated_path(backend: str, project_name: str, destination: str) -> str:
        """Where a layout-table destination lands once the language module has renamed the template package.

        Python's `language_files` renames the `delivery_starter` package after the project, and the Java
        family's `rename_java_sources` does the same for the `deliverystarter` segment; TypeScript and Go
        keep the table's paths as they are.
        """
        family = family_of(backend)
        if family == "python":
            return destination.replace("delivery_starter", python_package_name(project_name))
        if family == "java":
            return destination.replace("deliverystarter", java_package_segment(project_name))
        return destination
