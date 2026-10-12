"""The target loader: a target package on disk, read and imported the way a language's is.

10.1 built the protocol and the manifest and deliberately built no loader, because nothing was installed
yet to load. 10.3 is what needs one: the moment `aws` leaves the keel, the only way the keel can know a
cloud is to read one out of the package directory.

Two halves, as the language has: the manifest, which is read without importing anything, and the Python,
which is imported from the package's own directory and asked for `TARGET`. A refused target is refused
alone and in one line — a second cloud installed beside a broken one still generates projects.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import target_directory
from slipwai.language_directory import Refused
from slipwai.language_directory import read as read_languages
from slipwai.target_protocol import Target

CORE = "9.0"
MANIFEST = {
    "name": "cumulus", "label": "Cumulus — one box per app", "description": "Where a project goes",
    "kind": "target", "core": ">=9.0,<10", "managed": True, "requires": ["http"],
    "reserved": {"anywhere": ["cumulus"]},
}

MODULE = '''
from slipwai.target_protocol import (
    DEPLOY_STEPS, DOCS_PAGES, IMAGE_REGISTRY, SCRIPTS, SHAPES, TOOLS, Target,
)

TARGET = Target(
    name="cumulus",
    answers={
        SHAPES: {"bootstrap": ("bootstrap/main.tf",), "service": ("service/main.tf",)},
        SCRIPTS: {"scripts/deploy.py": "scripts/deploy.py"},
        DOCS_PAGES: {"docs/deployment.md": lambda selection: "# Deployment\\n"},
        TOOLS: (("tofu", "what applies the stacks", "https://opentofu.org/"),),
        IMAGE_REGISTRY: {"repository": "cumulus.invalid/${project}", "login": "cumulus auth"},
        DEPLOY_STEPS: lambda environment: f"      - run: make deploy ENVIRONMENT={environment}\\n",
    },
)
'''


def write_target(root: Path, name: str = "cumulus", manifest: dict | None = None, module: str | None = None) -> Path:
    """A target package in `root`, whole enough to load: its manifest and its Python."""
    package = root / name
    (package / f"slipwai_target_{name}").mkdir(parents=True)
    declared = dict(MANIFEST if manifest is None else manifest)
    (package / "target.json").write_text(json.dumps(declared), encoding="utf-8")
    text = MODULE if module is None else module
    (package / f"slipwai_target_{name}" / "__init__.py").write_text(text, encoding="utf-8")
    return package


class ReadTest(unittest.TestCase):
    """The manifest half: what the walk keeps, what it skips and what it refuses."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.area, True)

    def test_a_directory_holding_a_target_json_is_read_as_a_target(self) -> None:
        write_target(self.area)
        found, refusals = target_directory.read(self.area, CORE)
        self.assertEqual(refusals, [])
        self.assertEqual([package.name for package in found], ["cumulus"])
        self.assertEqual(found[0].manifest["label"], MANIFEST["label"])

    def test_the_row_a_target_contributes_is_the_catalogs_own_four_fields(self) -> None:
        write_target(self.area)
        (found,), _ = target_directory.read(self.area, CORE)
        self.assertEqual(found.entry, {"label": MANIFEST["label"], "requires": ["http"],
                                       "reserved": {"anywhere": ["cumulus"]}, "managed": True})

    def test_a_language_package_is_skipped_rather_than_refused(self) -> None:
        """Both kinds share one directory, and each walk ignores what the other owns."""
        (self.area / "go").mkdir()
        (self.area / "go" / "language.json").write_text("{}", encoding="utf-8")
        found, refusals = target_directory.read(self.area, CORE)
        self.assertEqual((found, refusals), ([], []))

    def test_a_target_package_is_skipped_by_the_language_walk(self) -> None:
        """The other direction: `has no language.json` about a thing that never claimed to be one sends its
        reader to fix something that is not broken."""
        write_target(self.area)
        found, refusals = read_languages(self.area, CORE)
        self.assertEqual((found, refusals), ([], []))

    def test_a_target_json_that_is_not_json_is_refused_in_one_line_naming_the_directory(self) -> None:
        package = write_target(self.area)
        (package / "target.json").write_text("{not json", encoding="utf-8")
        found, refusals = target_directory.read(self.area, CORE)
        self.assertEqual(found, [])
        self.assertEqual(len(refusals), 1)
        self.assertIn("target cumulus", refusals[0])
        self.assertIn(str(package), refusals[0])
        self.assertNotIn("\n", refusals[0])

    def test_a_manifest_whose_name_is_not_its_directory_is_refused(self) -> None:
        write_target(self.area, name="nimbus")
        _, refusals = target_directory.read(self.area, CORE)
        self.assertEqual(len(refusals), 1)
        self.assertIn("cumulus", refusals[0])
        self.assertIn("nimbus", refusals[0])

    def test_a_target_built_for_another_schema_is_refused_with_the_move_that_fixes_it(self) -> None:
        write_target(self.area, manifest={**MANIFEST, "core": ">=10.0,<11"})
        _, refusals = target_directory.read(self.area, CORE)
        self.assertIn("upgrade", refusals[0])

    def test_one_refused_target_does_not_take_another_with_it(self) -> None:
        write_target(self.area)
        write_target(self.area, name="stratus", manifest={**MANIFEST, "name": "stratus", "label": "x"})
        (self.area / "stratus" / "target.json").write_text("{", encoding="utf-8")
        found, refusals = target_directory.read(self.area, CORE)
        self.assertEqual([package.name for package in found], ["cumulus"])
        self.assertEqual(len(refusals), 1)


