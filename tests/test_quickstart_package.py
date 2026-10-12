"""A quickstart travels: `kind: quickstart` through the chandlery and the four `slipwai package` verbs.

A language and an extension are both packages — one directory, one loader, one shape of release file, one
index — and a quickstart is the third. The alternative was a kit of parts that people passed around as a
file in a message, which is what every one of those verbs exists to stop.

The one rule of its own is that it names packages **by range, never by snapshot**: a quickstart published
today that pinned the version somebody happened to have installed would hold every team that installs it to
the afternoon it was written.
"""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import index_schema, package_new, quickstart, quickstart_install
from slipwai.cli_quickstart import check_quickstart
from slipwai.errors import GenerationError
from slipwai.index_schema import QUICKSTART
from slipwai.package_release import kind_of, register

DOCUMENT: dict[str, object] = {
    "quickstart": 1,
    "name": "toy-ui",
    "suits": "A product whose browser app is the product.",
    "core": ">=9.0,<10",
    "answers": {"profile": "event-modelling", "language": "toy", "axes": {"persistence": "postgres"}},
    "languages": [{"name": "toy", "version": ">=1.0,<2"}],
    "extensions": [],
}


def package(root: Path, document: dict | None = None) -> Path:
    """One quickstart package on disk: its manifest and the version a release is of."""
    whole = document or DOCUMENT
    place = root / str(whole["name"])
    place.mkdir(parents=True, exist_ok=True)
    (place / quickstart.MANIFEST).write_text(json.dumps(whole), encoding="utf-8")
    (place / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    return place


class RangeTest(unittest.TestCase):
    """The rule that is a quickstart's alone, held where the document is read rather than where it is sent."""

    def test_a_package_pinned_to_one_version_is_refused_naming_the_range(self) -> None:
        pinned = {**DOCUMENT, "languages": [{"name": "toy", "version": "==1.2.3"}]}
        with self.assertRaises(GenerationError) as refused:
            quickstart.read(pinned)
        self.assertIn("range", str(refused.exception))
        self.assertIn(">=", str(refused.exception))

    def test_a_version_that_is_not_a_range_at_all_is_refused(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            quickstart.read({**DOCUMENT, "languages": [{"name": "toy", "version": "1.2.3"}]})
        self.assertIn("toy", str(refused.exception))

    def test_a_range_with_both_ends_is_what_a_quickstart_names(self) -> None:
        self.assertEqual(quickstart.read(DOCUMENT).languages[0].version, ">=1.0,<2")


class IndexTest(unittest.TestCase):
    """What an index entry of this kind is, and what is dropped rather than half-read."""

    def entry(self, **changes: object) -> dict:
        return {"version": "1.0.0", "file": "toy-ui-1.0.0.tar.gz", "sha256": "a" * 64,
                "kind": QUICKSTART, QUICKSTART: DOCUMENT, **changes}

    def test_an_entry_is_read_as_a_release_of_this_kind(self) -> None:
        release = index_schema.entry_of("https://c/index.json", "toy-ui", self.entry())
        assert release is not None
        self.assertEqual(release.kind, QUICKSTART)
        self.assertTrue(release.is_quickstart)
        self.assertEqual(release.fragment["suits"], DOCUMENT["suits"])

    def test_the_kind_is_read_off_the_manifest_where_the_field_is_missing(self) -> None:
        """A hand-written entry that forgot `kind` is still what it plainly is."""
        entry = self.entry()
        del entry["kind"]
        release = index_schema.entry_of("https://c/index.json", "toy-ui", entry)
        assert release is not None
        self.assertEqual(release.kind, QUICKSTART)

    def test_one_listed_under_a_name_that_is_not_its_own_is_dropped(self) -> None:
        self.assertIsNone(index_schema.entry_of("https://c/index.json", "other", self.entry()))

    def test_one_with_no_sentence_about_the_product_is_dropped(self) -> None:
        """The sentence is what the interview offers it by; an entry without one cannot be offered."""
        document = {**DOCUMENT, "suits": ""}
        self.assertIsNone(index_schema.entry_of("https://c/i.json", "toy-ui", self.entry(quickstart=document)))


class VerbsTest(unittest.TestCase):
    """The four verbs a publisher uses, on a quickstart."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_new_writes_one_that_reads_and_checks(self) -> None:
        package_new.write(QUICKSTART, "ours", self.area, "9.0")
        root = self.area / "ours"
        self.assertTrue((root / quickstart.MANIFEST).is_file())
        self.assertEqual(kind_of(root), QUICKSTART)
        self.assertEqual(check_quickstart(root), 0)

    def test_check_refuses_one_whose_document_is_wrong_and_says_why(self) -> None:
        root = package(self.area, {**DOCUMENT, "suits": ""})
        self.assertEqual(check_quickstart(root), 1)

    def test_register_lists_it_in_the_channel_beside_the_languages(self) -> None:
        root = package(self.area)
        channel = self.area / "channel"
        _, entry_file, index = register(root, channel, publisher="us")
        document = json.loads(index.read_text(encoding="utf-8"))
        listed = document["packages"]["toy-ui"][0]
        self.assertEqual(listed["kind"], QUICKSTART)
        self.assertEqual(listed[QUICKSTART]["suits"], DOCUMENT["suits"])
        self.assertIn("toy-ui-1.0.0.json", entry_file.name)


class InstallTest(unittest.TestCase):
    """`slipwai quickstart install <name>`: the fetch that makes `--quickstart <name>` work with nothing
    else set up."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.home = Path(tempfile.mkdtemp())

    def channel(self) -> Path:
        root = package(self.area / "src")
        channel = self.area / "channel"
        (channel / "slipwai-languages").mkdir(parents=True)
        archive = channel / "slipwai-languages/toy-ui-1.0.0.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(root, arcname="toy-ui")
        (channel / "slipwai-languages/index.json").write_text(json.dumps({
            "index": 2,
            "packages": {"toy-ui": [{"version": "1.0.0", "file": "toy-ui-1.0.0.tar.gz", "kind": QUICKSTART,
                                     "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                                     "publisher": "ROBCOATVG", QUICKSTART: DOCUMENT}]},
        }), encoding="utf-8")
        return channel

    def install(self, name: str) -> list[str]:
        from slipwai.language_index import READ
        READ.clear()
        try:
            with mock.patch.dict(os.environ, {"SLIPWAI_INDEX": self.channel().as_uri()}):
                return quickstart_install.install([name], self.home)
        finally:
            READ.clear()

    def test_installing_one_makes_it_findable_by_name_with_nothing_else_set_up(self) -> None:
        self.install("toy-ui")
        with mock.patch.dict(os.environ, {quickstart.VARIABLE: str(self.home)}):
            self.assertEqual(quickstart.find("toy-ui").suits, DOCUMENT["suits"])
            self.assertEqual(quickstart.saved_names(), ["toy-ui"])

    def test_a_name_the_chandlery_has_not_got_says_what_lists_what_it_has(self) -> None:
        with self.assertRaises(GenerationError) as refused:
            self.install("absent")
        self.assertIn("search --kind quickstart", str(refused.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
