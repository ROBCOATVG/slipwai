"""The catalog is the public configuration contract, so what it may say is checked before anything reads it."""
from __future__ import annotations

import json
import tempfile
from unittest.mock import patch

from support import FactoryTestCase

from slipwai.assets import PRUNER, ROOT
from slipwai.catalog import (
    CATALOG,
    axis_applies,
    axis_default,
    axis_options,
    catalog_axis_default,
    catalog_families,
    families,
    validate_axes,
    validate_catalog,
)
from slipwai.errors import GenerationError
from slipwai.selection import resolve_selection

# One per backend, because the transport options are. Named once: three copies of it below drifted the
# moment a fourth backend arrived.
TRANSPORTS = {
    "typescript": "fastify",
    "python": "fastapi",
    "go": "net-http",
    "java-quarkus": "quarkus-rest",
    "java-spring": "spring-web",
}


def without_java() -> dict:
    """The catalog with its Java family removed, so the naming rules can be tested against arrangements
    the validator *refuses* — the real Java family is already a valid one.

    The family's `default.framework` entry goes with it. That entry only exists because the family has
    two members, so leaving it behind would make every arrangement built on top of this one fail as
    "one backend, so it has no framework to default to" instead of on the rule under test."""
    catalog = json.loads(json.dumps(CATALOG))
    for name in [n for n, backend in catalog["backends"].items() if backend["family"] == "java"]:
        del catalog["backends"][name]
        catalog["default"]["http"].pop(name, None)
    catalog["default"]["framework"].pop("java", None)
    return catalog


