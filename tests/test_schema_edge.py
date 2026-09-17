"""The HTTP edge declares what it accepts, publishes what it declares, and checks its environment.

A suite of its own rather than more of `test_backing_services.py`, which is already at the module budget:
these assert one property of the transport across every backend that owns one, and what they are aimed at
is a *missing* registration. A transport that never registers the document builder, or never registers the
environment schema, answers every route exactly as it did before — nothing fails, the spec is simply empty
and the bad variable is simply discovered later. Each generated project's own suite proves the behaviour;
this proves the wiring is there to prove.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase


def prune(repo: Path, *answers: str) -> None:
    """Answer an axis again in a generated project, through the script it carries."""
    subprocess.run(
        ["python3", "scripts/backing-services.py", *answers],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )


class SchemaEdgeTest(FactoryTestCase):
    def test_the_fastify_edge_declares_its_schemas_and_serves_the_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "schema-fastify", event_store="memory", http="fastify")
            app = (repo / "apps/service/src/adapters/driving/http/app.ts").read_text()

            self.assertIn("@fastify/swagger", app)
            self.assertIn("@fastify/env", app)
            self.assertIn("'/openapi.json'", app)
            # The document is named after the service, so a reader knows which one it describes.
            self.assertIn("title: 'schema-fastify-service'", app)
            self.assertNotIn("__SERVICE_NAME__", app)
            # Fastify deletes what a schema did not name unless told otherwise, which turns a caller's
            # misspelt field into this service's silent data loss.
            self.assertIn("removeAdditional: false", app)
            # The routes sit inside `after` because `register` is deferred: a route declared before the
            # document builder's hook exists is one the document never hears about, and that failure is
            # silent — a 200 with an empty `paths`.
            self.assertIn("app.after(", app)
            self.assertTrue((repo / "apps/service/src/config.ts").is_file())

            # Exactly pinned, the way every manifest this factory writes is, and no more than the
            # transport needs: the framework, the one schema library its routes, its responses, its
            # document and its environment are all declared with, the two plugins that decide what a
            # browser may ask for and must enforce, and the telemetry only a transport can produce.
            service = json.loads((repo / "apps/service/package.json").read_text())
            self.assertEqual(
                service["dependencies"],
                {
                    "@fastify/cors": "11.3.0",
                    "@fastify/env": "7.0.0",
                    "@fastify/helmet": "13.1.1",
                    "@fastify/otel": "0.21.0",
                    "@fastify/swagger": "9.8.1",
                    "@fastify/type-provider-typebox": "6.1.0",
                    "@opentelemetry/api": "1.9.1",
                    "@opentelemetry/exporter-trace-otlp-http": "0.222.0",
                    "@opentelemetry/resources": "2.11.0",
                    "@opentelemetry/sdk-trace-node": "2.11.0",
                    "@opentelemetry/semantic-conventions": "1.43.0",
                    "@sinclair/typebox": "0.34.52",
                    "fastify": "5.7.1",
                },
            )

    def test_the_fastapi_edge_answers_through_a_model_rather_than_an_untyped_dict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "schema-fastapi", language="python", http="fastapi")
            edge = (repo / "apps/service/src/schema_fastapi/adapters/driving/http/app.py").read_text()

            self.assertIn("response_model=Health", edge)
            # The state this replaced: a handler whose annotation promises nothing, which FastAPI then
            # publishes as a route answering anything.
            self.assertNotIn("-> dict[str, Any]", edge)
            self.assertTrue((repo / "apps/service/src/schema_fastapi/settings.py").is_file())
            self.assertIn(
                "pydantic-settings==",
                (repo / "apps/service/pyproject.toml").read_text(),
            )

    def test_the_go_edge_publishes_a_file_and_a_test_holds_it_to_the_routes(self) -> None:
        """Go has no framework to build a document from the routes, and buying a generator would cost
        the dependency this backend exists without — so the contract is a file, and the test beside the
        adapter is what stops it drifting."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "schema-go", language="go", http="net-http")
            document = (repo / "apps/service/openapi.yaml").read_text()

            for path in ("\n  /health:\n", "\n  /api/flags:\n"):
                self.assertIn(path, document)
            self.assertTrue((repo / "apps/service/adapters/driving/http/openapi_test.go").is_file())
            self.assertTrue((repo / "apps/service/config/config.go").is_file())
            # The type is the schema here, and this is what makes that true rather than aspirational.
            adapter = (repo / "apps/service/adapters/driving/http/app.go").read_text()
            self.assertIn("DisallowUnknownFields", adapter)

    def test_a_project_with_no_transport_has_no_edge_to_configure(self) -> None:
        """The environment schema and the published contract belong to the transport, and go with it."""
        with tempfile.TemporaryDirectory() as directory:
            for language, relatives in (
                ("typescript", ("apps/service/src/config.ts",)),
                ("python", ("apps/service/src/plain/settings.py",)),
                ("go", ("apps/service/openapi.yaml", "apps/service/config/config.go")),
            ):
                repo = self.generate(directory, "plain", language=language, http="none")
                for relative in relatives:
                    self.assertFalse((repo / relative).exists(), relative)
                shutil.rmtree(repo)

    def test_a_dropped_backing_service_takes_its_environment_variables_with_it(self) -> None:
        """A variable left behind after the adapter that read it is configuration nobody can act on.

        The Python case is the one worth a test of its own: its settings module lives inside a package
        named after the project, which is the first marked file whose path the pruner has to glob.
        """
        with tempfile.TemporaryDirectory() as directory:
            for language, relative in (
                ("typescript", "apps/service/src/config.ts"),
                ("python", "apps/service/src/dropped/settings.py"),
            ):
                repo = self.generate(
                    directory, "dropped", language=language, event_store="sqlite", auth="keycloak"
                )
                self.assertIn("EVENT_STORE_PATH", (repo / relative).read_text().upper())

                prune(repo, "--event-store", "memory", "--auth", "none")

                settings = (repo / relative).read_text()
                self.assertNotIn("EVENT_STORE_PATH", settings.upper())
                self.assertNotIn("OIDC_ISSUER", settings.upper())
                # The transport is still here, so its own variables are too.
                self.assertIn("PORT", settings.upper())
                shutil.rmtree(repo)
