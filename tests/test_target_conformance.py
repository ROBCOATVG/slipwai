"""The conformance profile a target package is held to, run over packages this suite writes.

Slow, and in the Makefile's `SLOW` list for it: every check here starts an interpreter, because reading a
package's `TARGET` means importing it and a suite that imported it in its own process would be one a
package could change the verdict of.

What is proved is the suite, not any cloud: every package here is a fake written into a temporary
directory, and the one real package is what `slipwai package new --kind target` writes.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai import package_new
from slipwai.conformance.target import CHECKS, check

CORE = "9.0"
#: A module that answers everything a managed target owes, with the files the fixture also writes.
WHOLE = '''"""A target for the suite to read."""
from slipwai.target_protocol import (
    ADD_COMMANDS, AGENT_RULES, DOCS_PAGES, IMAGE_REGISTRY, PIPELINE, README_WORDS, SCRIPTS, SHAPES, TOOLS,
    Target,
)

TARGET = Target(name="cumulus", answers={
    SHAPES: {"bootstrap": ("bootstrap/main.tf",), "service": ("service/main.tf",)},
    SCRIPTS: {"scripts/deploy.py": "scripts/deploy.py"},
    DOCS_PAGES: {"docs/deployment.md": lambda project, apps: "# Where\\n"},
    TOOLS: (("tofu", "what applies the stacks", "https://opentofu.org"),),
    IMAGE_REGISTRY: {"cloud": "Cumulus", "registry": "CR", "example": "cumulus.example/", "runtime": "Boxes"},
    PIPELINE: {"cli": "", "credentials": "      - uses: cumulus/login@v1\\n", "build_cli": "",
               "registry_login": "      - run: cumulus registry login\\n",
               "environment": "  IMAGE_REGISTRY: ${{ vars.IMAGE_REGISTRY }}\\n"},
    README_WORDS: {"runtime": "one box per app", "site": " A bucket.", "credentials": "a cumulus sign-in"},
    AGENT_RULES: "- This project deploys to Cumulus from the pipeline.\\n",
    ADD_COMMANDS: {"service": "- one more box\\n", "web": "- behind the edge\\n"},
})
'''


def fixture(root: Path, module: str = WHOLE, manifest: dict | None = None,
            files: tuple[str, ...] = ("bootstrap/main.tf", "service/main.tf", "scripts/deploy.py")) -> Path:
    """One target package on disk, whole unless the caller takes something away."""
    place = root / "cumulus"
    (place / "slipwai_target_cumulus").mkdir(parents=True)
    (place / "slipwai_target_cumulus/__init__.py").write_text(module, encoding="utf-8")
    declared = {"name": "cumulus", "label": "Cumulus — a cloud", "description": "Where a project goes",
                "kind": "target", "core": ">=9.0,<10", "managed": True} if manifest is None else manifest
    (place / "target.json").write_text(json.dumps(declared), encoding="utf-8")
    (place / "VERSION").write_text("1.0.0.dev0\n", encoding="utf-8")
    (place / "changelog.d").mkdir()
    (place / "changelog.d/first.md").write_text("MINOR\n\n**It is a cloud.** And that is all.\n", encoding="utf-8")
    for relative in files:
        target = place / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# a stack\n", encoding="utf-8")
    return place


class ProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.area = Path(tempfile.mkdtemp())

    def test_a_whole_target_passes_every_check(self) -> None:
        report = check(fixture(self.area))
        self.assertEqual(report.findings, dict.fromkeys(CHECKS, []))
        self.assertTrue(report.passed)

    def test_a_declaration_the_keel_does_not_read_stops_the_checks_that_read_against_it(self) -> None:
        """Nothing after `declaration` runs: a package the catalog could not take a row from is a package
        whose answers nobody would ever ask for."""
        report = check(fixture(self.area, manifest={"name": "cumulus", "kind": "target"}))
        self.assertTrue(report.findings["declaration"])
        self.assertEqual(sorted(report.not_run), ["protocol", "shapes"])

    def test_a_name_that_is_not_its_directory_is_refused_naming_both(self) -> None:
        manifest = {"name": "nimbus", "label": "Nimbus", "description": "d", "kind": "target", "core": ">=9.0,<10"}
        report = check(fixture(self.area, manifest=manifest))
        self.assertIn("nimbus", report.findings["declaration"][0])
        self.assertIn("cumulus", report.findings["declaration"][0])

    def test_a_package_whose_module_does_not_import_says_so_and_reads_nothing_else(self) -> None:
        report = check(fixture(self.area, module="raise RuntimeError('no')\n"))
        self.assertIn("could not be imported", report.findings["protocol"][0])
        self.assertIn("shapes", report.not_run)

    def test_a_module_with_no_target_in_it_is_told_what_to_export(self) -> None:
        report = check(fixture(self.area, module='"""Nothing."""\n'))
        self.assertIn("has no TARGET", report.findings["protocol"][0])

    def test_a_target_called_something_else_than_its_manifest_is_refused(self) -> None:
        module = WHOLE.replace('Target(name="cumulus"', 'Target(name="nimbus"')
        report = check(fixture(self.area, module=module))
        self.assertIn("nimbus", report.findings["protocol"][0])

    def test_a_managed_target_missing_a_required_member_is_told_which(self) -> None:
        module = WHOLE.replace('    TOOLS: (("tofu", "what applies the stacks", "https://opentofu.org")),\n', "")
        module = module.replace('    TOOLS: (("tofu", "what applies the stacks", "https://opentofu.org"),),\n', "")
        report = check(fixture(self.area, module=module))
        self.assertEqual(report.findings["protocol"], ["target cumulus is missing tools"])

    def test_a_stack_made_of_files_the_package_does_not_ship_is_refused(self) -> None:
        report = check(fixture(self.area, files=("service/main.tf", "scripts/deploy.py")))
        self.assertEqual(len(report.findings["shapes"]), 1)
        self.assertIn("bootstrap/main.tf", report.findings["shapes"][0])

    def test_a_script_the_package_does_not_ship_is_refused_the_same_way(self) -> None:
        report = check(fixture(self.area, files=("bootstrap/main.tf", "service/main.tf")))
        self.assertEqual(len(report.findings["shapes"]), 1)
        self.assertIn("scripts/deploy.py", report.findings["shapes"][0])

    def test_the_version_rule_is_the_same_one_every_package_is_held_to(self) -> None:
        place = fixture(self.area)
        (place / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        report = check(place)
        self.assertTrue(report.findings["version"])


class ScaffoldTest(unittest.TestCase):
    def test_what_package_new_writes_passes_the_suite_the_moment_it_is_written(self) -> None:
        """A scaffold whose first lesson is that the tool is broken teaches that."""
        area = Path(tempfile.mkdtemp())
        package_new.write("target", "cumulus", area, CORE)
        report = check(area / "cumulus")
        self.assertTrue(report.passed, f"{report.findings} {report.not_run}")


if __name__ == "__main__":
    unittest.main()
