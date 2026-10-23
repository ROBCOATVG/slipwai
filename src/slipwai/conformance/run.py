"""Run the suite over one package: start a fresh interpreter whose package directory is the one named, read its report.

The merged catalog is read at the first `import slipwai.catalog`, from `SLIPWAI_LANGUAGES`, so a package directory
is only a process's own if it is set before that import. `check` therefore never reads the catalog in the caller's
process: it starts `python -m slipwai.conformance.probe` with the directory set and this `slipwai` first on the path,
and reads the report the probe writes to a file. The command line and `ConformanceCase` both come through here, so they
cannot disagree, and a test process that has already merged another directory is left as it was.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import child
from .version_rule import problems

# The checks, in the order they run and are reported. Each one's findings name what is missing.
#: How a reason says the check does not apply to this package at all, rather than that it could not run.
INAPPLICABLE = "does not apply: "


def inapplicable(reason: str) -> bool:
    return reason.startswith(INAPPLICABLE)


def shown(name: str, reason: str) -> str:
    """A check that did not run, as the report prints it."""
    return f"  {name:<11} {reason}" if inapplicable(reason) else f"  {name:<11} not run: {reason}"


CHECKS = ("protocol", "markers", "profiles", "targets", "prune rows", "frontends", "version")
# The ones the probe runs: `version` is read in the parent, where no package code can answer it.
PROBED = tuple(name for name in CHECKS if name != "version")
# Where this `slipwai` is imported from, put first on the probe's path so it checks against this keel.
CORE_PATH = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Report:
    """What the suite found for one package: each check's findings, and why a check that did not run did not."""

    package: str
    directory: Path
    findings: dict[str, list[str]] = field(default_factory=dict)
    not_run: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Every check that applies ran and found nothing. A check that does not apply — the frontend checks of a
        package that ships no browser app, the backend checks of one that ships browser apps alone — is not one
        that could not run, and fails nothing (`INAPPLICABLE`)."""
        return not any(not inapplicable(reason) for reason in self.not_run.values()) and not any(
            self.findings.values())

    def count(self) -> int:
        """How many findings there are across every check."""
        return sum(len(found) for found in self.findings.values())


def environment(language_dir: Path) -> dict[str, str]:
    """The caller's environment with the package directory named and this keel first on the path."""
    path = os.pathsep.join([str(CORE_PATH), *filter(None, [os.environ.get("PYTHONPATH")])])
    return {**os.environ, "SLIPWAI_LANGUAGES": str(language_dir), "PYTHONPATH": path}


def require_package_name(package: str) -> None:
    """A `ValueError` unless `package` is one directory name in the package directory."""
    if package in ("", ".", "..") or Path(package).name != package or "\\" in package:
        raise ValueError(f"{package!r} is not a package's directory name in the language directory")


def validated(package: str, said: object) -> tuple[dict[str, list[str]], dict[str, str]]:
    """The probe's report as `(findings, not_run)`, or a `RuntimeError` where it is not the shape the probe writes:
    each check the probe runs in exactly one of the two, a list of lines or a reason, and nothing else."""
    def malformed(why: str) -> RuntimeError:
        return RuntimeError(f"the conformance probe for {package} wrote a report that is not one: {why}")

    if not isinstance(said, dict) or not all(isinstance(said.get(key), dict) for key in ("findings", "not_run")):
        raise malformed('it is not {"findings": {...}, "not_run": {...}}')
    findings, not_run = said["findings"], said["not_run"]
    for name in PROBED:
        if (name in findings) == (name in not_run):
            raise malformed(f"{name} is in {'both' if name in findings else 'neither'} of findings and not_run")
    named = set(findings) | set(not_run)
    if named != set(PROBED):
        raise malformed(f"it names {sorted(named - set(PROBED))}, which are not checks it runs")
    if not all(isinstance(found, list) and all(isinstance(line, str) for line in found) for found in findings.values()):
        raise malformed("a check's findings are not a list of lines")
    if not all(isinstance(reason, str) for reason in not_run.values()):
        raise malformed("a reason a check did not run is not a line")
    return findings, not_run


def check(language_dir: Path | str, package: str) -> Report:
    """Run every check over `package` in `language_dir`, in a fresh interpreter, and return what it found.

    A `package` that is not one directory name is a `ValueError`. A probe that cannot report — a crash of the suite
    itself, or a package that ended the process while it was imported — is a `RuntimeError` naming the last line it
    printed, never a pass and never a finding about the package. The report travels in a file the probe is given
    the path of; its output is diagnostics only (`child`).

    `version` is read here, in this process, by `version_rule`: it needs no package code, so no package can answer it.
    """
    require_package_name(package)
    directory = Path(language_dir)
    if not directory.is_absolute():
        directory = directory.absolute()
    with tempfile.TemporaryDirectory(prefix="slipwai-report-") as scratch:
        destination = Path(scratch) / "report.json"
        done = child.run("slipwai.conformance.probe", [str(directory), package, str(destination)],
                         environment(directory))
        try:
            said = json.loads(destination.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            said = None
    if said is None:
        raise RuntimeError(f"the conformance probe for {package} did not report "
                           f"(exit {done.returncode}); the package's import is the likely cause if it ended the "
                           f"process. Last line: {done.last_line()}")
    findings, not_run = validated(package, said)
    root = directory / package
    if root.is_dir():
        findings["version"] = problems(root)
    else:
        not_run["version"] = f"there is no {root}"
    return Report(package, directory, {name: findings[name] for name in CHECKS if name in findings},
                  {name: not_run[name] for name in CHECKS if name in not_run})
