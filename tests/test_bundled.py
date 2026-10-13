"""What a distribution carries beside the package, and the three places that have to agree about it.

The keel reads its own material at run time — the catalogue, the changelog `upgrade` prints, the assets a
project is written from, the rename table `migrate` applies. In a checkout those sit at the repository root
and everything works. An installed copy has no checkout, so each has to be carried into the wheel, into the
source distribution the wheel is built from, and into the executable's spec.

`docs/rename.json` was read by `migrate` and carried by none of the three. `make verify` runs in a checkout,
where the file is there, so every gate was green and `slipwai migrate` ended in a `FileNotFoundError` for
everybody who had installed the thing. This holds the three lists to `assets.BUNDLED` so that the next one
is caught here rather than by somebody halfway through migrating their repository.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import checkout_packages  # noqa: F401

from slipwai.assets import BUNDLED

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
SPEC = (ROOT / "slipwai.spec").read_text(encoding="utf-8")


class BundledTest(unittest.TestCase):
    def test_everything_named_is_in_the_checkout(self) -> None:
        """A list naming a file that is not there would carry nothing and say it carried it."""
        for name in BUNDLED:
            self.assertTrue((ROOT / name).exists(), f"{name} is named as bundled and is not in the checkout")

    def test_the_wheel_carries_each_one_beside_the_package(self) -> None:
        """`force-include` is what puts it under `slipwai/_bundle/`, which is where `assets.ROOT` points
        when the keel finds no checkout around it."""
        forced = dict(re.findall(r'^"([^"]+)" = "slipwai/_bundle/([^"]+)"$', PYPROJECT, re.MULTILINE))
        for name in BUNDLED:
            self.assertIn(name, forced, f"the wheel does not carry {name}")
            self.assertEqual(forced[name], name, f"the wheel carries {name} under another name")

    def test_the_source_distribution_carries_each_one(self) -> None:
        """The wheel is built from the sdist, so a file missing here is missing from the wheel whatever
        the force-include says."""
        found = re.search(r"\[tool\.hatch\.build\.targets\.sdist\].*?include = \[(.*?)\]", PYPROJECT,
                          re.DOTALL)
        assert found is not None
        included = re.findall(r'"/([^"]+)"', found.group(1))
        for name in BUNDLED:
            self.assertTrue(any(name == one or name.startswith(f"{one}/") for one in included),
                            f"the source distribution does not carry {name}")

    def test_the_executable_carries_each_one(self) -> None:
        """A frozen command has no checkout and no site-packages: what it does not carry it cannot read."""
        datas = re.findall(r'\(str\(root / "([^"]+)"\)', SPEC)
        for name in BUNDLED:
            self.assertIn(name, datas, f"the executable does not carry {name}")


class RenameTableTest(unittest.TestCase):
    """The one that got away, and what it does now when it is not there."""

    def test_the_table_reads_from_the_keel_s_own_root(self) -> None:
        from slipwai.migration_renames import table
        self.assertTrue(table())

    def test_a_copy_without_it_refuses_rather_than_raising_a_traceback(self) -> None:
        import tempfile

        from slipwai.errors import GenerationError
        from slipwai.migration_renames import table
        with self.assertRaises(GenerationError) as refused:
            table(Path(tempfile.mkdtemp()))
        self.assertIn("rename table cannot be read", str(refused.exception))
        self.assertIn("Nothing has been changed", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
