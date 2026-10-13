"""The catalogue read again, for the one process that installs packages into itself.

Built once at import is right for a verb: a command runs in a process of its own, and the package directory
cannot change underneath it. The board is the exception — it is one process, serving, and the packages tab
installs into the directory the catalogue was read from. Until this, a language installed from the page was
on disk, listed by the tab, and missing from the interview's menus until the server was restarted, which is
the one thing the person the board is for cannot do.

Every test here points the package directory at a temporary one and puts the pinned catalogue back
afterwards, because the thing under test is process-wide state and the suite shares a process.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import catalog
from slipwai.catalog import CATALOG, PACKAGES, REFUSALS, families, reread

FRAGMENT = {
    "name": "toy", "core": ">=9.0,<10", "order": 50, "family": "toy",
    "backends": {"toy": {"label": "Toy", "targets": ["none"],
                         "options": {"event-store": ["memory"], "http": ["none"]}}},
}


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.packages = Path(tempfile.mkdtemp())
        self.patch = mock.patch.dict(os.environ, {"SLIPWAI_LANGUAGES": str(self.packages)})
        self.patch.start()
        # The pinned catalogue back, whatever this test did to the process's own.
        self.addCleanup(reread)
        self.addCleanup(self.patch.stop)
        reread()

    def install(self, name: str = "toy", manifest: str = "language.json", **held: object) -> Path:
        """A package of any kind, written into the directory the way an install leaves one."""
        place = self.packages / name
        place.mkdir()
        (place / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        body = {**FRAGMENT, "name": name, "family": name, **held}
        if manifest == "extension.json":
            body = {"key": name, "name": name.title(), "kind": "extension", "core": ">=9.0,<10",
                    "description": "A local code index", **held}
        (place / manifest).write_text(json.dumps(body), encoding="utf-8")
        return place


class ListedTest(Fixture):
    """`slipwai list` under **Languages** lists languages, installed as well as offered.

    The four kinds share one directory and are told apart by the manifest each carries, and the installed
    half read every directory as a language — so a target installed beside a language was listed as one,
    with its version, under Languages. The offered half had the same fault from the index end.
    """

    def listed(self) -> str:
        from slipwai.cli_language import languages_section
        return "\n".join(languages_section(False)[0])

    def test_an_installed_target_is_not_listed_as_a_language(self) -> None:
        self.install("python")
        self.install("aws", manifest="target.json")
        said = self.listed()
        self.assertIn("python", said)
        self.assertNotIn("aws", said)

    def test_an_installed_extension_is_not_listed_as_a_language_either(self) -> None:
        self.install("python")
        self.install("codegraph", manifest="extension.json")
        self.assertNotIn("codegraph", self.listed())


class RereadTest(Fixture):
    def test_a_package_that_arrived_after_the_catalogue_was_built_is_in_it_after_a_reread(self) -> None:
        self.assertEqual(families(), {})
        self.install()
        self.assertEqual(families(), {}, "the catalogue read the directory again without being asked to")
        reread()
        self.assertEqual(families(), {"toy": ["toy"]})

    def test_the_readers_holding_the_table_see_the_new_one(self) -> None:
        """Thirty-odd modules did `from .catalog import CATALOG`. Rebinding the name here would leave every
        one of them on the table it replaced, which is a bug that would look exactly like no fix at all."""
        self.install()
        reread()
        self.assertIn("toy", CATALOG["backends"])
        self.assertEqual([package.name for package in PACKAGES], ["toy"])

    def test_an_extension_arrives_the_same_way(self) -> None:
        self.install("codegraph", manifest="extension.json")
        reread()
        self.assertIn("codegraph", CATALOG["extensions"])

    def test_a_package_that_cannot_be_read_is_a_line_and_not_an_empty_catalogue(self) -> None:
        self.install()
        (self.packages / "broken").mkdir()
        (self.packages / "broken" / "language.json").write_text("{not json", encoding="utf-8")
        reread()
        self.assertEqual(families(), {"toy": ["toy"]})
        self.assertTrue([line for line in REFUSALS if "broken" in line])

    def test_a_package_taken_out_of_the_directory_goes_out_of_the_catalogue(self) -> None:
        place = self.install()
        reread()
        self.assertIn("toy", families())
        for path in sorted(place.rglob("*"), reverse=True):
            path.unlink()
        place.rmdir()
        reread()
        self.assertEqual(families(), {})

    def test_the_caches_that_are_once_per_process_are_cleared(self) -> None:
        """`registry.registry` and `loaded_targets.loaded` are both `@cache`. This is the moment that
        stops being true, and a registry built before the install would import nothing new."""
        import importlib

        from slipwai.registry import registry
        self.install()
        reread()
        self.assertEqual(registry.cache_info().currsize, 0)
        self.assertEqual(importlib.import_module("slipwai.loaded_targets").loaded.cache_info().currsize, 0)

    def test_nothing_is_replaced_until_everything_could_be_read(self) -> None:
        """A directory that cannot be listed leaves the catalogue that was working in place, rather than
        emptying the menus of a board somebody is in the middle of using."""
        self.install()
        reread()
        with mock.patch.object(catalog, "built", side_effect=OSError("the disk went away")), \
                self.assertRaises(OSError):
            reread()
        self.assertEqual(families(), {"toy": ["toy"]})


if __name__ == "__main__":
    unittest.main()
