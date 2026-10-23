"""`ConformanceCase`: the suite as a `unittest` case, for a package's own `tests/test_conformance.py`.

A package subclasses it and names where it is::

    from pathlib import Path
    from slipwai import conformance

    class Conformance(conformance.ConformanceCase):
        language_dir = Path(__file__).resolve().parents[2]
        package = "go"

The suite runs once for the class, in a fresh interpreter (`run.check`), and each check is one test that fails with
its findings. A check that could not run because `protocol` stopped the rest — the package did not load, or loaded
with nothing to check it through — is skipped with the reason, so the one `protocol` failure is the one cause shown;
so is one whose generations all stopped at a snippet `markers` named, which claims no pass over them.
Imported as `conformance.ConformanceCase`, the base class is not a name in the package's test module, and so is not
collected again; collected anyway, it skips saying what to set.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from typing import ClassVar

from .run import Report, check

UNSET = "set language_dir and package on the subclass of ConformanceCase"


class ConformanceCase(unittest.TestCase):
    """The conformance suite over `package` in `language_dir`, one test per check."""

    language_dir: ClassVar[Path | str | None] = None
    package: ClassVar[str | None] = None
    report: ClassVar[Report]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if cls.language_dir is None or cls.package is None:
            raise unittest.SkipTest(UNSET)
        cls.report = check(cls.language_dir, cls.package)

    def verdict(self, name: str) -> None:
        """Fail with every finding `name` made, or skip where it could not run."""
        if name in self.report.not_run:
            self.skipTest(f"{name}: {self.report.not_run[name]}")
        found = self.report.findings.get(name, [])
        if found:
            self.fail(f"{self.report.package} fails {name}:\n" + "\n".join(f"  {finding}" for finding in found))

    def test_protocol(self) -> None:
        self.verdict("protocol")

    def test_markers(self) -> None:
        self.verdict("markers")

    def test_profiles(self) -> None:
        self.verdict("profiles")

    def test_targets(self) -> None:
        self.verdict("targets")

    def test_prune_rows(self) -> None:
        self.verdict("prune rows")

    def test_frontends(self) -> None:
        self.verdict("frontends")

    def test_version(self) -> None:
        self.verdict("version")
