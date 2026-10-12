"""The catalogue the keel ships, and the one boundary where a fault in it becomes a refusal.

`catalog.json` is the questions the keel asks. It carries no backend at all: a backend is a package's to
declare, and a keel that named one would be a keel a new language has to be edited into. What it does
carry — the five axes, the targets, the profiles, the frontends, the extensions — is held here against
three things at once: its own schema, the pruner that ships into every generated project, and the
registry of whatever is loaded.

`validate_axes` and `validate_targets` are tested here rather than in `test_validators.py` because both
hold the catalogue against `assets/backing-services/prune.py`, and a catalogue built in a test fails on
that mirror before it reaches the rule under test. This is the file that has the real one.
"""
from __future__ import annotations

import copy
import json
import unittest

import checkout_packages  # noqa: F401

from slipwai.assets import PRUNER, ROOT
from slipwai.axes import validate_axes
from slipwai.catalog import CATALOG, PACKAGES, SCHEMA_VERSION, TARGETS
from slipwai.catalog_checks import check_rung, validate_catalog
from slipwai.errors import Refusal
from slipwai.registry import load, registry
from slipwai.targets import validate_targets

#: The targets this checkout has installed. The two validators take it because a packaged
#: target's contribution reaches a project's pruner through the emission that writes it there,
#: so the keel's own static copy has nothing to mirror for one.
PACKAGED = [package.name for package in TARGETS]

EMPTY = load([])
SHIPPED = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))


class ShippedCatalogTest(unittest.TestCase):
    def test_the_keel_ships_no_backend(self) -> None:
        """Theme A's line, in one assertion: the keel declares the questions, a package the answers.
        `catalog.json` on disk has none; `CATALOG` in memory has whatever is installed merged in."""
        self.assertEqual(SHIPPED["backends"], {})

    def test_the_backend_in_the_merged_catalogue_came_from_a_package(self) -> None:
        self.assertEqual(set(CATALOG["backends"]), {"toy-plain"})

    def test_the_whole_catalogue_validates_against_the_registry_it_describes(self) -> None:
        """The catalogue and the registry are two halves of one answer: every backend listed has an
        object behind it, and every object has a row. Held against the process's own registry, which is
        the toy package merged in."""
        validate_catalog(CATALOG, loaded=registry())

    def test_a_catalogue_holding_a_backend_the_registry_has_not_is_refused(self) -> None:
        """Which is what an empty registry makes of a catalogue the toy is merged into."""
        with self.assertRaises(Refusal) as raised:
            validate_catalog(CATALOG, loaded=EMPTY)
        self.assertIn("no registry object", str(raised.exception))

    def test_the_axes_are_the_five_the_keel_asks_about(self) -> None:
        self.assertEqual(
            set(SHIPPED["axes"]), {"write-model", "persistence", "http", "auth", "users"}
        )

    def test_the_rung_is_an_axis_and_not_a_profile(self) -> None:
        """Phase 15's whole point, in three assertions. Event sourcing is what `write-model: events`
        gives a service; no profile hands it out, and a project may hold one service on each rung."""
        rungs = SHIPPED["axes"]["write-model"]["options"]
        self.assertEqual(list(rungs), ["events", "state"])
        self.assertEqual(rungs["events"]["capabilities"], ["event-sourcing"])
        self.assertEqual(rungs["state"]["capabilities"], [])
        for name, profile in SHIPPED["profiles"].items():
            self.assertNotIn("event-sourcing", profile["capabilities"], name)

    def test_the_rung_is_the_one_answer_init_may_not_move(self) -> None:
        """Every other axis can be answered down later; a rung cannot, so it is never a prune flag."""
        self.assertIs(SHIPPED["axes"]["write-model"]["prunable"], False)
        for axis, spec in SHIPPED["axes"].items():
            if axis != "write-model":
                self.assertNotIn("prunable", spec, axis)

    def test_the_schema_version_is_the_one_the_code_speaks(self) -> None:
        self.assertEqual(SHIPPED["schemaVersion"], SCHEMA_VERSION)

    def test_the_toy_package_is_the_one_this_keel_reads(self) -> None:
        """One package, in-tree, and no first-party one: a keel whose gate checks seven packages is a
        keel that cannot be changed without them."""
        self.assertEqual([package.name for package in PACKAGES], ["toy"])


