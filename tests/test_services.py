"""Which services a project has is one fact, and everything that names a service reads it.

`project.json`'s `deployables` is that fact: one entry per application with its own language, framework,
port and selection. These tests hold the generator to it: the manifest has the shape `services.py` says,
and when a second service is on the list — in the same language or another — every reader iterates rather
than spelling `apps/service`.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import VERSION
from slipwai.catalog import CATALOG, axis_default
from slipwai.errors import GenerationError
from slipwai.manifest import MANIFEST_SCHEMA, apps_from_manifest
from slipwai.scaffold import project_files, write_project
from slipwai.selection import Selection, resolve_selection
from slipwai.services import (
    add_service,
    add_web,
    contexts_of,
    default_apps,
    described,
    services_of,
)


def selected(backend: str, **named: str) -> Selection:
    """Axis answers by keyword — `event_store="sqlite"` — the way `FactoryTestCase.generate` takes them."""
    return resolve_selection(
        {axis.replace("_", "-"): answer for axis, answer in named.items()}, "event-modelling", backend, "none"
    )


def with_payments(
    backend: str, frontend: str = "none", second: str | None = None, second_axes: dict | None = None, **named: str
):
    """A project's files with `payments` beside the first service, in the same language or `second`."""
    first = selected(backend, **named)
    second = backend if second is None else second
    answers = {"http": axis_default("http", second, "none"), **(second_axes or {})}
    apps = add_service(default_apps(backend, frontend, first), "payments", second, selected(second, **answers))
    return project_files("two", "event-modelling", "none", apps), apps


