"""A target's row, folded into the catalog: what a cloud adds to the tables when it is installed.

The keel's `catalog.json` carries `none` and `existing` and no cloud. Everything a cloud contributes — the
row the prompt shows, the answers it offers, what each of them is provisioned as there, and the answers that
are its own and nowhere else — arrives through this merge, which is the targets' half of what
`catalog_merge` and `catalog_options` are for a language.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.target_directory import TargetPackage, merge_targets

CORE: dict = {
    "targets": {"none": {"label": "Local only"}, "existing": {"label": "Somewhere else"}},
    "axes": {
        "persistence": {"absent": "memory", "options": {
            "memory": {"label": "In memory", "backends": [], "targets": ["none", "existing"]},
            "postgres": {"label": "Postgres", "backends": [], "targets": ["none", "existing"]},
        }},
        "auth": {"absent": "none", "options": {
            "none": {"label": "None", "backends": [], "targets": ["none", "existing"]},
        }},
        "http": {"absent": "none", "options": {
            "none": {"label": "None", "backends": [], "targets": ["none", "existing"]},
        }},
    },
}

MANIFEST = {
    "name": "cumulus", "label": "Cumulus — one box per app", "description": "Where a project goes",
    "kind": "target", "core": ">=9.0,<10", "managed": True, "requires": ["http"],
    "offers": {"persistence": ["memory"], "auth": ["none"]},
    "provisions": {"persistence": {"postgres": "managed-postgres"}},
    "axes": {"auth": {"cirrus-id": {"label": "Cirrus ID", "capabilities": ["auth-cirrus"],
                                    "features": ["keycloak"]}}},
}


def package(name: str = "cumulus", **changed: object) -> TargetPackage:
    return TargetPackage(name, Path(tempfile.gettempdir()) / name, {**MANIFEST, "name": name, **changed})


def merged(*packages: TargetPackage) -> tuple[dict, list[str]]:
    catalog = copy.deepcopy(CORE)
    return catalog, merge_targets(catalog, list(packages))


class RowTest(unittest.TestCase):
    def test_an_installed_target_becomes_a_row_the_prompt_can_show(self) -> None:
        catalog, refusals = merged(package())
        self.assertEqual(refusals, [])
        self.assertEqual(catalog["targets"]["cumulus"],
                         {"label": MANIFEST["label"], "requires": ["http"], "managed": True})

    def test_the_keels_own_rows_are_left_as_they_were(self) -> None:
        catalog, _ = merged(package())
        self.assertEqual(sorted(catalog["targets"]), ["cumulus", "existing", "none"])

    def test_a_target_claiming_a_name_something_already_holds_is_refused_and_changes_nothing(self) -> None:
        catalog, refusals = merged(package(name="existing"))
        self.assertEqual(len(refusals), 1)
        self.assertIn("existing", refusals[0])
        self.assertEqual(catalog["targets"]["existing"], CORE["targets"]["existing"])

    def test_one_refused_target_does_not_stop_another_merging(self) -> None:
        catalog, refusals = merged(package(name="existing", axes={}), package())
        self.assertEqual(len(refusals), 1)
        self.assertIn("cumulus", catalog["targets"])

    def test_a_target_requiring_an_axis_the_keel_does_not_declare_is_refused(self) -> None:
        """The manifest's shape is the publisher's to get right; whether `http` exists is this keel's fact."""
        catalog, refusals = merged(package(requires=["telepathy"]))
        self.assertEqual(len(refusals), 1)
        self.assertIn("telepathy", refusals[0])
        self.assertNotIn("cumulus", catalog["targets"])