class CatalogTest(FactoryTestCase):
    def test_catalog_and_default_are_valid(self) -> None:
        validate_catalog(CATALOG)
        self.assertEqual(
            CATALOG["default"],
            {
                "profile": "event-modelling",
                # Local only, and the only target there is; `tests/test_targets.py` owns the dimension.
                "target": "none",
                "backend": "typescript",
                # Java has two frameworks, so one of them has to be the answer `--language java` alone
                # resolves to. Every other family has one member, and something with one answer is not a
                # choice — which is why this map has one entry rather than four.
                "framework": {"java": "quarkus"},
                "frontend": "react-vite",
                "event-store": "postgres",
                # One answer per backend, because the options themselves are per backend.
                "http": TRANSPORTS,
                "auth": "none",
                "users": "none",
            },
        )
        self.assertNotIn("upstream" + "Template", CATALOG)

    def test_every_axis_says_what_its_answers_have_in_common(self) -> None:
        """An axis is named for a role, and the description is what keeps it from being renamed for a product
        or a protocol: `auth` was once `oidc`, because every answer to it speaks OIDC — which is exactly the
        sentence the description now carries instead of the name."""
        self.assertIn("OIDC issuer", CATALOG["axes"]["auth"]["description"])
        broken = json.loads(json.dumps(CATALOG))
        del broken["axes"]["auth"]["description"]
        with self.assertRaisesRegex(ValueError, "auth axis must describe what every answer"):
            validate_axes(broken)

    def test_event_capabilities_cannot_be_split(self) -> None:
        broken = json.loads(json.dumps(CATALOG))
        broken["profiles"]["event-modelling"]["capabilities"].remove("event-sourcing")
        with self.assertRaisesRegex(ValueError, "indivisible bundle"):
            validate_catalog(broken)

    def test_the_default_answer_on_every_axis_is_the_one_worth_starting_from(self) -> None:
        """A default is a recommendation, and the one this factory makes is a real event store and the HTTP
        transport the chosen backend actually has. The identity provider stays absent: Keycloak is scaffolded
        without its flow, so defaulting to it would hand every project a placeholder to finish."""
        for language in CATALOG["backends"]:
            self.assertEqual(axis_default("event-store", language, "none"), "postgres", language)
            self.assertEqual(axis_default("auth", language, "none"), "none", language)
        # The transport default is per backend because the options are: Fastify is not something a Go
        # project can be given, so one flat answer would refuse to generate on two backends out of three.
        self.assertEqual(
            {language: axis_default("http", language, "none") for language in CATALOG["backends"]},
            TRANSPORTS,
        )

        with tempfile.TemporaryDirectory() as directory:
            transports = TRANSPORTS
            for language, transport in transports.items():
                repo = self.generate(directory, f"default-{language}", language=language)
                selection = json.loads((repo / "project.json").read_text())["deployables"]["service"]["selection"]
                self.assertEqual(
                    selection, {"event-store": "postgres", "http": transport, "auth": "none", "users": "none"}, language
                )
                compose = (repo / "docker-compose.yml").read_text()
                self.assertIn("postgres", compose)
                # The axes stay independent: taking the event-store default does not bring an identity
                # provider along with it.
                self.assertNotIn("keycloak", compose)
                self.assertTrue((repo / ".env.example").is_file(), language)
                makefile = (repo / "Makefile").read_text()
                for target in ("services-up:", "services-down:", "migrate:"):
                    self.assertIn(target, makefile, language)
                self.assertIn("postgres", (repo / ".github/workflows/verify.yml").read_text())

            # The standard profile has no event-store port, so its default is the transport
            # alone rather than a store it cannot be given.
            plain = self.generate(directory, "default-cd", "standard", "typescript")
            self.assertEqual(
                json.loads((plain / "project.json").read_text())["deployables"]["service"]["selection"],
                {"http": "fastify", "auth": "none", "users": "none"},
            )
            # It still has a Compose file — the app itself is in there, which is what `make demo` runs —
            # but nothing in it is a backing service, so there is no `make services-up` to be had.
            compose = self.settings((plain / "docker-compose.yml").read_text())
            self.assertNotIn("postgres", compose)
            self.assertNotIn("keycloak", compose)
            self.assertNotIn("services-up:", (plain / "Makefile").read_text())

    def test_a_default_is_a_recommendation_a_backend_can_actually_be_given(self) -> None:
        """A language can be added before its adapters are, so an axis with nothing for a backend falls back
        to its no-infrastructure answer. What is refused is the other case: a backend that *can* be given a
        real answer and is left defaulting to none, which is a recommendation that silently stopped."""
        catalog = json.loads(json.dumps(CATALOG))
        catalog["backends"]["rust"] = {"family": "rust", "label": "Rust", "targets": ["none"]}
        self.assertEqual(
            {axis: catalog_axis_default(catalog, axis, "rust", "none") for axis in catalog["axes"]},
            {"event-store": "memory", "http": "none", "auth": "none", "users": "none"},
        )

        # The moment that backend has a transport of its own, the default has to name it.
        catalog["axes"]["http"]["options"]["rust-axum"] = {
            "capabilities": ["http-rust-axum"],
            "backends": ["rust"],
            "targets": ["none"],
            "containers": [],
            "migrations": False,
            "integration-suite": False,
            "label": "Axum",
            "features": [],
        }
        with self.assertRaisesRegex(ValueError, "http default names no answer for rust"):
            validate_axes(catalog)
        catalog["default"]["http"]["rust"] = "rust-axum"
        self.assertEqual(catalog_axis_default(catalog, "http", "rust", "none"), "rust-axum")

        # And a default naming an answer that backend cannot be built with is refused outright, rather
        # than falling back to nothing and generating a project nobody asked for.
        broken = json.loads(json.dumps(CATALOG))
        broken["axes"]["event-store"]["options"]["postgres"]["backends"] = ["typescript"]
        with self.assertRaisesRegex(ValueError, "'postgres' is not implemented for go"):
            validate_axes(broken)

    def test_the_documented_axis_coverage_is_the_catalog_s(self) -> None:
        """`docs/axes.md` states what each backend can be given, and prose cannot check itself.

        The page claims every axis is implemented for every backend. That claim is true today and is one
        commit away from not being: a language may legitimately be added before its adapters are, and the
        sentence would then be false with nothing to notice. So coverage is a table built from the same
        `axis_options` the command line refuses with, and a backend answering no axis has to appear here
        as a row of dashes or this fails.
        """
        rows: dict[str, list[list[str]]] = {}
        for line in (ROOT / "docs/axes.md").read_text().splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) != 1 + len(CATALOG["axes"]) or not cells[0].startswith("`"):
                continue
            backend = cells[0].strip("`")
            if backend not in CATALOG["backends"]:
                continue
            rows[backend] = [
                [] if cell == "\N{EM DASH}" else [option.strip().strip("`") for option in cell.split(",")]
                for cell in cells[1:]
            ]

        self.assertEqual(
            set(rows),
            set(CATALOG["backends"]),
            "docs/axes.md does not carry one coverage row per catalogued backend",
        )
        for backend, documented in rows.items():
            self.assertEqual(
                documented,
                [axis_options(axis, backend, "none") for axis in CATALOG["axes"]],
                f"docs/axes.md states the wrong axis coverage for {backend}",
            )

    def test_the_axes_are_asked_only_where_there_is_a_choice(self) -> None:
        for language in CATALOG["backends"]:
            # Every backend can be given every event store, and each has exactly one transport.
            self.assertTrue(axis_applies("event-store", "event-modelling", language, "none"), language)
            self.assertEqual(
                axis_options("event-store", language, "none"), ["memory", "sqlite", "postgres"], language
            )
            self.assertEqual(len(axis_options("http", language, "none")), 2, language)
            self.assertTrue(axis_applies("auth", "standard", language, "none"), language)
        # The event store belongs to the profile that has the port, so it is not a question the
        # standard profile is asked at all.
        self.assertFalse(axis_applies("event-store", "standard", "typescript", "none"))
        self.assertEqual(axis_options("http", "python", "none"), ["none", "fastapi"])
        self.assertEqual(axis_options("http", "go", "none"), ["none", "net-http"])

    def test_the_pruner_knows_every_family_the_catalog_offers(self) -> None:
        """A family the pruner has never heard of does not prune less — it refuses to prune at all.

        `project_language` reads `project.json`'s `language`, which is the family, and raises for anything
        outside its own tuple. Generation calls the pruner for any selection with a prunable feature, so a
        family missing from that tuple fails the whole backend at "project.json names an unsupported
        backend language" — a message about a generated project, raised while generating it, naming nothing
        a reader would connect to the tuple they forgot. So the catalog asserts the agreement up front.

        Driven from the pruner's side because the two halves of a disagreement are symmetric and only this
        one can be simulated: the catalog's own backend set is pinned by a literal in the same function.
        """
        self.assertEqual(set(PRUNER.LANGUAGES), set(families()))

        without_go = tuple(name for name in PRUNER.LANGUAGES if name != "go")
        with patch.object(PRUNER, "LANGUAGES", without_go), self.assertRaisesRegex(
            ValueError, "disagree about the language families"
        ):
            validate_catalog(CATALOG)

        with patch.object(PRUNER, "LANGUAGES", (*PRUNER.LANGUAGES, "rust")), self.assertRaisesRegex(
            ValueError, "disagree about the language families"
        ):
            validate_catalog(CATALOG)

        # Families, not backends: a second framework in a family the pruner already knows needs no entry
        # there, because both members generate a project whose manifest names the same language.
        promoted = json.loads(json.dumps(CATALOG))
        promoted["backends"]["go-plain"] = {
            "family": "go", "framework": "none", "label": "Framework-free", "targets": ["none"]
        }
        promoted["backends"]["go-fiber"] = {"family": "go", "framework": "fiber", "label": "Fiber", "targets": ["none"]}
        del promoted["backends"]["go"]
        promoted["default"]["framework"]["go"] = "none"
        self.assertEqual(set(PRUNER.LANGUAGES), set(catalog_families(promoted)))

    def test_the_in_memory_store_is_never_the_thing_that_gets_dropped(self) -> None:
        """It is what the port's contract runs against in `make verify`, so every answer ships it and no
        answer can take it away. That is why it is the axis's rather than an option's."""
        for option in CATALOG["axes"]["event-store"]["options"].values():
            self.assertNotIn("memory", option["features"])
        self.assertEqual(CATALOG["axes"]["event-store"]["always"], ["memory"])
        self.assertNotIn("memory", PRUNER.FEATURES)
        for answer in ("memory", "sqlite", "postgres"):
            selection = resolve_selection({"event-store": answer}, "event-modelling", "typescript", "none")
            self.assertIn("memory", selection.features)
            self.assertNotIn("memory", selection.prunable_features)

    def test_a_service_trait_is_declared_by_the_option_and_checked_before_anything_reads_it(self) -> None:
        """"Needs a container, migrations, its own integration suite" is a declaration, not a product name.

        It used to be the literal string `postgres`, branched on across fifteen modules, which is why a
        second container-backed store meant twinning every one of them. Now the option says so and the
        generator asks the selection — so the declaration has to be a contract rather than a convention: an
        option that leaves it unstated would generate a project whose `make ci` never migrates and whose
        `make test-integration` runs nothing, with every gate still green.
        """
        catalog = json.loads(json.dumps(CATALOG))
        option = catalog["axes"]["event-store"]["options"]["sqlite"]
        del option["migrations"]
        with self.assertRaisesRegex(ValueError, "must declare whether it needs migrations"):
            validate_axes(catalog)
        # Stated, but not as an answer: a truthy string is the shape a hand-edited catalog acquires.
        option["migrations"] = "yes"
        with self.assertRaisesRegex(ValueError, "must declare whether it needs migrations"):
            validate_axes(catalog)

        # The axis's no-infrastructure answer cannot claim a trait: there is nothing there to migrate, and
        # nothing to prove against.
        catalog = json.loads(json.dumps(CATALOG))
        catalog["axes"]["event-store"]["options"]["memory"]["integration-suite"] = True
        with self.assertRaisesRegex(ValueError, "means no infrastructure, so nothing there needs"):
            validate_axes(catalog)

        # And a trait is carried by one marked region, named after one feature — so an option owning none
        # cannot claim one, because the region would have nothing to be called.
        catalog = json.loads(json.dumps(CATALOG))
        featureless = catalog["axes"]["auth"]["options"]["keycloak"]
        featureless["features"] = []
        featureless["migrations"] = True
        with self.assertRaisesRegex(ValueError, "must own exactly one feature"):
            validate_axes(catalog)

    def test_the_selection_answers_which_feature_owns_each_service_trait(self) -> None:
        """The question every site asks is "which feature", never "is it Postgres".

        Two answers to two different axes each owning the same trait is a real thing to want — a store and
        a deploy target that both migrate — and it needs one `make migrate` generalised first, so it is
        refused with the reason instead of emitted as a Makefile with two definitions of one target.
        """
        answers = {"event-store": "postgres", "http": "fastify", "auth": "keycloak", "users": "none"}
        selection = resolve_selection(dict(answers), "event-modelling", "typescript", "none")
        self.assertEqual(selection.migrating_feature, "postgres")
        self.assertEqual(selection.integration_feature, "postgres")
        # And the role that feature answers, which is what the generated `make migrate` help names.
        self.assertEqual(selection.axis_of("postgres"), "event-store")
        self.assertEqual(selection.feature_of("http"), "fastify")

        # A store that carries its own schema and is proved inside the Docker-free gate owns neither.
        embedded = resolve_selection({**answers, "event-store": "sqlite"}, "event-modelling", "typescript", "none")
        self.assertIsNone(embedded.migrating_feature)
        self.assertIsNone(embedded.integration_feature)
        # It still owns a feature — its adapter is prunable — which is exactly why the traits are declared
        # rather than inferred from whether the answer brought files.
        self.assertEqual(embedded.feature_of("event-store"), "sqlite")
        bare = resolve_selection({**answers, "event-store": "memory"}, "event-modelling", "typescript", "none")
        self.assertIsNone(bare.feature_of("event-store"))

        catalog = json.loads(json.dumps(CATALOG))
        catalog["axes"]["auth"]["options"]["keycloak"]["migrations"] = True
        with patch.dict(CATALOG["axes"], catalog["axes"], clear=True):
            contested = resolve_selection(dict(answers), "event-modelling", "typescript", "none")
            with self.assertRaisesRegex(GenerationError, "both declare migrations"):
                self.assertIsNone(contested.migrating_feature)

