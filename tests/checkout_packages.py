"""Pins the package directory to this checkout's `packages/`, so the suite tests the packages it pins.

Imported first by every suite that imports `slipwai`, because the merged catalogue is read at the first
`import slipwai.catalog` and this suite is `unittest`, with no `conftest.py` to run beforehand. Nothing
here imports `slipwai` until a function is called. `SLIPWAI_LANGUAGES` is set whatever the caller's
environment said, so a run is tested against the pinned package and never the person's home, and
`SLIPWAI_INDEX` is pinned to a `file:` URL that is not there, so no test reaches a network index.

**And no board under test asks this machine for its tools.** A board reads `machine_probe.MACHINE`, which
asks `git`, `make`, `python` and `node` their versions; a Windows runner once took twelve seconds over that
while a test's window waited five. `no_machine` stands a described machine in its place — every tool found,
answered at once and on the asking thread, so a page under test is the same page every time. It is here
rather than in a board fixture because here is the one module every suite that can start a board already
imports: four fixtures each had to remember, and three had not. `test_machine_probe` starts a bare board
and fails if anything but this stand-in answered, and holds every such suite to importing this.

`packages/` does not exist yet. Slice 3.8 puts one package here — the template's toy, in-tree as a
fixture — and no first-party package ever: the keel pins none, because a keel whose gate checks seven
packages is a keel that cannot be changed without them. Until then `pinned()` is false and the tests that
need a package on disk skip with that reason rather than passing on nothing, which is the failure mode
this file exists to prevent: a suite that silently proves less than it claims.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PACKAGES = Path(__file__).resolve().parents[1] / "packages"
VARIABLE = "SLIPWAI_LANGUAGES"
# A `file:` URL that is not there, so an unreachable index is what a test meets by default.
NO_INDEX = (Path(__file__).resolve().parent / "fixtures" / "no-index").as_uri()


def unchecked(packages: Path = PACKAGES) -> list[str]:
    """A line for each package directory holding nothing: a submodule nobody initialised."""
    if not packages.is_dir():
        return []
    return [
        f"packages/{entry.name} is not checked out: git submodule update --init packages/{entry.name}"
        for entry in sorted(packages.iterdir())
        if entry.is_dir() and not entry.name.startswith(".") and not any(entry.iterdir())
    ]


def pinned(packages: Path = PACKAGES) -> bool:
    """Whether there is a package to test against at all."""
    return packages.is_dir() and any(packages.iterdir())


def installed(name: str) -> bool:
    """Whether a package of this name is in the directory.

    `pinned()` says a package is there; this says *which*. A suite that generates in Go needs Go, and
    the toy arriving made every `skipUnless(pinned())` true at once — including on suites that then
    failed with `KeyError: 'go'`, which is a skip that stopped guarding the moment it mattered.
    """
    return (PACKAGES / name).is_dir()


def pin(packages: Path = PACKAGES) -> Path:
    """Point `SLIPWAI_LANGUAGES` at `packages`, or raise the line saying one is not checked out."""
    missing = unchecked(packages)
    if missing:
        raise RuntimeError(missing[0])
    os.environ[VARIABLE] = str(packages)
    os.environ["SLIPWAI_INDEX"] = NO_INDEX
    return packages


#: Where the stand-in machine says each tool is: a directory no machine has, so a test can tell who answered.
NO_MACHINE = "/asked-of-no-machine"


def equipped(tool):  # noqa: ANN001, ANN201 — `prerequisites.Tool` to `Found`, neither imported up here
    """What the stand-in machine has of every tool: a good copy."""
    from slipwai.prerequisites import Found  # noqa: PLC0415 — nothing here imports slipwai before `pin`

    return Found(tool, "found", f"{NO_MACHINE}/{tool.command}", "0.0.0")


def no_machine() -> None:
    """Stand the described machine in for this one, for every board this process starts."""
    from slipwai import machine_probe  # noqa: PLC0415 — after `pin`, as every import of slipwai is

    machine_probe.MACHINE = machine_probe.Machine(equipped, start=lambda work: work())


def inside_the_command_line() -> bool:
    """Whether this process is `slipwai` itself rather than a suite: a fake package a test writes imports
    this module from inside the command the test ran against a directory and an index of its own, and
    pinning there would point the running command at the checkout halfway through."""
    spec = getattr(sys.modules.get("__main__"), "__spec__", None)
    return getattr(spec, "name", None) in ("slipwai", "slipwai.__main__")


if not inside_the_command_line():
    pin()
    no_machine()