class ServicesTest(FactoryTestCase):
    def test_the_manifest_records_every_application_and_reads_back(self) -> None:
        apps = default_apps("typescript", "react-vite", Selection({"http": "fastify"}))
        document = json.loads(project_files("listed", "event-modelling", "none", apps)["project.json"])
        self.assertEqual(document["schema"], MANIFEST_SCHEMA)
        # Provenance, so a project can be read against the factory's CHANGELOG: what made it, and what has
        # written into it since. Equal at generation, and only `add-service` moves the second one.
        self.assertEqual(
            document["generator"], {"name": "slipwai", "generatedWith": VERSION, "updatedWith": VERSION}
        )
        service = document["deployables"]["service"]
        self.assertEqual(
            {k: service[k] for k in ("kind", "path", "language", "port", "selection")},
            {"kind": "service", "path": "apps/service", "language": "typescript", "port": 3000,
             "selection": {"http": "fastify"}},
        )
        web = document["deployables"]["web"]
        self.assertEqual((web["kind"], web["path"], web["port"], web["api"]), ("web", "apps/web", 5173, "service"))
        self.assertNotIn("selection", web)
        self.assertEqual(document["frontend"], "react-vite")
        # No project-wide backend or selection: a project may have several, and each entry carries its own.
        for absent in ("backend", "language", "framework", "selection"):
            self.assertNotIn(absent, document)
        # Round trip: what the factory wrote is what `add-service` will read.
        self.assertEqual(apps_from_manifest(document), apps)

    def test_a_service_records_what_it_owns_and_which_contexts_it_holds(self) -> None:
        """`purpose` and `contexts` scaffold nothing; they are what the delivery loop places slices against,
        so the manifest has to carry them, read them back, and tell "not said" from "said"."""
        apps = default_apps(
            "typescript", "none", Selection({"http": "fastify"}),
            purpose="Lists open tables and takes seat requests.", contexts=["tables"],
        )
        document = json.loads(project_files("owned", "event-modelling", "none", apps)["project.json"])
        service = document["deployables"]["service"]
        self.assertEqual(service["purpose"], "Lists open tables and takes seat requests.")
        self.assertEqual(service["contexts"], ["tables"])
        self.assertEqual(apps_from_manifest(document), apps)
        # Not said is absent — not "" and not "none" — so a reader can tell unanswered from answered, and
        # the service is then a context of its own.
        bare = default_apps("typescript", "none")
        record = json.loads(project_files("bare", "event-modelling", "none", bare)["project.json"])
        self.assertNotIn("purpose", record["deployables"]["service"])
        self.assertNotIn("contexts", record["deployables"]["service"])
        self.assertEqual(bare[0].context_names, ("service",))
        self.assertEqual(apps_from_manifest(record), bare)
        # A context is a directory inside a service and a heading, so it takes a service name's shape.
        with self.assertRaises(GenerationError):
            default_apps("typescript", "none", contexts=["Not A Context"])
        # Two services may answer to one context, and the prose groups them by it.
        grown = add_service(
            apps, "seating", "typescript", Selection({"http": "fastify"}),
            purpose="Holds seats and never oversells a table.", contexts=["tables"],
        )
        grown = add_service(grown, "location", "python", Selection({}), purpose="Geocodes places and fuzzes pins.")
        self.assertEqual(
            {context: [s.name for s in members] for context, members in contexts_of(grown).items()},
            {"tables": ["service", "seating"], "location": ["location"]},
        )
        self.assertEqual(
            described(grown[2]), "`apps/location` (`python`, port 3002) — Geocodes places and fuzzes pins."
        )
        self.assertIn("context `tables`", described(grown[0]))

    def test_one_service_may_hold_several_contexts(self) -> None:
        """The modular monolith a project starts as: one deployable, several models. The list is recorded
        once each and in the order given, the service appears under every context it holds, and a manifest
        from before the field was a list still reads."""
        apps = default_apps(
            "typescript", "none", Selection({"http": "fastify"}),
            purpose="Runs the whole product until a context earns its own deployable.",
            contexts=["gifting", "budgeting", "gifting"],
        )
        self.assertEqual(apps[0].contexts, ("gifting", "budgeting"))
        document = json.loads(project_files("monolith", "event-modelling", "none", apps)["project.json"])
        self.assertEqual(document["deployables"]["service"]["contexts"], ["gifting", "budgeting"])
        self.assertEqual(apps_from_manifest(document), apps)
        self.assertEqual(
            {context: [s.name for s in members] for context, members in contexts_of(apps).items()},
            {"gifting": ["service"], "budgeting": ["service"]},
        )
        self.assertIn("contexts `gifting`, `budgeting`", described(apps[0]))
        # `"context": "billing"` — one context, singular — is what the factory wrote before; it reads as a
        # list of one, so a project generated then is not refused by the factory that generates now.
        older = json.loads(json.dumps(document))
        older["deployables"]["service"]["contexts"] = "billing"
        with self.assertRaises(GenerationError):
            apps_from_manifest(older)
        del older["deployables"]["service"]["contexts"]
        older["deployables"]["service"]["context"] = "billing"
        self.assertEqual(apps_from_manifest(older)[0].contexts, ("billing",))

    def test_a_manifest_this_factory_does_not_know_is_refused(self) -> None:
        for broken, message in (
            ({"schema": 99, "deployables": {}}, "schema 99"),
            ({"schema": MANIFEST_SCHEMA}, "no deployables"),
            ({"schema": MANIFEST_SCHEMA, "deployables": {"service": {"kind": "service"}}}, "missing"),
            (
                {
                    "schema": MANIFEST_SCHEMA,
                    "deployables": {
                        "web": {"kind": "web", "path": "apps/web", "language": "typescript", "port": 5173}
                    },
                },
                "no service",
            ),
        ):
            with self.subTest(message=message), self.assertRaises(GenerationError) as refused:
                apps_from_manifest(broken)
            self.assertIn(message, str(refused.exception))

    def test_a_service_name_has_to_be_a_directory_a_package_and_a_compose_service(self) -> None:
        apps = default_apps("go", "react-vite")
        for name in ("Payments", "1st", "-x", "pay_ments", "web", "service"):
            with self.subTest(name=name), self.assertRaises(GenerationError):
                add_service(apps, name, "go", Selection({}))
        added = add_service(apps, "payments", "go", Selection({}))
        payments = added[-1]
        # The next service port, not one above the browser app's 5173.
        self.assertEqual((payments.path, payments.port, payments.backend), ("apps/payments", 3001, "go"))
        self.assertEqual(add_service(added, "billing", "python", Selection({}))[-1].port, 3002)

    def test_every_reader_iterates_over_the_services(self) -> None:
        """The proof that no reader kept its own copy: with two services, each names both."""
        for backend in CATALOG["backends"]:
            frontend = "react-vite" if backend == "typescript" else "none"
            files, apps = with_payments(backend, frontend, http=axis_default("http", backend, "none"))
            with self.subTest(backend=backend):
                skeleton = [path for path in files if path.startswith("apps/payments/")]
                self.assertTrue(skeleton, "the second service has no skeleton")
                # Named for itself, not a copy of the first: nothing under it carries the template name.
                self.assertFalse(
                    [path for path in skeleton if "delivery_starter" in path or "deliverystarter" in path]
                )
                for path in ("Makefile", "docker-compose.yml", "scripts/verify", "README.md",
                             "docs/architecture.md", "skills/run-the-app/SKILL.md", ".claude/settings.json"):
                    self.assertIn("apps/payments", files[path].replace("dev-payments", "apps/payments"), path)
                deployables = json.loads(files["project.json"])["deployables"]
                self.assertEqual(deployables["payments"]["port"], 3001)
                makefile = files["Makefile"]
                self.assertIn("\ndev-payments:", makefile)
                self.assertIn("PORT:-3001", makefile)
                self.assertIn("test-integration: test-integration-service test-integration-payments", makefile)
                compose = files["docker-compose.yml"]
                self.assertIn("\n  payments:\n", compose)
                self.assertIn("'${PORT_PAYMENTS:-3001}:3001'", compose)
                self.assertIn("make dev-payments", compose)
                self.assertIn("make dev-payments", files[".claude/settings.json"])
                # The gate loops inside Make, so the verify job is unchanged; only the caches know the list.
                workflow = files[".github/workflows/verify.yml"]
                self.assertEqual(workflow.count("make verify"), 1)
                if apps[0].language in ("python", "java", "go"):
                    self.assertIn("apps/payments/", workflow)

    def test_each_language_has_a_shape_for_a_second_service(self) -> None:
        typescript, _ = with_payments("typescript", "react-vite", http="fastify")
        self.assertEqual(
            json.loads(typescript["package.json"])["workspaces"],
            ["apps/service", "apps/payments", "apps/web", "packages/*"],
        )
        lock = json.loads(typescript["package-lock.json"])
        self.assertEqual(lock["packages"]["apps/payments"]["name"], "two-payments")
        self.assertEqual(lock["packages"]["node_modules/two-payments"], {"resolved": "apps/payments", "link": True})
        go, _ = with_payments("go", http="net-http")
        self.assertIn("use ./apps/service\nuse ./apps/payments\n", go["go.work"])
        self.assertIn("module example.com/two/payments", go["apps/payments/go.mod"])
        python, _ = with_payments("python", http="fastapi")
        self.assertIn('apps="apps/service apps/payments"', python["scripts/verify"])
        self.assertTrue(any(path.startswith("apps/payments/src/two_payments/") for path in python))
        java, _ = with_payments("java-spring", http="spring-web")
        self.assertFalse("pom.xml" in java, "no aggregator pom: each service is a Maven project of its own")
        self.assertIn("<artifactId>two-payments</artifactId>", java["apps/payments/pom.xml"])
        self.assertTrue(
            any(path.startswith("apps/payments/src/main/java/com/example/twopayments/") for path in java)
        )

    def test_services_in_two_languages_share_one_repository(self) -> None:
        """A TypeScript service on Fastify and Postgres beside a Python one on FastAPI and SQLite: every
        project-wide file is the union of what the two say, and each service keeps its own answers."""
        files, apps = with_payments(
            "typescript", "react-vite", second="python", second_axes={"event_store": "sqlite"},
            event_store="postgres", http="fastify",
        )
        manifest = json.loads(files["project.json"])["deployables"]
        self.assertEqual(manifest["service"]["language"], "typescript")
        self.assertEqual(manifest["payments"]["language"], "python")
        self.assertEqual(manifest["payments"]["selection"]["http"], "fastapi")
        # One verify script per family, and a dispatcher above them.
        self.assertIn("scripts/verify-typescript", files)
        self.assertIn("scripts/verify-python", files)
        self.assertIn("scripts/verify-python scripts/verify-typescript", files["scripts/verify"].replace(
            "scripts/verify-typescript scripts/verify-python", "scripts/verify-python scripts/verify-typescript"))
        makefile = files["Makefile"]
        self.assertIn("./scripts/verify-python --lint-only", makefile)
        self.assertIn("npm --workspace apps/service run lint", makefile)
        self.assertNotIn("./scripts/verify --lint-only", makefile)
        # The npm workspace names the Node services only; a Python directory is not a package. `packages/*`
        # is globbed rather than named, because a shared package is added after generation and npm skips a
        # glob that matches nothing.
        self.assertEqual(
            json.loads(files["package.json"])["workspaces"], ["apps/service", "apps/web", "packages/*"]
        )
        # Both toolchains set up in CI, and one integration job per family with a suite to run.
        workflow = files[".github/workflows/verify.yml"]
        self.assertIn("actions/setup-node", workflow)
        self.assertIn("actions/setup-python", workflow)
        self.assertEqual(workflow.count("actions/setup-node"), 1)
        self.assertIn("  integration:\n", workflow)
        self.assertIn("make migrate-service test-integration-service", workflow)
        self.assertNotIn("test-integration-payments", workflow)
        # That job takes a `container:`, and a job with one runs a JavaScript action *inside* the image.
        # GitHub mounts its own Node in to do it; Gitea's act_runner execs a bare `node`, which `python:`
        # here — and `golang:` and `maven:` elsewhere — does not ship, so `actions/checkout` killed the job
        # on step one with exit 127 before a line of the suite ran. So it carries no `uses:` at all and
        # clones itself with git. Of `$GITHUB_SHA`, not a branch: `$GITHUB_REF` moves if something merges
        # while the run queues, and a suite that quietly tested another commit is worse than one that failed.
        integration = workflow.split("  integration:\n", 1)[1]
        self.assertNotIn("uses:", integration)
        self.assertIn('fetch -q --depth 1 origin "$GITHUB_SHA"', integration)
        # Compose: each service in its own transport's region; both toolchains' artifacts ignored.
        compose = files["docker-compose.yml"]
        self.assertIn("backing-service:fastify:begin", compose)
        self.assertIn("backing-service:fastapi:begin", compose)
        self.assertIn("image: python:3.13-bookworm", compose)
        gitignore = files[".gitignore"]
        self.assertIn("node_modules/", gitignore)
        self.assertIn(".venv/", gitignore)
        self.assertIn("*.sqlite3", gitignore)
        settings = files[".claude/settings.json"]
        self.assertIn("npm ci", settings)
        self.assertIn("python -m pytest *", settings)
        self.assertIn("apps/payments/src/two_payments/", "".join(files))

    def test_the_pruner_prunes_every_service_by_its_own_language(self) -> None:
        """`./init` after generation reaches a second service's adapters exactly as it reaches the first's,
        whatever language each is in."""
        apps = add_service(
            default_apps("python", "none", selected("python", event_store="postgres", http="fastapi", auth="keycloak")),
            "payments", "go", selected("go", event_store="postgres", http="net-http", auth="keycloak"),
        )
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "pruned"
            write_project(repo, "pruned", "event-modelling", "none", apps)
            self.assertTrue((repo / "apps/service/migrations/apply.py").is_file())
            self.assertTrue((repo / "apps/payments/cmd/migrate").is_dir())
            subprocess.run(
                ["python3", "scripts/backing-services.py", "--event-store", "memory", "--auth", "none"],
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            self.assertFalse((repo / "apps/service/migrations").exists())
            self.assertFalse(list((repo / "apps/service/src").glob("*/adapters/driving/http/auth")))
            self.assertTrue(list((repo / "apps/service/src").glob("*/adapters/driving/http/app.py")))
            self.assertNotIn("psycopg", (repo / "apps/service/pyproject.toml").read_text())
            self.assertFalse((repo / "apps/payments/cmd/migrate").exists())
            self.assertFalse((repo / "apps/payments/adapters/driving/http/auth").exists())
            self.assertTrue((repo / "apps/payments/adapters/driving/http/app.go").is_file())
            for service in services_of(apps):
                self.assertTrue((repo / service.path).is_dir())

    def test_browser_apps_are_a_list_too(self) -> None:
        """A second browser app, proxying to a second service: every reader names both, on their own ports."""
        first = selected("typescript", event_store="postgres", http="fastify")
        apps = add_service(default_apps("typescript", "react-vite", first), "payments", "typescript", first)
        apps = add_web(apps, "admin", "payments")
        files = project_files("two", "event-modelling", "none", apps)
        manifest = json.loads(files["project.json"])
        admin = manifest["deployables"]["admin"]
        self.assertEqual((admin["kind"], admin["port"], admin["api"]), ("web", 5174, "payments"))
        self.assertEqual(manifest["frontend"], "react-vite")
        self.assertIn("port: 5174,", files["apps/admin/vite.config.ts"])
        self.assertIn("'http://localhost:3001'", files["apps/admin/vite.config.ts"])
        self.assertIn("'http://localhost:3000'", files["apps/web/vite.config.ts"])
        makefile = files["Makefile"]
        self.assertIn(
            "\ndev-admin: ## Run admin in the foreground on http://localhost:5174, proxying /api to payments", makefile
        )
        self.assertIn("npm --workspace apps/admin run lint", makefile)
        compose = files["docker-compose.yml"]
        self.assertIn("\n  admin:\n", compose)
        self.assertIn("API_ORIGIN: http://payments:3001", compose)
        self.assertIn("'${WEB_PORT_ADMIN:-5174}:5174'", compose)
        self.assertEqual(
            json.loads(files["package.json"])["workspaces"],
            ["apps/service", "apps/payments", "apps/web", "apps/admin", "packages/*"],
        )
        self.assertEqual(json.loads(files["package-lock.json"])["packages"]["apps/admin"]["name"], "two-admin")
        self.assertIn("apps/admin/dist/", files[".gitignore"])
        self.assertIn("make dev-admin WEB_HOST=*", files[".claude/settings.json"])
        for name in ("Payments", "web", "service"):
            with self.subTest(name=name), self.assertRaises(GenerationError):
                add_web(apps, name, None)
        with self.assertRaises(GenerationError):
            add_web(apps, "portal", "billing")