class MirrorTest(unittest.TestCase):
    """The catalogue and the pruner hold the same tables, and each refuses a catalogue that drifts.

    The pruner ships into a generated project as `scripts/backing-services.py` and prunes it to what was
    selected. Two implementations of one prune would be two sets of bugs, so there is one file and the
    catalogue is held to it — which is the check that cannot be tested against a catalogue made up here.
    """

    def test_the_axes_agree_with_the_pruner(self) -> None:
        validate_axes(CATALOG, PACKAGED)

    def test_the_targets_agree_with_the_pruner(self) -> None:
        validate_targets(CATALOG, PACKAGED)

    def test_the_pruner_knows_every_feature_the_keel_itself_offers(self) -> None:
        """The keel's copy carries the infrastructure features and no framework. A feature a package's
        option brought is in the package and in the project's copy, and in neither of these."""
        offered = {feature for axis in CATALOG["axes"].values()
                   for option in axis["options"].values() for feature in option.get("features", [])}
        self.assertLessEqual(set(PRUNER.FEATURES), offered)
        self.assertNotIn("toy-serve", PRUNER.FEATURES)
        self.assertIn("toy-serve", offered)

    def test_an_option_offered_somewhere_the_pruner_does_not_know_about_is_refused(self) -> None:
        """Drift in either direction is a project that prunes to something the catalogue did not promise."""
        drifted = copy.deepcopy(CATALOG)
        axis = drifted["axes"]["persistence"]
        name = next(n for n in axis["options"] if n != axis["absent"])
        axis["options"][name]["targets"] = ["none"]
        with self.assertRaises(ValueError) as raised:
            validate_axes(drifted, PACKAGED)
        self.assertIn("prune.py", str(raised.exception))

    def test_a_managed_target_with_no_package_behind_it_is_refused(self) -> None:
        """A catalogue entry with nothing behind it generates projects claiming a destination they
        cannot reach, which is the half-ported shape the keel refuses everywhere else. Since phase 10 the
        infrastructure travels inside the package, so "nothing behind it" means no package of that name."""
        drifted = copy.deepcopy(CATALOG)
        drifted["targets"]["gcp"] = {"label": "GCP", "managed": True, "requires": []}
        with self.assertRaises(ValueError) as raised:
            validate_targets(drifted, PACKAGED)
        said = str(raised.exception)
        self.assertIn("gcp", said)
        self.assertIn("target install gcp", said)


class RungTest(unittest.TestCase):
    """The three rules that replaced the indivisible bundle, each refused by name.

    The bundle welded Event Modeling to event sourcing in the profile, so a product that wanted the model
    and not the log could not be generated. These hold the catalogue to the shape that replaced it: the
    rung is an axis answer, per service, and the profile only says whether there is a model at all.
    """

    def refuse(self, catalog: dict) -> str:
        with self.assertRaises(ValueError) as raised:
            check_rung(catalog)
        return str(raised.exception)

    def test_the_shipped_catalogue_keeps_all_three(self) -> None:
        check_rung(CATALOG)

    def test_a_profile_handing_out_event_sourcing_is_refused(self) -> None:
        drifted = copy.deepcopy(CATALOG)
        drifted["profiles"]["event-modelling"]["capabilities"].append("event-sourcing")
        self.assertIn("rung a service stands on", self.refuse(drifted))

    def test_a_rung_that_gives_nothing_is_refused(self) -> None:
        """`events` is where the capability lives now; without it a project would model and never say so."""
        drifted = copy.deepcopy(CATALOG)
        drifted["axes"]["write-model"]["options"]["events"]["capabilities"] = []
        self.assertIn("event-sourcing capability", self.refuse(drifted))

    def test_a_modelled_profile_missing_either_axis_is_refused(self) -> None:
        for axis in ("write-model", "persistence"):
            with self.subTest(axis=axis):
                drifted = copy.deepcopy(CATALOG)
                drifted["axes"][axis]["profiles"] = ["standard"]
                self.assertIn(f"must offer the {axis} axis", self.refuse(drifted))


class RefusalBoundaryTest(unittest.TestCase):
    """Where a schema fault becomes something a person reads.

    The validators underneath raise `ValueError` and say what is wrong; only here is it known whether a
    reader can do anything about it. With packages loaded the catalogue is theirs as much as the keel's,
    and `list` shows whose. With none, a wrong catalogue is a bug in this keel, and the refusal ends
    without a command rather than sending the reader somewhere useless.
    """

    def refuse(self, catalog: dict) -> Refusal:
        with self.assertRaises(Refusal) as raised:
            validate_catalog(catalog, loaded=EMPTY)
        return raised.exception

    def test_a_fault_reaches_the_reader_as_one_line(self) -> None:
        said = str(self.refuse({**CATALOG, "schemaVersion": "1.0"}))
        self.assertEqual(len(said.splitlines()), 1)
        self.assertIn('catalog schemaVersion must be "9.0"', said)

    def test_a_refusal_is_a_refusal_and_not_a_bare_value_error(self) -> None:
        """So a verb catches one kind of thing. `ValueError` is the validators' word, not the keel's."""
        self.assertIsInstance(self.refuse({**CATALOG, "schemaVersion": "1.0"}), Refusal)

    def test_with_a_package_installed_the_refusal_names_the_command_that_shows_whose(self) -> None:
        """The merged catalogue is the packages' as much as the keel's, so `list` is what shows whose."""
        refusal = self.refuse({**CATALOG, "schemaVersion": "1.0"})
        self.assertEqual(len(refusal.faults), 1)
        self.assertIsNotNone(refusal.faults[0].fix)
        self.assertIn("list", str(refusal.faults[0].fix))

    def test_the_underlying_value_error_is_kept_as_the_cause(self) -> None:
        """A keel bug should still have a traceback that points at the rule that fired."""
        with self.assertRaises(Refusal) as raised:
            validate_catalog({**CATALOG, "schemaVersion": "1.0"}, loaded=EMPTY)
        self.assertIsInstance(raised.exception.__cause__, ValueError)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