class OffersTest(unittest.TestCase):
    def test_an_option_the_target_offers_gains_it_among_the_targets_it_is_offered_under(self) -> None:
        catalog, _ = merged(package())
        self.assertEqual(catalog["axes"]["persistence"]["options"]["memory"]["targets"],
                         ["none", "existing", "cumulus"])

    def test_an_option_the_target_does_not_offer_is_untouched(self) -> None:
        catalog, _ = merged(package(offers={"persistence": ["memory"]}, provisions={}))
        self.assertEqual(catalog["axes"]["persistence"]["options"]["postgres"]["targets"], ["none", "existing"])

    def test_an_option_the_target_provisions_is_offered_there_without_being_listed_twice(self) -> None:
        """Provisioning something is offering it: a row saying what `postgres` becomes here and a second row
        saying it is offered here would be two statements of one fact, and a manifest can carry only one."""
        catalog, _ = merged(package())
        option = catalog["axes"]["persistence"]["options"]["postgres"]
        self.assertEqual(option["targets"], ["none", "existing", "cumulus"])
        self.assertEqual(option["cumulus"], {"provisions": "managed-postgres"})

    def test_offering_an_option_the_keel_does_not_declare_is_refused(self) -> None:
        catalog, refusals = merged(package(offers={"persistence": ["tape"]}))
        self.assertEqual(len(refusals), 1)
        self.assertIn("tape", refusals[0])
        self.assertNotIn("cumulus", catalog["targets"])

    def test_offering_against_an_axis_the_keel_does_not_declare_is_refused(self) -> None:
        catalog, refusals = merged(package(offers={"telepathy": ["none"]}))
        self.assertIn("telepathy", refusals[0])
        self.assertNotIn("cumulus", catalog["targets"])

    def test_a_refused_target_leaves_no_half_merged_offer_behind(self) -> None:
        """The whole of one package's contribution lands or none of it does: a catalog carrying an option
        offered under a target that is not in the targets block is one nothing can resolve a default against."""
        catalog, _ = merged(package(offers={"persistence": ["memory", "tape"]}))
        self.assertEqual(catalog["axes"]["persistence"]["options"]["memory"]["targets"], ["none", "existing"])


class OwnOptionsTest(unittest.TestCase):
    def test_an_option_the_target_brings_is_declared_and_offered_only_there(self) -> None:
        catalog, refusals = merged(package())
        self.assertEqual(refusals, [])
        option = catalog["axes"]["auth"]["options"]["cirrus-id"]
        self.assertEqual(option["label"], "Cirrus ID")
        self.assertEqual(option["targets"], ["cumulus"])
        self.assertEqual(option["backends"], [])

    def test_an_option_the_target_brings_and_provisions_carries_both(self) -> None:
        catalog, _ = merged(package(provisions={"auth": {"cirrus-id": "cirrus"}}))
        self.assertEqual(catalog["axes"]["auth"]["options"]["cirrus-id"]["cumulus"], {"provisions": "cirrus"})

    def test_a_target_may_not_declare_an_option_the_keel_already_has(self) -> None:
        catalog, refusals = merged(package(axes={"persistence": {"postgres": {"label": "x"}}}))
        self.assertIn("postgres", refusals[0])
        self.assertEqual(catalog["axes"]["persistence"]["options"]["postgres"]["label"], "Postgres")

    def test_two_targets_declaring_one_option_are_both_refused_rather_than_one_preferred(self) -> None:
        other = package(name="stratus", axes=MANIFEST["axes"], offers={}, provisions={})
        catalog, refusals = merged(package(), other)
        self.assertEqual(len(refusals), 2)
        self.assertNotIn("cirrus-id", catalog["axes"]["auth"]["options"])


class ShapeTest(unittest.TestCase):
    def test_nothing_installed_leaves_the_catalog_exactly_as_the_keel_wrote_it(self) -> None:
        catalog, refusals = merged()
        self.assertEqual((catalog, refusals), (CORE, []))

    def test_the_merge_does_not_alias_the_manifest_it_read(self) -> None:
        """A catalog holding the manifest's own lists would let a later edit of one change the other."""
        one = package()
        catalog, _ = merged(one)
        catalog["axes"]["auth"]["options"]["cirrus-id"]["capabilities"].append("extra")
        self.assertEqual(one.manifest["axes"]["auth"]["cirrus-id"]["capabilities"], ["auth-cirrus"])

    def test_a_refusal_is_one_line_naming_the_target_and_its_directory(self) -> None:
        _, refusals = merged(package(requires=["telepathy"]))
        self.assertIn("target cumulus", refusals[0])
        self.assertNotIn("\n", refusals[0])


class SerialisableTest(unittest.TestCase):
    def test_the_merged_catalog_is_still_json(self) -> None:
        """It is written into a generated project's own copy, so nothing in it may be a Python object."""
        catalog, _ = merged(package())
        self.assertIsInstance(json.dumps(catalog), str)


if __name__ == "__main__":
    unittest.main()
