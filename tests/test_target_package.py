"""A target as a package: listed in a channel, scaffolded by `package new`, and built into a release.

The third kind. Everything here is about the parts that had to learn a third word — the index document, the
channel's own check and its front page, `search --kind`, and the four verbs a publisher uses — so what is
proved is that none of them has two kinds hard-wired into it any more.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import package_new
from slipwai.channel import shape_findings
from slipwai.channel_page import page
from slipwai.cli_search import matches
from slipwai.errors import GenerationError
from slipwai.index_schema import KINDS, TARGET, Index, entry_of, releases_of
from slipwai.language_release import read_package
from slipwai.package_release import kind_of

CORE = "9.0"
DOCUMENT = "https://example.invalid/slipwai-languages/index.json"
MANIFEST = {
    "name": "cumulus", "label": "Cumulus — a cloud", "description": "Where a project goes",
    "kind": "target", "core": ">=9.0,<10", "managed": True, "requires": ["http"],
}


def entry(**extra: object) -> dict:
    return {"version": "1.0.0", "file": "cumulus-1.0.0.tar.gz", "sha256": "0" * 64,
            "kind": "target", "target": MANIFEST, **extra}


class IndexTest(unittest.TestCase):
    def test_target_is_one_of_the_kinds_an_index_may_list(self) -> None:
        self.assertIn(TARGET, KINDS)

    def test_a_target_entry_carries_its_manifest_under_its_own_key(self) -> None:
        found = entry_of(DOCUMENT, "cumulus", entry())
        assert found is not None
        self.assertEqual((found.kind, found.name), (TARGET, "cumulus"))
        self.assertEqual(found.fragment["label"], MANIFEST["label"])
        self.assertTrue(found.is_target)

    def test_an_entry_with_no_kind_field_is_read_from_the_manifest_it_carries(self) -> None:
        """A hand-written entry that forgot the field works rather than vanishing, as the other two do."""
        found = entry_of(DOCUMENT, "cumulus", {k: v for k, v in entry().items() if k != "kind"})
        assert found is not None
        self.assertEqual(found.kind, TARGET)

    def test_a_manifest_whose_name_is_not_the_name_it_is_listed_under_is_dropped(self) -> None:
        self.assertIsNone(entry_of(DOCUMENT, "nimbus", entry()))

    def test_a_manifest_that_declares_no_label_is_dropped(self) -> None:
        """The label is the sentence the prompt shows; an entry with none could not be offered."""
        bare = {key: value for key, value in MANIFEST.items() if key != "label"}
        self.assertIsNone(entry_of(DOCUMENT, "cumulus", entry(target=bare)))

    def test_a_document_listing_one_of_each_kind_reads_all_three(self) -> None:
        document = {"index": 2, "packages": {"cumulus": [entry()]}}
        found = releases_of(DOCUMENT, document, 2)
        self.assertEqual([release.kind for release in found["cumulus"]], [TARGET])


class ChannelTest(unittest.TestCase):
    def test_a_channel_accepts_an_entry_of_the_third_kind(self) -> None:
        self.assertEqual(shape_findings({"name": "cumulus", **entry()}), [])

    def test_the_front_page_names_the_kind_and_offers_no_command_that_does_not_exist(self) -> None:
        """A target is listed and not installed. This keel reads a target out of a channel and has no verb
        that installs one — that arrives with the clouds themselves — so the page offers none, rather than
        printing `slipwai install cumulus`, which would look for a language of that name."""
        text = page("A channel", [{"name": "cumulus", **entry()}], "")
        self.assertIn("cumulus", text)
        self.assertIn(">target<", text)
        self.assertNotIn("slipwai install cumulus", text)


class SearchTest(unittest.TestCase):
    def test_a_search_narrowed_to_targets_leaves_the_other_kinds_out(self) -> None:
        one = entry_of(DOCUMENT, "cumulus", entry())
        assert one is not None
        index = Index(DOCUMENT, "a channel", {"cumulus": [one]})
        self.assertEqual([release.name for release in matches(index, "", TARGET)], ["cumulus"])
        self.assertEqual(matches(index, "", "language"), [])


class ScaffoldTest(unittest.TestCase):
    """What `package new --kind target` writes has to be what this keel reads back."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_a_scaffolded_target_declares_the_schema_this_keel_speaks(self) -> None:
        package_new.write("target", "cumulus", self.area, CORE)
        manifest = json.loads((self.area / "cumulus/target.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["core"], manifest["kind"]), (">=9.0,<10", "target"))

    def test_a_scaffolded_target_ships_both_shapes_and_the_module_that_names_them(self) -> None:
        package_new.write("target", "cumulus", self.area, CORE)
        for path in ("bootstrap/main.tf", "service/main.tf", "slipwai_target_cumulus/__init__.py"):
            with self.subTest(path=path):
                self.assertTrue((self.area / "cumulus" / path).is_file(), path)

    def test_its_module_is_named_after_the_package_as_a_language_s_is(self) -> None:
        self.assertEqual(package_new.target_module_of("two-clouds"), "slipwai_target_two_clouds")

    def test_a_kind_that_is_none_of_the_three_is_refused_naming_them(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            package_new.write("cloud", "cumulus", self.area, CORE)
        for kind in package_new.KINDS:
            self.assertIn(kind, str(refused.exception))


class ReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_a_directory_holding_a_target_json_is_a_target_package(self) -> None:
        package_new.write("target", "cumulus", self.area, CORE)
        self.assertEqual(kind_of(self.area / "cumulus"), TARGET)

    def test_a_release_is_named_after_the_name_the_manifest_gives(self) -> None:
        package_new.write("target", "cumulus", self.area, CORE)
        source = read_package(self.area / "cumulus")
        self.assertEqual((source.name, source.version), ("cumulus", "1.0.0.dev0"))

    def test_the_scaffold_opens_the_first_release_rather_than_claiming_it(self) -> None:
        """A snapshot of 1.0.0, which is what the version rule asks of a package that has cut none. A
        scaffold carrying a release number fails its own `check` on the line that says that release has no
        entry, which is the scaffold teaching a publisher that the tool is broken."""
        package_new.write("target", "cumulus", self.area, CORE)
        self.assertEqual((self.area / "cumulus/VERSION").read_text(encoding="utf-8"), "1.0.0.dev0\n")


if __name__ == "__main__":
    unittest.main()
