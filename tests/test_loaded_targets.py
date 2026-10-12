"""What the keel asks a loaded target, and what it says when there is nothing there to ask.

The targets' half of `loaded.py`. A row, a menu and `--target <name>` are answered from the manifest and
import nothing; this is the other half — every answer the keel reads *while writing a project*, which means
the package's Python has to be imported, which means it is imported here and lazily rather than at the
moment the catalog is built.

The refusals matter more than the answers. A keel with no cloud installed is the ordinary case now, so
`--target aws` on a machine where `aws` is not installed has to end on the command that fixes it rather than
on a KeyError somewhere inside a page generator.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import checkout_packages  # noqa: F401

from slipwai import loaded_targets
from slipwai.errors import GenerationError
from slipwai.language_directory import Refused
from slipwai.target_directory import TargetPackage
from slipwai.target_protocol import REGION, SHAPES, TOOLS, Target

MANIFEST = {
    "name": "cumulus", "label": "Cumulus", "description": "Where a project goes",
    "kind": "target", "core": ">=9.0,<10", "managed": True,
}
ANSWERS: dict = {
    SHAPES: {"bootstrap": ("bootstrap/main.tf",), "service": ("service/main.tf",)},
    TOOLS: (("tofu", "what applies the stacks", "https://opentofu.org/"),),
}
PACKAGE = TargetPackage("cumulus", Path("/packages/cumulus"), MANIFEST)


class Installed:
    """A package directory with these targets in it, for the length of a `with`."""

    def __init__(self, *targets: Target, packages: list[TargetPackage] | None = None) -> None:
        self.targets = {one.name: one for one in targets}
        self.packages = packages if packages is not None else [PACKAGE]

    def __enter__(self) -> None:
        loaded_targets.loaded.cache_clear()
        self.patches: list[Any] = [
            mock.patch.object(loaded_targets, "TARGETS", self.packages),
            mock.patch.object(loaded_targets, "import_package",
                              side_effect=lambda package: self.targets[package.name]),
        ]
        for patch in self.patches:
            patch.start()

    def __exit__(self, *_: object) -> None:
        for patch in self.patches:
            patch.stop()
        loaded_targets.loaded.cache_clear()


class LoadedTest(unittest.TestCase):
    def tearDown(self) -> None:
        loaded_targets.loaded.cache_clear()

    def test_an_installed_targets_answers_are_read_by_name(self) -> None:
        with Installed(Target("cumulus", ANSWERS)):
            self.assertEqual(loaded_targets.answer("cumulus", TOOLS), ANSWERS[TOOLS])

    def test_a_member_the_target_does_not_answer_comes_back_as_the_default(self) -> None:
        """An optional member's absence is an answer — "this cloud has no ambient region" — so it is read
        as one rather than refused."""
        with Installed(Target("cumulus", ANSWERS)):
            self.assertIsNone(loaded_targets.answer("cumulus", REGION))
            self.assertEqual(loaded_targets.answer("cumulus", REGION, default=()), ())

    def test_nothing_is_imported_until_something_is_asked(self) -> None:
        with Installed(Target("cumulus", ANSWERS)):
            self.assertEqual(loaded_targets.import_package.call_count, 0)  # type: ignore[attr-defined]
            loaded_targets.answer("cumulus", TOOLS)
            self.assertEqual(loaded_targets.import_package.call_count, 1)  # type: ignore[attr-defined]

    def test_a_second_question_does_not_import_the_package_again(self) -> None:
        with Installed(Target("cumulus", ANSWERS)):
            loaded_targets.answer("cumulus", TOOLS)
            loaded_targets.answer("cumulus", SHAPES)
            self.assertEqual(loaded_targets.import_package.call_count, 1)  # type: ignore[attr-defined]


class RefusalTest(unittest.TestCase):
    def tearDown(self) -> None:
        loaded_targets.loaded.cache_clear()

    def test_asking_a_target_that_is_not_installed_names_the_command_that_installs_it(self) -> None:
        with Installed(packages=[]), self.assertRaises(GenerationError) as raised:
            loaded_targets.answer("cumulus", TOOLS)
        said = str(raised.exception)
        self.assertIn("cumulus", said)
        self.assertIn("target install", said)

    def test_a_target_whose_python_will_not_import_is_a_refusal_and_not_a_traceback(self) -> None:
        def refuse(package: TargetPackage) -> Target:
            raise Refused(f"target {package.name} ({package.root}): it would not import")

        loaded_targets.loaded.cache_clear()
        with mock.patch.object(loaded_targets, "TARGETS", [PACKAGE]), \
                mock.patch.object(loaded_targets, "import_package", side_effect=refuse):
            with self.assertRaises(GenerationError) as raised:
                loaded_targets.answer("cumulus", TOOLS)
            self.assertIn("would not import", str(raised.exception))
            self.assertIn("would not import", "\n".join(loaded_targets.refusals()))

    def test_one_target_that_will_not_import_does_not_stop_another_answering(self) -> None:
        other = TargetPackage("stratus", Path("/packages/stratus"), {**MANIFEST, "name": "stratus"})
        working = Target("stratus", ANSWERS)

        def one_refuses(package: TargetPackage) -> Target:
            if package.name == "cumulus":
                raise Refused("target cumulus (/packages/cumulus): it would not import")
            return working

        loaded_targets.loaded.cache_clear()
        with mock.patch.object(loaded_targets, "TARGETS", [PACKAGE, other]), \
                mock.patch.object(loaded_targets, "import_package", side_effect=one_refuses):
            self.assertEqual(loaded_targets.answer("stratus", TOOLS), ANSWERS[TOOLS])
            self.assertEqual(len(loaded_targets.refusals()), 1)

    def test_asking_a_required_member_a_target_somehow_does_not_answer_names_the_member(self) -> None:
        """The loader refuses a managed target missing one, so reaching this means an unmanaged target was
        asked something only a managed one answers — which is a keel fault, said as one."""
        with Installed(Target("cumulus", {})), self.assertRaises(GenerationError) as raised:
            loaded_targets.answer("cumulus", SHAPES)
        self.assertIn("shapes", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
