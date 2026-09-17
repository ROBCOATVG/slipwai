"""A service can be asked what happened inside it, and a browser is told what it may ask for.

Two facts about the edge, per backend that owns its startup. Traces: the SDK is wired, the exporter is
not, and the ids reach the log and the events. Exposure: the response headers a browser enforces, and the
allow-list that decides whose page may read a reply at all. Both are asserted against the generated files
rather than a running process — `tests/test_matrix.py` runs each project's own suite, which is where the
behaviour itself is proved.
"""
from __future__ import annotations

import tempfile

from support import FactoryTestCase

# Per backend: the module that starts tracing, the entry point that starts it, and the configuration the
# endpoint is read through. A backend absent from here answers `--http none` or is a Java framework whose
# own extension would do this — see the observability skill, which says so and says how.
TRACING = {
    "typescript": (
        "apps/service/src/tracing.ts",
        "apps/service/src/main.ts",
        "apps/service/src/config.ts",
    ),
    "python": (
        "apps/service/src/{package}/tracing.py",
        "apps/service/src/{package}/main.py",
        "apps/service/src/{package}/settings.py",
    ),
    "go": (
        "apps/service/observability/tracing.go",
        "apps/service/cmd/serve/main.go",
        "apps/service/config/config.go",
    ),
}

# Where each backend's browser-facing rules live: what a response carries, and who may ask for one.
EXPOSURE = {
    "typescript": "apps/service/src/adapters/driving/http/app.ts",
    "python": "apps/service/src/{package}/adapters/driving/http/app.py",
    "go": "apps/service/adapters/driving/http/security.go",
}


def package(name: str) -> str:
    """A Python project's importable package, which is its name with the dashes replaced."""
    return name.replace("-", "_")


class ObservabilityTest(FactoryTestCase):
    def test_every_backend_wires_the_sdk_and_leaves_the_exporter_to_the_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for backend, (module, entry, config) in TRACING.items():
                name = f"traced-{backend}"
                repo = self.generate(directory, name, "standard", backend, "none")
                paths = [path.format(package=package(name)) for path in (module, entry, config)]
                tracing, main, settings = (repo / path for path in paths)

                for path in (tracing, main, settings):
                    self.assertTrue(path.is_file(), f"{backend}: {path} is missing")
                # The endpoint is the only thing that turns exporting on, and it is read through the
                # checked configuration rather than out of the environment at the point of use.
                # Spelled as the variable in two of the three and as the lower-cased field Pydantic
                # matches it to in the other, so the comparison is case-insensitive rather than three
                # assertions saying the same thing.
                declared = settings.read_text().upper()
                self.assertIn("OTEL_EXPORTER_OTLP_ENDPOINT", declared)
                self.assertIn("OTEL_SERVICE_NAME", declared)
                # And the entry point starts it: an SDK nothing registers is an SDK that records nothing.
                self.assertRegex(main.read_text(), r"[Ss]tart_?[Tt]racing")

    def test_the_environment_template_offers_the_endpoint_unset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "traced-template", "standard", "typescript", "none")
            template = self.settings((repo / ".env.example").read_text())

            # Present so an operator knows it exists, empty so nothing is exported until it is asked for.
            self.assertRegex(template, r"(?m)^OTEL_EXPORTER_OTLP_ENDPOINT=\s*$")
            self.assertRegex(template, r"(?m)^CORS_ALLOWED_ORIGINS=\s*$")

    def test_a_trace_id_reaches_every_log_line_and_the_events_it_correlates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for backend, (module, _entry, _config) in TRACING.items():
                name = f"correlated-{backend}"
                repo = self.generate(directory, name, "event-modelling", backend, "none")
                tracing = (repo / module.format(package=package(name))).read_text()

                # The two spellings OpenTelemetry's own logging conventions use, so a collector joins a
                # log line to its trace without being told how.
                self.assertIn("trace_id", tracing)
                self.assertIn("span_id", tracing)
                # And the seam a slice takes an event's correlation and causation from, so neither has to
                # be invented per slice — which is how a causal tree ends up naming itself as its cause.
                self.assertRegex(tracing, r"[Tt]race[_]?[Ii][Dd]s")

    def test_a_browser_is_told_what_to_enforce_and_asked_which_origins_may_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for backend, edge in EXPOSURE.items():
                name = f"exposed-{backend}"
                repo = self.generate(directory, name, "standard", backend, "none")
                source = (repo / edge.format(package=package(name))).read_text()

                self.assertIn("nosniff", source.lower())
                # An allow-list, never a wildcard: a `*` and credentials cannot be combined at all, and a
                # `*` without them hands every page on the internet a reader for an unauthenticated reply.
                self.assertIn("CORS_ALLOWED_ORIGINS", source.upper())
                self.assertNotIn('"*"', source.replace('allow_methods=["*"]', "").replace('allow_headers=["*"]', ""))

    def test_the_skill_says_what_is_not_wired_and_how_java_would_be(self) -> None:
        """Java is documented rather than instrumented, and the page a reader lands on has to say so.

        The exemption this records is the one worth a test: every other backend is wired, so a reader who
        finds nothing in a Quarkus or Spring project would reasonably conclude the factory forgot.
        """
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "documented-java", "standard", "java-quarkus", "none")
            skill = (repo / "skills/observability/SKILL.md").read_text()

            self.assertIn("quarkus-opentelemetry", skill)
            self.assertIn("micrometer-tracing-bridge-otel", skill)
            self.assertIn("quarkus.otel.exporter.otlp.endpoint", skill)
            self.assertIn("management.otlp.tracing.endpoint", skill)
            # And that the default it asks for is the one every other backend already has.
            self.assertIn("OTEL_EXPORTER_OTLP_ENDPOINT", skill)
