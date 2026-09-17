"""Readiness: the probe that asks the event store, and everything that waits on it.

`/health` says a process is up. That is not the question a load balancer, a Compose healthcheck or a
deploy smoke is asking, and for a long time every one of them asked it anyway — so a service whose event
store was unreachable reported healthy and took traffic it could not serve. These assert the other half:
that the composition root opens the store for the chosen answer, that the probe runs a query through the
**port**, and that each waiter waits on the readiness path rather than the liveness one.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile

from support import FactoryTestCase, backends_under_test

from slipwai.assets import PRUNER
from slipwai.catalog import CATALOG, axis_default, axis_options
from slipwai.probes import HEALTH_PATH, READY_PATHS, ready_path
from slipwai.project.compose import CONTAINER_ADDRESSES


class ReadinessTest(FactoryTestCase):
    def test_every_backend_declares_where_it_answers_send_me_traffic(self) -> None:
        """A backend missing from the table is a backend whose Compose file, load balancer and smoke would
        all fall back to the liveness probe without anything saying so."""
        self.assertEqual(set(CATALOG["backends"]), set(READY_PATHS))

    def test_every_generated_backend_serves_a_readiness_route_that_asks_the_port(self) -> None:
        """Per backend, whichever way it is served: the three whose entry point this factory writes answer
        on `/ready` from a route of their own, and the two whose framework owns startup contribute a
        readiness check to the endpoint that framework maintains."""
        with tempfile.TemporaryDirectory() as directory:
            for backend in backends_under_test():
                with self.subTest(backend=backend):
                    repo = self.generate(
                        directory,
                        f"ready-{backend}",
                        "event-modelling",
                        backend,
                        "none",
                        event_store="memory",
                        http=axis_default("http", backend, "none"),
                    )
                    sources = "\n".join(
                        path.read_text()
                        for path in (repo / "apps/service").rglob("*")
                        if path.is_file() and path.suffix in {".ts", ".py", ".go", ".java"}
                    )
                    if ready_path(backend) == "/ready":
                        self.assertIn("/ready", sources, backend)
                        # Through the port's own `head`, never through an adapter and never as SQL.
                        self.assertRegex(sources, r"[Ss]tore\.[Hh]ead\(", backend)
                    else:
                        # The framework's readiness endpoint, which this project points at HEALTH_PATH.
                        self.assertIn("Readiness", sources, backend)

    def test_the_composition_root_opens_the_store_the_project_chose(self) -> None:
        """One store, opened by the entry point, inside the marked region of the answer that chose it — so
        `./init --event-store memory` takes the adapter, the import and the line that opens it together."""
        entries = {
            "typescript": ("src/main.ts", "openSqliteEventStore"),
            "python": ("src/ready_store_python/main.py", "open_sqlite_event_store"),
            "go": ("cmd/serve/main.go", "eventstoresqlite.Open"),
        }
        with tempfile.TemporaryDirectory() as directory:
            for backend, (entry, opener) in entries.items():
                if backend not in backends_under_test():
                    continue
                with self.subTest(backend=backend):
                    repo = self.generate(
                        directory,
                        "ready-store-" + backend.replace("_", "-"),
                        "event-modelling",
                        backend,
                        "none",
                        event_store="sqlite",
                        http=axis_default("http", backend, "none"),
                    )
                    text = (repo / "apps/service" / entry).read_text()
                    self.assertIn(opener, text, backend)
                    # Several regions in one file is not nesting: Go's import belongs to the answer too.
                    regions = re.findall(
                        r"backing-service:sqlite:begin(.*?)backing-service:sqlite:end", text, re.S
                    )
                    self.assertTrue(regions, f"{backend}: the sqlite answer is not in a marked region")
                    self.assertTrue(
                        any(opener in region for region in regions),
                        f"{backend}: {opener} is outside every marked region, so a prune would strand it",
                    )
                    # And the store reaches the probe from there, rather than a module-level singleton.
                    self.assertRegex(text, r"readiness\(|Readiness\(", backend)

    def test_the_standard_profile_still_answers_ready_with_nothing_to_ask(self) -> None:
        """No event store, so no port that can be unreachable — and the route exists anyway, because a
        waiter that has to know which profile it is waiting on is a waiter that will get it wrong."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "ready-standard", "standard", "typescript", "none")
            entry = (repo / "apps/service/src/main.ts").read_text()
            self.assertIn("import { buildApp, readiness } from './adapters/driving/http/app.js';", entry)
            self.assertIn("readiness()", entry)
            self.assertNotIn("EventStore", entry)
            compose = (repo / "docker-compose.yml").read_text()
            self.assertIn("/ready", compose)

    def test_compose_waits_on_readiness_and_gives_the_service_the_store_s_address(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "ready-compose", event_store="postgres", http="fastify"
            )
            compose = (repo / "docker-compose.yml").read_text()
            self.assertIn(f"curl -fsS http://localhost:3000{ready_path('typescript')}", compose)
            self.assertIn("DATABASE_URL: 'postgres://app:app@postgres:5432/app'", compose)

            # And the address goes when the answer does. It cannot be a marked region — the app's block is
            # already inside the transport's — so the pruner takes it away by name instead.
            subprocess.run(
                ["python3", "scripts/backing-services.py", "--event-store", "memory"],
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            pruned = (repo / "docker-compose.yml").read_text()
            # The mapping line, not the word: the file's own header explains what `DATABASE_URL` is for.
            self.assertNotIn("      DATABASE_URL:", pruned)
            self.assertIn(f"curl -fsS http://localhost:3000{ready_path('typescript')}", pruned)
            entry = (repo / "apps/service/src/main.ts").read_text()
            self.assertNotIn("event-store-postgres", entry)
            self.assertIn("createInMemoryEventStore", entry)

    def test_what_generation_adds_to_compose_is_what_a_prune_takes_away(self) -> None:
        """The two halves of one fact, as `PACKAGE_EDITS` and the manifest additions already are."""
        self.assertEqual(
            {feature: (name,) for feature, (name, _) in CONTAINER_ADDRESSES.items()},
            PRUNER.SERVICE_ENVIRONMENT,
        )

    def test_a_production_target_gates_traffic_on_readiness_and_restarts_on_liveness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for backend in backends_under_test():
                with self.subTest(backend=backend):
                    store = "postgres" if "postgres" in axis_options(
                        "event-store", backend, "aws"
                    ) else "memory"
                    repo = self.generate(
                        directory,
                        # No `aws` in the name: the target reserves its own brand anywhere in one.
                        f"ready-cloud-{backend}",
                        "event-modelling",
                        backend,
                        "none",
                        target="aws",
                        event_store=store,
                        http=axis_default("http", backend, "aws"),
                    )
                    document = json.loads(
                        (repo / "infra/service/project.auto.tfvars.json").read_text()
                    )
                    record = document["services"]["service"]
                    self.assertEqual(record["health_path"], ready_path(backend))
                    self.assertEqual(record["liveness_path"], HEALTH_PATH)
