"""What `check-structure` refuses, proven by making it refuse.

A gate nobody has seen fail is a gate nobody knows the shape of. Each test here builds a small tree that
breaks exactly one rule and asserts the gate says so, naming the file and the reason; the last one runs the
gate against this repository, which is the only way to know the rules are satisfiable by real code.

The gate is driven by patching its module globals at the tree it should read, rather than by a subprocess,
so the whole suite stays inside the per-increment gate. `main()` reads nothing else.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "scripts/check-structure.py"

_spec = importlib.util.spec_from_file_location("check_structure", SCRIPT)
assert _spec is not None and _spec.loader is not None
structure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(structure)

CLEAN_TIERS = (("foundation", ("errors",)), ("edge", ("cli",)), ("package", ("__init__",)))


def run_gate(
    root: Path,
    modules: dict[str, str],
    *,
    tiers: tuple[tuple[str, tuple[str, ...]], ...] = CLEAN_TIERS,
    surface: str = "",
    packages: dict[str, str] | None = None,
    suites: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Write a tree and run the gate over it, returning its exit code and what it printed to stderr."""
    keel = root / "src/slipwai"
    for name, text in modules.items():
        path = keel / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    for name, text in (suites or {}).items():
        (root / "tests" / name).write_text(text, encoding="utf-8")
    for name, text in (packages or {}).items():
        path = root / "packages" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "import-surface.txt").write_text(surface, encoding="utf-8")

    stderr = io.StringIO()
    with mock.patch.multiple(
        structure, ROOT=root, KEEL=keel, PACKAGES=root / "packages", SURFACE=root / "import-surface.txt", TIERS=tiers
    ), contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
        code = structure.main()
    return code, stderr.getvalue()


class GateTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def gate(self, modules: dict[str, str], **options: Any) -> tuple[int, str]:
        return run_gate(self.root, modules, **options)

    def test_a_tree_that_keeps_every_rule_passes(self) -> None:
        code, said = self.gate({"__init__.py": '"""The keel."""\n', "errors.py": '"""A refusal."""\n'})
        self.assertEqual((code, said), (0, ""))

    def test_an_import_against_the_direction_is_refused(self) -> None:
        """`errors` is inward of `cli`, so it may not read it. This is the rule the gate exists for."""
        code, said = self.gate({
            "__init__.py": '"""The keel."""\n',
            "cli.py": '"""The command line."""\n',
            "errors.py": '"""A refusal."""\nfrom .cli import main\n',
        })
        self.assertEqual(code, 1)
        self.assertIn("foundation imports edge: errors -> cli", said)
        self.assertIn("Imports point inward", said)

    def test_the_same_import_the_other_way_round_is_allowed(self) -> None:
        """Outward may read inward; that is the whole point of the direction having one."""
        code, said = self.gate({
            "__init__.py": '"""The keel."""\n',
            "errors.py": '"""A refusal."""\n',
            "cli.py": '"""The command line."""\nfrom .errors import *  # noqa: F403\n',
        })
        self.assertEqual((code, said), (0, ""))

    def test_a_cycle_is_named_rather_than_left_to_become_an_import_error(self) -> None:
        code, said = self.gate(
            {
                "__init__.py": '"""The keel."""\n',
                "a.py": '"""A."""\nfrom .b import thing\n',
                "b.py": '"""B."""\nfrom .a import other\n',
            },
            tiers=(("foundation", ("a", "b")), ("package", ("__init__",))),
        )
        self.assertEqual(code, 1)
        self.assertIn("import cycle:", said)

    def test_a_module_over_the_budget_is_refused(self) -> None:
        body = "\n".join(f"x{n} = {n}" for n in range(structure.MODULE_BUDGET + 1))
        code, said = self.gate({"__init__.py": '"""The keel."""\n', "errors.py": f'"""A refusal."""\n{body}\n'})
        self.assertEqual(code, 1)
        self.assertIn(f"over the {structure.MODULE_BUDGET}-line budget", said)

    def test_a_facade_that_does_more_than_dispatch_is_refused(self) -> None:
        body = "\n".join(f"x{n} = {n}" for n in range(structure.FACADE_BUDGET + 1))
        code, said = self.gate({"__init__.py": f'"""The keel."""\n{body}\n'})
        self.assertEqual(code, 1)
        self.assertIn("package facade", said)

    def test_a_module_with_no_docstring_is_refused(self) -> None:
        code, said = self.gate({"__init__.py": '"""The keel."""\n', "errors.py": "THING = 1\n"})
        self.assertEqual(code, 1)
        self.assertIn("no module docstring saying what part this is", said)

    def test_a_module_in_no_tier_stops_the_gate_rather_than_passing_unchecked(self) -> None:
        """Silence here would let a module arrive with no declared place, which is how tiers rot."""
        with self.assertRaises(SystemExit) as raised:
            self.gate({"__init__.py": '"""The keel."""\n', "stowaway.py": '"""Nowhere."""\n'})
        self.assertIn("belongs to no declared tier", str(raised.exception))

    def test_the_keel_may_not_import_a_language_package(self) -> None:
        code, said = self.gate({
            "__init__.py": '"""The keel."""\n',
            "errors.py": '"""A refusal."""\nimport slipwai_language_go\n',
        })
        self.assertEqual(code, 1)
        self.assertIn("the keel imports a language package: slipwai_language_go", said)

    def test_the_keel_may_not_import_a_target_package_either(self) -> None:
        """The same rule, and it has to be a rule rather than a habit: the keel naming a cloud is exactly
        what the clouds were made packages to stop, and a keel that only refused languages would let the
        first `import slipwai_target_aws` back in without a word."""
        code, said = self.gate({
            "__init__.py": '"""The keel."""\n',
            "errors.py": '"""A refusal."""\nfrom slipwai_target_aws import stacks\n',
        })
        self.assertEqual(code, 1)
        self.assertIn("the keel imports a target package: slipwai_target_aws", said)

    def test_the_keel_importing_a_package_inside_a_function_is_refused_too(self) -> None:
        """Anywhere in the module, not only at the top: a deferred import is still the keel knowing a cloud,
        and it is the shape somebody reaches for when the top of the file is being watched."""
        code, said = self.gate({
            "__init__.py": '"""The keel."""\n',
            "errors.py": ('"""A refusal."""\ndef go():\n    import slipwai_target_azure\n'
                          "    return slipwai_target_azure\n"),
        })
        self.assertEqual(code, 1)
        self.assertIn("the keel imports a target package: slipwai_target_azure", said)

    def test_every_kind_of_package_the_keel_may_not_name_is_refused(self) -> None:
        """Named from the table the gate walks the packages by, so a fourth kind is refused the day it is
        declared rather than the day somebody remembers to write a test for it."""
        for kind, prefix in structure.PACKAGE_PREFIXES.items():
            with self.subTest(kind=kind):
                code, said = self.gate({
                    "__init__.py": '"""The keel."""\n',
                    "errors.py": f'"""A refusal."""\nimport {prefix}thing\n',
                })
                self.assertEqual(code, 1)
                self.assertIn(f"the keel imports a {kind} package: {prefix}thing", said)

    def test_a_surface_naming_a_module_the_keel_has_not_got_is_refused(self) -> None:
        """An empty surface is held the same way: the file is checked whether or not a package exists."""
        code, said = self.gate({"__init__.py": '"""The keel."""\n'}, surface="slipwai.registry\n")
        self.assertEqual(code, 1)
        self.assertIn("lists slipwai.registry, which the keel does not have", said)

    def test_a_package_importing_off_the_surface_is_refused(self) -> None:
        code, said = self.gate(
            {"__init__.py": '"""The keel."""\n', "errors.py": '"""A refusal."""\n', "cli.py": '"""The edge."""\n'},
            surface="slipwai.errors\n",
            packages={"go/slipwai_language_go/backend.py": '"""Go."""\nfrom slipwai import errors, cli\n'},
        )
        self.assertEqual(code, 1)
        self.assertIn("language go imports slipwai.cli, which is not on the import surface", said)
        self.assertNotIn("slipwai.errors, which is not on the import surface", said)

    def test_a_target_package_is_read_and_held_to_the_targets_own_surface(self) -> None:
        """The surface is a section per kind. A target reaching for a module only a language is promised is
        refused exactly as a language reaching past its own section is."""
        code, said = self.gate(
            {"__init__.py": '"""The keel."""\n', "errors.py": '"""A refusal."""\n', "cli.py": '"""The edge."""\n'},
            surface="[language]\nslipwai.cli\n[target]\nslipwai.errors\n",
            packages={"cumulus/slipwai_target_cumulus/__init__.py":
                      '"""Cumulus."""\nfrom slipwai import errors, cli\n'},
        )
        self.assertEqual(code, 1)
        self.assertIn("target cumulus imports slipwai.cli, which is not on the import surface", said)
        self.assertNotIn("slipwai.errors, which is not on the import surface", said)

    def test_a_language_may_not_reach_for_what_only_a_target_is_promised(self) -> None:
        code, said = self.gate(
            {"__init__.py": '"""The keel."""\n', "errors.py": '"""A refusal."""\n', "cli.py": '"""The edge."""\n'},
            surface="[language]\nslipwai.cli\n[target]\nslipwai.errors\n",
            packages={"go/slipwai_language_go/backend.py": '"""Go."""\nfrom slipwai import errors\n'},
        )
        self.assertEqual(code, 1)
        self.assertIn("language go imports slipwai.errors, which is not on the import surface", said)

    def test_a_whole_target_package_passes(self) -> None:
        code, said = self.gate(
            {"__init__.py": '"""The keel."""\n', "errors.py": '"""A refusal."""\n'},
            surface="[target]\nslipwai.errors\n",
            packages={"cumulus/slipwai_target_cumulus/__init__.py": '"""Cumulus."""\nfrom slipwai import errors\n'},
        )
        self.assertEqual((code, said), (0, ""))

    def test_a_surface_naming_a_module_the_keel_has_not_got_is_refused_in_any_section(self) -> None:
        code, said = self.gate({"__init__.py": '"""The keel."""\n'},
                               surface="[target]\nslipwai.registry\n")
        self.assertEqual(code, 1)
        self.assertIn("lists slipwai.registry, which the keel does not have", said)

    def test_a_package_directory_that_was_never_checked_out_is_reported(self) -> None:
        (self.root / "packages/go").mkdir(parents=True)
        code, said = self.gate({"__init__.py": '"""The keel."""\n'})
        self.assertEqual(code, 1)
        self.assertIn("git submodule update --init packages/go", said)

    def test_a_suite_over_the_budget_is_refused(self) -> None:
        body = "\n".join(f"x{n} = {n}" for n in range(structure.MODULE_BUDGET + 1))
        code, said = self.gate({"__init__.py": '"""The keel."""\n'}, suites={"test_big.py": body})
        self.assertEqual(code, 1)
        self.assertIn("over the", said)


