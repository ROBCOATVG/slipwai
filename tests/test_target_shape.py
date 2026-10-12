"""What a `target.json` declares, and what the keel refuses before a cloud is ever reached.

A target package's manifest is the third of three, and it is held the way the other two are: on the
publisher's machine, where the fault can be fixed, rather than at generation time where it becomes somebody
else's problem. The rows it declares are the ones `catalog.json` has always carried for `aws` and `azure` —
the label a prompt shows, the axes the target cannot take the no-infrastructure answer to, the words its
cloud refuses inside a name, and whether the keel provisions it at all.
"""
from __future__ import annotations

import unittest

import checkout_packages  # noqa: F401

from slipwai import target_shape

MANIFEST = {
    "name": "cumulus",
    "label": "Cumulus — one container per app behind its own balancer",
    "description": "Where a project goes when it goes to Cumulus",
    "kind": "target",
    "core": ">=9.0,<10",
    "managed": True,
    "requires": ["http"],
    "reserved": {"anywhere": ["cumulus"]},
}


def refusal(**changes: object) -> str:
    """The one line `validate` refuses a manifest with these changes on it."""
    manifest = {**MANIFEST, **changes}
    for key, value in list(manifest.items()):
        if value is None:
            del manifest[key]
    try:
        target_shape.validate(manifest)
    except ValueError as error:
        return str(error)
    raise AssertionError(f"{changes} was not refused")


class ValidateTest(unittest.TestCase):
    def test_a_whole_manifest_is_accepted(self) -> None:
        target_shape.validate(MANIFEST)

    def test_the_kind_says_which_of_the_three_a_package_is(self) -> None:
        said = refusal(kind="language")
        self.assertIn("language.json", said)
        self.assertIn("extension.json", said)

    def test_a_name_that_is_not_a_slug_is_refused_saying_what_it_becomes(self) -> None:
        self.assertIn("directory", refusal(name="Cumulus Cloud"))

    def test_every_required_field_is_named_when_it_is_missing(self) -> None:
        for field in target_shape.REQUIRED:
            with self.subTest(field=field):
                self.assertIn(f"`{field}`", refusal(**{field: None}))

    def test_a_field_the_keel_does_not_read_is_refused_with_the_list_of_what_it_does(self) -> None:
        said = refusal(weather={"forecast": "fine"})
        self.assertIn("weather", said)
        self.assertIn("label", said)

    def test_an_axis_list_that_is_not_a_list_of_names_is_refused(self) -> None:
        self.assertIn("requires", refusal(requires="http"))

    def test_a_reserved_class_the_keel_does_not_know_is_refused_naming_the_three(self) -> None:
        said = refusal(reserved={"somewhere": ["cumulus"]})
        for how in ("anywhere", "word", "prefix"):
            self.assertIn(how, said)

    def test_a_reserved_word_a_project_name_could_never_carry_is_refused(self) -> None:
        self.assertIn("lowercase", refusal(reserved={"anywhere": ["Cumulus!"]}))

    def test_a_target_that_provisions_nothing_reserves_nothing(self) -> None:
        """The rule `targets.validate_targets` already holds the catalog to: a target that creates nothing
        names nothing after the project, so it has no name to have refused."""
        self.assertIn("reserves no words", refusal(managed=False))

    def test_managed_is_a_yes_or_a_no_and_not_a_word(self) -> None:
        self.assertIn("managed", refusal(managed="yes"))

    def test_a_target_may_be_unmanaged_and_then_declares_no_reserved_words(self) -> None:
        target_shape.validate({**MANIFEST, "managed": False, "reserved": {}})

    def test_the_name_none_is_refused_because_the_keel_already_has_it(self) -> None:
        """`none` is local only and is the one row every catalog must carry; a package claiming it would
        replace the answer that is always offered."""
        self.assertIn("none", refusal(name="none"))


class CatalogueEntryTest(unittest.TestCase):
    def test_the_entry_is_the_row_catalog_json_has_always_carried(self) -> None:
        self.assertEqual(target_shape.catalogue_entry(MANIFEST), {
            "label": MANIFEST["label"],
            "requires": ["http"],
            "reserved": {"anywhere": ["cumulus"]},
            "managed": True,
        })

    def test_what_is_not_declared_is_left_out_rather_than_written_empty(self) -> None:
        """A row with `"requires": []` on it reads as a decision somebody made; an absent key does not."""
        entry = target_shape.catalogue_entry({**MANIFEST, "managed": False, "requires": [], "reserved": {}})
        self.assertEqual(entry, {"label": MANIFEST["label"]})


if __name__ == "__main__":
    unittest.main()


class MenuTest(unittest.TestCase):
    """The three blocks that say what this target does to the menus — the ones that let a cloud leave the
    keel at all, because every option that named a cloud named it because the cloud offered it."""

    def test_a_whole_set_of_menu_blocks_is_accepted(self) -> None:
        target_shape.validate({**MANIFEST,
                               "offers": {"persistence": ["memory"]},
                               "provisions": {"persistence": {"postgres": "cumulus-sql"}},
                               "axes": {"auth": {"cirrus-id": {"label": "Cirrus ID"}}}})

    def test_offers_that_is_not_a_mapping_to_names_is_refused(self) -> None:
        self.assertIn("offers", refusal(offers={"persistence": "memory"}))

    def test_provisions_that_does_not_say_what_an_option_becomes_is_refused(self) -> None:
        self.assertIn("provisions", refusal(provisions={"persistence": {"postgres": ""}}))

    def test_provisions_that_is_not_a_mapping_per_axis_is_refused(self) -> None:
        self.assertIn("provisions", refusal(provisions={"persistence": ["postgres"]}))

    def test_an_axes_block_whose_options_are_not_entries_is_refused(self) -> None:
        self.assertIn("axes", refusal(axes={"auth": {"cirrus-id": "Cirrus ID"}}))

    def test_an_unmanaged_target_brings_no_answer_of_its_own(self) -> None:
        """An option offered only where this target is installed is one nothing here could build."""
        said = refusal(managed=None, reserved=None, axes={"auth": {"cirrus-id": {"label": "x"}}})
        self.assertIn("brings no answer of its own", said)
