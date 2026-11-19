"""A package that declares a script it does not ship is refused, and an installed one in that state says so (#117).

`codegraph` 1.0.0 declared `"after-stage": {"run": "hooks/sync.py"}` and shipped no `hooks/sync.py`. Conformance
read the `init` hook and no other, so the package passed, was published, and synced nothing for the life of that
version; `slipwai extension list` showed `after-stage` among its hooks all the while.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import cli_extension, package_new
from slipwai.conformance.__main__ import main as conformance
from slipwai.conformance.extension import check
from slipwai.extension_directory import absent

CORE = "9.0"


def declaring(area: Path, key: str, **blocks: dict) -> Path:
    """The scaffold, which passes all six, declaring whatever else the case names."""
    package_new.write("extension", key, area, CORE)
    place = area / key
    manifest = json.loads((place / "extension.json").read_text(encoding="utf-8"))
    for block, declared in blocks.items():
        manifest[block] = {**manifest.get(block, {}), **declared}
    (place / "extension.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return place


class Case(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.area, True)


class AbsentTest(Case):
    def test_every_declared_script_the_package_ships_is_nothing_to_say(self) -> None:
        place = declaring(self.area, "whole", hooks={"after-stage": {"run": "hooks/sync.py"}},
                          guards={"before-search": "guards/search.py"})
        for script in ("hooks/sync.py", "guards/search.py"):
            (place / script).parent.mkdir(exist_ok=True)
            (place / script).write_text("", encoding="utf-8")
        self.assertEqual(absent(place, json.loads((place / "extension.json").read_text(encoding="utf-8"))), [])

    def test_a_hook_and_a_guard_whose_script_is_not_there_are_each_named(self) -> None:
        place = declaring(self.area, "holed", hooks={"after-stage": {"run": "hooks/sync.py"}},
                          guards={"before-search": "guards/search.py"})
        found = absent(place, json.loads((place / "extension.json").read_text(encoding="utf-8")))
        self.assertEqual(found, [("guard", "before-search", "guards/search.py"),
                                 ("hook", "after-stage", "hooks/sync.py")])

    def test_a_default_declaration_is_held_to_as_a_written_one_is(self) -> None:
        """`project` fires `init.py` where the manifest names nothing else, so a package without one has a
        hook that never runs, whether or not it wrote the line."""
        place = declaring(self.area, "renamed", hooks={"init": "setup.py"})
        (place / "init.py").rename(place / "setup.py")
        self.assertEqual(absent(place, json.loads((place / "extension.json").read_text(encoding="utf-8"))),
                         [("hook", "project", "init.py")])

    def test_a_script_spelled_in_another_case_is_not_the_script(self) -> None:
        """A project is generated on Linux too, where `Hooks/sync.py` is not `hooks/sync.py`."""
        place = declaring(self.area, "cased", hooks={"after-stage": "hooks/sync.py"})
        (place / "Hooks").mkdir()
        (place / "Hooks/sync.py").write_text("", encoding="utf-8")
        self.assertEqual(absent(place, json.loads((place / "extension.json").read_text(encoding="utf-8"))),
                         [("hook", "after-stage", "hooks/sync.py")])


class ConformanceTest(Case):
    def said(self, place: Path) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            status = conformance(["--extension", str(place)])
        return status, out.getvalue()

    def test_the_scaffold_ships_everything_it_declares(self) -> None:
        status, said = self.said(declaring(self.area, "whole"))
        self.assertEqual(status, 0, said)
        self.assertIn("ships", said)

    def test_a_hook_whose_script_is_missing_fails_naming_the_point_and_the_path(self) -> None:
        place = declaring(self.area, "holed", hooks={"after-stage": {"run": "hooks/sync.py", "budget": "30s"}})
        report = check(place)
        self.assertFalse(report.passed)
        self.assertEqual(len(report.findings["ships"]), 1)
        self.assertIn("`after-stage` hook", report.findings["ships"][0])
        self.assertIn("hooks/sync.py", report.findings["ships"][0])
        self.assertEqual(report.findings["idempotent"], [], "the six are still run: the entry point is there")
        status, said = self.said(place)
        self.assertEqual(status, 1)
        self.assertIn("hooks/sync.py", said)
        self.assertIn("holed failed, 1 finding", said)

    def test_a_guard_whose_script_is_missing_fails_the_same_way(self) -> None:
        report = check(declaring(self.area, "open", guards={"before-search": "guards/search.py"}))
        self.assertFalse(report.passed)
        self.assertIn("`before-search` guard", report.findings["ships"][0])
        self.assertIn("guards/search.py", report.findings["ships"][0])


class ListTest(Case):
    def listed(self) -> str:
        with mock.patch.dict(os.environ, {"SLIPWAI_LANGUAGES": str(self.area)}):
            return "\n".join(cli_extension.rows())

    def test_an_installed_package_missing_a_declared_script_says_which(self) -> None:
        declaring(self.area, "holed", hooks={"after-stage": "hooks/sync.py"},
                  guards={"before-search": "guards/search.py"})
        said = self.listed()
        self.assertIn("after-stage (hooks/sync.py is not in the package, so it never runs)", said)
        self.assertIn("before-search (guards/search.py is not in the package, so it never runs)", said)
        self.assertIn("extension install holed", said)

    def test_a_whole_package_is_listed_as_it_was(self) -> None:
        declaring(self.area, "whole")
        self.assertIn("      hooks: init, project", self.listed())
        self.assertNotIn("not in the package", self.listed())


if __name__ == "__main__":
    unittest.main()
