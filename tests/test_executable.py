"""The standalone executable's recipe, checked without building one.

Building it takes PyInstaller and several minutes, which is `make test-executable` and a release job's
work rather than the gate's. What the gate can hold is the recipe: that it bundles the keel and no
package, that every file it claims to carry exists, and that the hidden-imports line is still there —
a package is imported by name at run time, so a static analysis of `__main__` reaches none of the keel
and the executable would ship with most of itself missing.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SPEC = REPOSITORY / "slipwai.spec"


class SpecTest(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = SPEC.read_text(encoding="utf-8")

    def test_every_file_it_carries_is_there(self) -> None:
        """PyInstaller fails on a `datas` entry that is not there, and it fails at release time."""
        for named in re.findall(r'root / "([^"]+)"', self.spec):
            with self.subTest(carried=named):
                self.assertTrue((REPOSITORY / named).exists(), named)

    def test_it_carries_the_keels_own_material(self) -> None:
        for named in ("assets", "catalog.json", "VERSION"):
            self.assertIn(f'root / "{named}"', self.spec)

    def test_it_bundles_no_package(self) -> None:
        """The executable is the keel alone, the same as the wheel: one artefact to build and sign, and
        no bundled copy to drift from the chandlery's."""
        self.assertNotIn("packages", self.spec.replace("the package directory", ""))

    def test_every_keel_module_stays_in_it(self) -> None:
        """A package imports the keel by name at run time, so a static analysis of `__main__` reaches
        almost none of it and the executable would ship with most of itself missing."""
        self.assertIn('collect_submodules("slipwai")', self.spec)

    def test_it_carries_the_roots_it_verifies_against(self) -> None:
        """A new Windows holds too few roots to verify the index or Node, so the executable carries its own
        (`slipwai/certificates.py`). The recipe imports the package, so a build without it stops; it names
        the bundle among what it carries; and the build pins it."""
        self.assertRegex(self.spec, r"(?m)^import certifi\b")
        self.assertIn('collect_data_files("certifi")', self.spec)
        self.assertRegex((REPOSITORY / "requirements-build.txt").read_text(encoding="utf-8"), r"(?m)^certifi==")

    def test_both_doors_install_them(self) -> None:
        """The command and the app each start their own process, and each fetches."""
        for door, call in (("cli.py", "carry_certificates()"), ("app.py", "certificates.install()")):
            with self.subTest(door=door):
                self.assertIn(call, (REPOSITORY / "src/slipwai" / door).read_text(encoding="utf-8"))

    def test_the_entry_point_is_the_one_python_m_uses(self) -> None:
        self.assertIn("src/slipwai/__main__.py", self.spec)


class BuildToolsTest(unittest.TestCase):
    def test_the_build_pins_are_exact(self) -> None:
        """A range here is an executable that differs between two builds of the same commit."""
        pins = (REPOSITORY / "requirements-build.txt").read_text(encoding="utf-8")
        for line in pins.splitlines():
            if line.strip() and not line.startswith("#"):
                with self.subTest(pin=line):
                    self.assertRegex(line, r"^[A-Za-z0-9._-]+==[^;]+")

    def test_the_build_and_the_smoke_script_are_both_here(self) -> None:
        self.assertTrue((REPOSITORY / "scripts/build-executable").is_file())
        self.assertTrue((REPOSITORY / "scripts/smoke-executable.py").is_file())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