class ImportTest(unittest.TestCase):
    """The Python half: `TARGET`, checked against the manifest and against the protocol."""

    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, self.area, True)
        self.addCleanup(target_directory.forget, "slipwai_target_cumulus")

    def one(self, **kwargs: object) -> target_directory.TargetPackage:
        write_target(self.area, **kwargs)  # type: ignore[arg-type]
        (package,), _ = target_directory.read(self.area, CORE)
        return package

    def test_the_packages_module_is_imported_and_its_target_returned(self) -> None:
        found = target_directory.import_package(self.one())
        self.assertIsInstance(found, Target)
        self.assertEqual(found.name, "cumulus")

    def test_a_package_with_no_python_is_refused_naming_the_module_it_owes(self) -> None:
        package = self.one()
        (self.area / "cumulus" / "slipwai_target_cumulus" / "__init__.py").unlink()
        with self.assertRaises(Refused) as raised:
            target_directory.import_package(package)
        self.assertIn("slipwai_target_cumulus", str(raised.exception))

    def test_a_module_that_raises_at_import_is_refused_rather_than_crashing_the_keel(self) -> None:
        with self.assertRaises(Refused) as raised:
            target_directory.import_package(self.one(module="raise RuntimeError('no')"))
        self.assertIn("failed to import", str(raised.exception))

    def test_a_module_with_no_target_is_refused(self) -> None:
        with self.assertRaises(Refused) as raised:
            target_directory.import_package(self.one(module="VALUE = 1"))
        self.assertIn("has no TARGET", str(raised.exception))

    def test_a_target_that_is_not_a_target_is_refused_by_its_type(self) -> None:
        with self.assertRaises(Refused) as raised:
            target_directory.import_package(self.one(module="TARGET = 'cumulus'"))
        self.assertIn("not a Target", str(raised.exception))

    def test_a_target_naming_itself_something_else_than_its_manifest_is_refused(self) -> None:
        module = MODULE.replace('name="cumulus"', 'name="nimbus"')
        with self.assertRaises(Refused) as raised:
            target_directory.import_package(self.one(module=module))
        self.assertIn("nimbus", str(raised.exception))

    def test_a_managed_target_missing_a_required_member_is_refused_with_every_fault_at_once(self) -> None:
        """All of them, for `registry.load`'s reason: one fault per run is six runs to find out what is owed."""
        module = "".join(line for line in MODULE.splitlines(keepends=True)
                         if "TOOLS:" not in line and "IMAGE_REGISTRY:" not in line)
        with self.assertRaises(Refused) as raised:
            target_directory.import_package(self.one(module=module))
        said = str(raised.exception)
        self.assertIn("tools", said)
        self.assertIn("image_registry", said)
        self.assertNotIn("\n", said)

    def test_an_unmanaged_target_owes_none_of_the_required_members(self) -> None:
        """A project deploying somewhere the keel does not own ships no stacks, and is not asked for any."""
        manifest = {key: value for key, value in MANIFEST.items() if key not in ("managed", "reserved")}
        module = 'from slipwai.target_protocol import Target\n\nTARGET = Target(name="cumulus")\n'
        found = target_directory.import_package(self.one(manifest=manifest, module=module))
        self.assertEqual(found.answers, {})


if __name__ == "__main__":
    unittest.main()
