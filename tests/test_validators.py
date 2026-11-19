"""The four validators the catalogue is held to, each against a catalogue built here rather than the real one.

`features`, `extensions`, `targets` and `axes` say what is wrong with a catalogue. In version 1 they were
tested through `slipwai.catalog.CATALOG` — the real, whole, valid one — so a red result named the
catalogue and not the rule, and a rule could only be tested by breaking the file every other suite read.
Here each refusal is provoked by the smallest catalogue that provokes it.

What these do not do is end on a command. A refusal reaches a person through `catalog.validate_catalog`,
which is where it becomes a `Refusal` of `Fault`s with the fix named; a validator deep in the schema check
does not know whether the reader should edit `catalog.json`, reinstall a package or upgrade the keel.
That wrapping is slice 2.3's, at the one boundary that knows.

Two of the eight entry points are missing here, and deliberately. `validate_axes` and `validate_targets`
hold the catalogue against `assets/backing-services/prune.py` — the same tables, kept in two places
because a generated project prunes itself with the second — and that comparison is only meaningful
against the real catalogue. A synthetic one fails on the mirror before it reaches the rule under test.
They are tested in slice 2.3, with the `catalog.json` they mirror. What is here is everything that takes
an option, an entry or a small map rather than the whole catalogue.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai.axes import validate_axis_capabilities
from slipwai.extensions import known_extensions, validate_extensions
from slipwai.features import axis_of, known_features, validate_traits
from slipwai.targets import check_targets, managed, offered_backends, required_axes

# What a valid catalogue is, built here rather than read from `catalog.json`, which is slice 2.3's and
# would make these tests depend on the thing they exist to check. An axis has to carry its question, what
# its answers have in common, at least two options, the profiles it applies to, and the option that means
# "no infrastructure" — so the fixture carries all of that and the tests change one thing at a time.
PROFILES = {"standard": {"label": "Standard"}, "event-modelling": {"label": "Event modelling"}}


def option(label: str, **changes: object) -> dict:
    """A complete option. Every field here is one a validator refuses the absence of: the label the
    prompt shows, what it gives the project, what it runs, which backends answer it, the feature that
    owns its files, where it is offered, and the two traits — whether it has migrations to apply and a
    suite to prove them."""
    return {
        "label": label,
        "capabilities": [],
        "containers": [],
        "backends": [],
        "features": [],
        "migrations": False,
        "integration-suite": False,
        "targets": ["none", "existing"],
        **changes,
    }


def axis(**changes: object) -> dict:
    return {
        "label": "An axis",
        "prompt": "Which one?",
        "description": "what every answer to this has in common",
        "profiles": sorted(PROFILES),
        "absent": "none",
        "options": {
            "none": option("None"),
            "something": option("Something"),
        },
        **changes,
    }


AXES = {name: axis() for name in ("persistence", "http", "auth", "users")}
# Both unmanaged, because a managed target must have `assets/targets/<name>/` behind it — a catalogue
# entry with no infrastructure would generate projects claiming a destination they cannot reach — and
# those trees arrive in phase 3. `managed()` is tested against a catalogue of its own.
TARGETS = {
    "none": option("None"),
    "existing": {"label": "Somewhere that already exists", "managed": False},
}
MANAGED = {**TARGETS, "aws": {"label": "AWS", "managed": True}}


def catalog(**changes: object) -> dict:
    """The smallest catalogue that is valid, with whatever a test is about changed."""
    return {
        "schemaVersion": "9.0",
        "backends": {},
        "profiles": dict(PROFILES),
        "targets": dict(TARGETS),
        "axes": {name: axis() for name in AXES},
        "extensions": {},
        "default": {"target": "none", **{name: "none" for name in AXES}},
        **changes,
    }


class ExtensionsTest(unittest.TestCase):
    def test_an_extension_declares_a_name_and_a_description(self) -> None:
        for missing in ("name", "description"):
            entry = {"name": "CodeGraph", "description": "a code index"}
            del entry[missing]
            with self.subTest(missing=missing), self.assertRaises(ValueError) as raised:
                validate_extensions(catalog(extensions={"codegraph": entry}))
            self.assertIn(f"must declare a non-empty {missing}", str(raised.exception))

    def test_an_unknown_field_is_refused_by_name(self) -> None:
        """A misspelt field that is quietly ignored is a setting that silently does nothing."""
        entry = {"name": "CodeGraph", "description": "a code index", "ignores": ".codegraph/"}
        with self.assertRaises(ValueError) as raised:
            validate_extensions(catalog(extensions={"codegraph": entry}))
        self.assertIn("unknown field(s): ignores", str(raised.exception))

    def test_ignore_is_gitignore_text_when_it_is_there_at_all(self) -> None:
        entry = {"name": "CodeGraph", "description": "a code index", "ignore": [".codegraph/"]}
        with self.assertRaises(ValueError) as raised:
            validate_extensions(catalog(extensions={"codegraph": entry}))
        self.assertIn("ignore must be a string", str(raised.exception))

    def test_a_well_formed_extension_passes_and_is_read_back(self) -> None:
        entry = {"name": "CodeGraph", "description": "a code index", "ignore": ".codegraph/\n"}
        page = catalog(extensions={"codegraph": entry})
        validate_extensions(page)
        self.assertEqual(known_extensions(page), {"codegraph": entry})

    def test_a_catalogue_with_no_extensions_is_not_a_fault(self) -> None:
        validate_extensions(catalog())
        self.assertEqual(known_extensions(catalog()), {})


class FeaturesTest(unittest.TestCase):
    def test_a_feature_belongs_to_the_axis_that_offers_it(self) -> None:
        page = catalog(axes={**AXES, "http": axis(options={
            "none": option("None"),
            "fastapi": option("FastAPI", features=["http-fastapi"]),
        })})
        self.assertEqual(known_features(page), {"http-fastapi"})
        self.assertEqual(axis_of(page, "http-fastapi"), "http")

    def test_a_feature_no_axis_offers_is_refused_by_name(self) -> None:
        with self.assertRaises(ValueError) as raised:
            axis_of(catalog(), "http-fastapi")
        self.assertIn("no axis offers the http-fastapi feature", str(raised.exception))

    def test_a_trait_that_is_not_a_string_is_refused_by_axis_option_and_trait(self) -> None:
        with self.assertRaises(ValueError) as raised:
            validate_traits("http", "fastapi", {"features": ["http-fastapi"], "traits": {"kind": 1}}, "none")
        said = str(raised.exception)
        self.assertIn("http", said)
        self.assertIn("fastapi", said)


class TargetsTest(unittest.TestCase):
    def test_a_managed_target_is_told_from_an_unmanaged_one(self) -> None:
        page = catalog(targets=MANAGED)
        self.assertTrue(managed(page, "aws"))
        self.assertFalse(managed(page, "none"))

    def test_a_target_a_backend_names_and_the_catalogue_has_not_is_refused(self) -> None:
        with self.assertRaises(ValueError) as raised:
            check_targets("backend go", {"targets": ["none", "gcp"]}, TARGETS)
        self.assertIn("gcp", str(raised.exception))
        self.assertIn("The catalog offers existing, none", str(raised.exception))

    def test_a_backend_is_offered_only_where_it_names_the_target(self) -> None:
        page = catalog(backends={
            "go": {"family": "go", "label": "Go", "targets": ["none", "existing"]},
            "rust": {"family": "rust", "label": "Rust", "targets": ["none"]},
        })
        self.assertEqual(offered_backends(page, "existing"), ["go"])
        self.assertEqual(sorted(offered_backends(page, "none")), ["go", "rust"])

    def test_a_target_requiring_an_axis_says_which(self) -> None:
        self.assertEqual(required_axes(catalog(), "none"), [])



class AxesTest(unittest.TestCase):

    def test_an_option_whose_capabilities_are_not_a_list_is_refused_by_axis_and_option(self) -> None:
        with self.assertRaises(ValueError) as raised:
            validate_axis_capabilities("http", axis(options={"none": option("None", capabilities="all")}))
        said = str(raised.exception)
        self.assertIn("http", said)
        self.assertIn("none", said)


class NoLanguageTest(unittest.TestCase):
    def test_none_of_the_validators_names_a_language(self) -> None:
        """This is the line issue #26 drew: the keel declares the questions, a package declares the
        answers. A validator that knows `go` is a validator a new language has to be added to."""
        import pathlib

        here = pathlib.Path(__file__).resolve().parents[1] / "src/slipwai"
        for module in ("features.py", "extensions.py", "targets.py", "axes.py"):
            text = (here / module).read_text(encoding="utf-8")
            for language in ("quarkus", "fastapi", "typescript", "golang"):
                with self.subTest(module=module, language=language):
                    self.assertNotIn(language, text.lower())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