class SurfaceTest(unittest.TestCase):
    def test_comments_and_blank_lines_are_not_modules(self) -> None:
        listing = "# a comment\n\nslipwai.registry\n  slipwai.loaded  # why\n"
        self.assertEqual(structure.import_surface(listing), {"slipwai.registry", "slipwai.loaded"})

    def test_a_listing_with_no_section_header_is_what_it_always_was(self) -> None:
        """The file was one flat list of what a language may import, so that is what a headerless one is."""
        listing = "slipwai.registry\n"
        self.assertEqual(structure.import_surface(listing, "language"), {"slipwai.registry"})
        self.assertEqual(structure.import_surface(listing, "target"), set())

    def test_each_kind_reads_its_own_section_and_no_other(self) -> None:
        listing = "slipwai.registry\n[target]\nslipwai.target_protocol\n[language]\nslipwai.loaded\n"
        self.assertEqual(structure.import_surface(listing, "language"), {"slipwai.registry", "slipwai.loaded"})
        self.assertEqual(structure.import_surface(listing, "target"), {"slipwai.target_protocol"})

    def test_the_whole_file_is_every_section_at_once(self) -> None:
        """Which is what holds the other direction: a line naming a module the keel has not got is a
        promise nobody can keep, in whichever section somebody wrote it."""
        listing = "slipwai.registry\n[target]\nslipwai.target_protocol\n"
        self.assertEqual(structure.import_surface(listing), {"slipwai.registry", "slipwai.target_protocol"})

    def test_every_module_this_repository_promises_is_one_it_has(self) -> None:
        """A surface line is a promise. One naming a module the keel has not got cannot be kept."""
        self.assertTrue(structure.SURFACE.is_file())
        promised = structure.import_surface(structure.SURFACE.read_text(encoding="utf-8"))
        self.assertTrue(promised, "the surface should not be empty once a module is promised")
        self.assertLessEqual(promised, structure.keel_modules())

    def test_every_section_stays_under_the_ceiling(self) -> None:
        """Twenty is what the six language packages actually import, and the plan's ceiling. Past it, a
        package is reaching into the keel rather than being answered by it — which is the same question for
        every kind, so every kind's section is held to the same number rather than to one of its own."""
        listing = structure.SURFACE.read_text(encoding="utf-8")
        for kind in structure.PACKAGE_PREFIXES:
            with self.subTest(kind=kind):
                promised = structure.import_surface(listing, kind)
                self.assertLessEqual(len(promised), structure.CEILING, sorted(promised))

    def test_a_language_still_promises_exactly_the_twenty_it_did(self) -> None:
        """The surface was already at the ceiling when targets arrived, which is what sections are for: a
        kind's own section widens without the language's being spent on it."""
        listing = structure.SURFACE.read_text(encoding="utf-8")
        self.assertEqual(len(structure.import_surface(listing, "language")), structure.CEILING)


class RepositoryTest(unittest.TestCase):
    def test_this_repository_satisfies_its_own_gate(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = structure.main()
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("no upward imports and no cycles", out.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
