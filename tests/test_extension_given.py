"""A project's copy of an extension holds what runs or is read there, and not the package's repository (#119).

`extension_directory.files` is every file of a package, and that list was a project's `scripts/extensions/<key>/`:
so every project carried each package's workflows, its changelog and its tests, which nothing in a project runs
and an agent reads as though they were the project's. No git and no network: a package directory in a temporary
folder.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import toolkit
from slipwai.extension_copies import copies, differing
from slipwai.extension_directory import Extension, files
from slipwai.extension_given import WITHHELD, given, held_back
from slipwai.extension_shape import validate

MANIFEST = {"key": "indexer", "name": "Indexer", "description": "A test extension", "kind": "extension",
            "core": ">=9.0,<10", "hooks": {"init": "init.py", "check": "hooks/check.py"}}
#: A package as a publisher's repository holds it: what a project runs, and what only the repository needs.
PACKAGE = {
    "init.py": "import code_index\n", "code_index.py": "", "hooks/check.py": "from lib import shared\n",
    "lib/__init__.py": "", "lib/shared.py": "", "bin/tool": "#!/bin/sh\n", "skill/tests/kept.md": "",
    "README.md": "", "LICENSE": "", "NOTICE": "", "VERSION": "1.0.0\n",
    ".github/workflows/verify.yml": "", "CHANGELOG.md": "", "changelog.d/one.md": "", "tests/test_package.py": "",
    ".gitignore": "", ".gitattributes": "", "hooks/__pycache__/check.cpython-311.pyc": "",
}
REPOSITORY_ONLY = [".gitattributes", ".github/workflows/verify.yml", ".gitignore", "CHANGELOG.md",
                   "changelog.d/one.md", "hooks/__pycache__/check.cpython-311.pyc", "tests/test_package.py"]


def package(area: Path, manifest: dict | None = None, **more: str) -> Path:
    root = area / "indexer"
    for name, body in {**PACKAGE, **more}.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(body, encoding="utf-8")
    (root / "extension.json").write_text(json.dumps(manifest or MANIFEST), encoding="utf-8")
    return root


def names(paths: list[Path]) -> list[str]:
    return [path.as_posix() for path in paths]


class Case(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.area, True)


class GivenTest(Case):
    def test_a_project_is_not_given_what_only_the_packages_repository_needs(self) -> None:
        root = package(self.area)
        self.assertEqual(names(held_back(root, MANIFEST)), REPOSITORY_ONLY)
        self.assertEqual(names(given(root, MANIFEST)),
                         ["LICENSE", "NOTICE", "README.md", "VERSION", "bin/tool", "code_index.py", "hooks/check.py",
                          "init.py", "lib/__init__.py", "lib/shared.py", "skill/tests/kept.md"])

    def test_the_two_lists_are_the_whole_package_and_in_one_order_on_every_platform(self) -> None:
        root = package(self.area, None, **{"Zebra.md": "", "apple.md": ""})
        both = names(given(root, MANIFEST)) + names(held_back(root, MANIFEST))
        self.assertEqual(sorted(both), names(files(root)))
        self.assertEqual(names(given(root, MANIFEST)), sorted(names(given(root, MANIFEST))))

    def test_a_declared_script_is_given_wherever_it_sits_and_so_is_what_it_imports(self) -> None:
        manifest = {**MANIFEST, "hooks": {"init": "init.py", "check": "tests/check.py"},
                    "guards": {"before-search": "tests/guard.py"}}
        root = package(self.area, manifest, **{
            "tests/check.py": "import helper\nfrom tests.support import words\n", "tests/helper.py": "import deeper\n",
            "tests/deeper.py": "", "tests/__init__.py": "", "tests/support/__init__.py": "",
            "tests/support/words.py": "", "tests/guard.py": "", "tests/broken.py": "def (:\n"})
        kept = names(given(root, manifest))
        for path in ("tests/check.py", "tests/guard.py", "tests/helper.py", "tests/deeper.py", "tests/__init__.py",
                     "tests/support/__init__.py", "tests/support/words.py"):
            self.assertIn(path, kept)
        self.assertNotIn("tests/test_package.py", kept, "the rest of the folder is still the repository's")
        self.assertNotIn("tests/broken.py", kept)

    def test_a_manifest_adds_to_what_is_held_back_and_never_takes_away_a_script_it_declares(self) -> None:
        manifest = {**MANIFEST, "withhold": ["bin/", "NOTICE", "hooks/check.py"]}
        validate(manifest)
        root = package(self.area, manifest)
        kept = names(given(root, manifest))
        self.assertNotIn("bin/tool", kept)
        self.assertNotIn("NOTICE", kept)
        self.assertIn("hooks/check.py", kept, "a hook the manifest declares runs in a project")
        self.assertNotIn("CHANGELOG.md", kept, "the conventional list still holds")

    def test_a_withhold_that_is_not_a_list_of_paths_inside_the_package_is_refused(self) -> None:
        for wrong in ("tests/", [""], [3], ["../other"], ["/etc/passwd"], ["a\\b"]):
            with self.assertRaises(ValueError, msg=repr(wrong)) as raised:
                validate({**MANIFEST, "withhold": wrong})
            self.assertIn("withhold", str(raised.exception))

    def test_the_conventional_list_is_the_one_this_names(self) -> None:
        self.assertEqual(WITHHELD, (".github/", "changelog.d/", "tests/", "CHANGELOG.md", ".gitignore",
                                    ".gitattributes"))


class ProjectTest(Case):
    def test_a_generated_project_holds_only_what_it_is_given(self) -> None:
        root = package(self.area)
        with mock.patch.object(toolkit, "EXTENSIONS", [Extension("indexer", root, MANIFEST)]):
            written = toolkit.extension_files()
        copied = sorted(path.removeprefix("scripts/extensions/indexer/") for path in written
                        if path.startswith("scripts/extensions/indexer/"))
        self.assertEqual(copied, names(given(root, MANIFEST)))
        self.assertIn("scripts/extensions/available.json", written)


class CopyTest(Case):
    """An existing project's copy, after the migration that stopped giving it the repository's files."""

    def setUp(self) -> None:
        super().setUp()
        self.packages = self.area / "packages"
        self.package = package(self.packages)
        self.root = self.area / "project"
        self.copy = self.root / "scripts/extensions/indexer"
        shutil.copytree(self.package, self.copy)
        (self.copy / "extension.json").unlink()
        (self.root / ".slipwai").mkdir()
        (self.root / ".slipwai/extensions.json").write_text(json.dumps({"extensions": ["indexer"]}), encoding="utf-8")

    def test_a_copy_without_the_repositorys_files_is_the_installed_package(self) -> None:
        for name in REPOSITORY_ONLY:
            (self.copy / name).unlink()
        self.assertEqual(differing(self.copy, self.package), [])
        self.assertEqual(copies(self.root, {"name": "pir"}, self.packages), [])

    def test_a_file_no_longer_given_that_is_still_here_is_named_and_not_called_a_difference(self) -> None:
        for name in REPOSITORY_ONLY:
            if name != "CHANGELOG.md":
                (self.copy / name).unlink()
        (self.copy / "CHANGELOG.md").write_text("a note somebody wrote here\n", encoding="utf-8")
        self.assertEqual(differing(self.copy, self.package), [])
        section = copies(self.root, {"name": "pir"}, self.packages)
        self.assertEqual(section[1], "## Extension files a project is no longer given, and this one still has")
        self.assertEqual([line for line in section if line.startswith("- ")],
                         ["- `indexer` — `scripts/extensions/indexer/CHANGELOG.md`"])
        self.assertIn("git rm", "\n".join(section), "and what to do about it")

    def test_one_of_an_extension_nobody_elected_here_is_named_too(self) -> None:
        (self.root / ".slipwai/extensions.json").unlink()
        for name in REPOSITORY_ONLY[1:]:
            (self.copy / name).unlink()
        rows = [line for line in copies(self.root, {"name": "pir"}, self.packages) if line.startswith("- ")]
        self.assertEqual(rows, ["- `indexer` — `scripts/extensions/indexer/.gitattributes`"])


if __name__ == "__main__":
    unittest.main()
