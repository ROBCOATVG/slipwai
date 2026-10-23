"""The native-gate rows of one backend: what `slipwai generate` is asked for, before each project's own gate runs.

Moved from the root suite's `tests/test_matrix.py` and `tests/test_images.py`, not rewritten. Both profiles and
both frontend answers, without multiplying them: adding a frontend does not change a service's native tree, so the
other diagonal would run the same backend gate twice. `standard` proves the deliberately smaller service;
`event-modelling` proves the larger one and carries the browser gate. Then the maximal selection on each store — the
SQLite one runs its whole contract inside the Docker-free gate — with the backend's own transport, read from the
catalog rather than listed, so a backend added last is never silently skipped. Then the production row: every row
before it leaves `--target` at `none`, and a production target is what wires the flags route into a project, so this
is where a linter first reads it. The image row is the backend on a managed target with the memory store, the
project `make build smoke-image` builds and starts.

**Which** managed target is the catalog's to say and not this module's. The clouds are packages, so a matrix run
has whichever of them the machine installed, and a row naming one by name would plan nothing on a machine that
installed the other. The first managed target the catalog offers is the one these two rows take, and a catalog
with none of them plans the rows that need no target and says so by leaving the other two out.

Pure over the catalog it is given: the plan probe passes the merged catalog of the package directory it was started
for, and a test can pass a copy.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..axes import catalog_axis_default

# The diagonals cover every profile only while there are exactly these. Frontends are whatever the installed
# languages ship, so their diagonals are read off the catalogue (`diagonals`) rather than written down here.
PROFILES = {"standard", "event-modelling"}
STORES = ("sqlite", "postgres")


def production_target(catalog: Mapping[str, Any]) -> str | None:
    """The target the production and image rows are planned against: the first managed one the catalog
    offers, or None where it offers none. In catalog order, so two machines with the same packages plan the
    same matrix."""
    return next((name for name, target in catalog["targets"].items() if target.get("managed")), None)


@dataclass(frozen=True)
class Row:
    """One project to generate: its name, profile, backend, frontend and every other answer, as `--<axis> <option>`."""

    name: str
    profile: str
    backend: str
    frontend: str
    answers: tuple[tuple[str, str], ...] = ()

    def arguments(self) -> list[str]:
        """The `slipwai generate` options this row stands for, after the project's name."""
        said = ["--profile", self.profile, "--backend", self.backend, "--frontend", self.frontend]
        for axis, option in self.answers:
            said += [f"--{axis}", option]
        return said


def takes(catalog: Mapping[str, Any], axis: str, option: str, backend: str, target: str) -> bool:
    """Whether this backend, on this target, can actually be generated with that answer.

    The same two questions `selection.py` asks before it refuses — is the option implemented for this
    backend, and is it offered under this target — read here so that a row generation would refuse is
    never planned. A row that cannot generate is not a failing matrix, it is a matrix that was written
    down wrong, and the two look identical in a CI log.

    The language template is what found this. Every real language implements both stores and Keycloak, so
    the rows were hard-coded and nothing noticed; the toy implements none of them, and its first matrix run
    planned four rows whose own refusals say `a half-ported version is deliberately not emitted`.
    """
    spec = catalog["axes"].get(axis)
    if not isinstance(spec, dict) or option not in spec.get("options", {}):
        return False
    held = spec["options"][option]
    return backend in held.get("backends", []) and target in held.get("targets", [])


def plannable(catalog: Mapping[str, Any], row: Row) -> bool:
    """Whether every answer this row names is one its backend can be generated with."""
    target = next((option for axis, option in row.answers if axis == "target"), "none")
    return all(takes(catalog, axis, option, row.backend, target)
               for axis, option in row.answers if axis != "target")


def covered(catalog: Mapping[str, Any]) -> None:
    """A `ValueError` unless the diagonals still cover every profile the catalog has."""
    if set(catalog["profiles"]) != PROFILES:
        raise ValueError(f"the matrix's diagonals cover {', '.join(sorted(PROFILES))}, and the catalog has "
                         f"profiles {', '.join(sorted(catalog['profiles']))}: add the rows that cover them")


def diagonals(catalog: Mapping[str, Any], backend: str) -> list[tuple[str, str]]:
    """`standard` with no browser app, and `event-modelling` beside each frontend `backend` can be generated
    with — or with none, where no installed language ships one.

    Each frontend rather than the default, because a frontend is a package's answer like an axis option and
    one no row generates is one nothing proves. Not one of another npm family's beside an npm backend:
    generation refuses that pair (`project/frontend.frontend_files`), and a planned row it refuses is a matrix
    written down wrong. Which families are npm is the catalogue's to say, by the frontends they ship.
    """
    family = catalog["backends"][backend].get("family")
    npm = {entry.get("family") for entry in catalog["frontends"].values()}
    offered = [name for name, entry in catalog["frontends"].items() if name != "none"
               and (family not in npm or entry.get("family") == family)]
    return [("standard", "none"), *(("event-modelling", name) for name in offered or ["none"])]


def native_rows(catalog: Mapping[str, Any], backend: str) -> list[Row]:
    """Every native-gate row of `backend`, in the order the root suite ran them."""
    covered(catalog)
    transport = catalog_axis_default(dict(catalog), "http", backend, "none")
    if transport == "none":
        # Either a backend that had a transport and lost one, or one that never offered any — the
        # template's toy is the second, deliberately. The matrix generates variants and runs each one's
        # native gate, and there is nothing to run against a backend that serves nothing, so it says so
        # rather than planning an empty matrix that passes.
        raise ValueError(
            f"backend {backend} answers no http option but `none`, so it has no variants to generate. "
            f"A package meant to be matrix-tested declares a transport; the conformance suite "
            f"(`python -m slipwai.conformance`) is what holds one that does not"
        )
    rows = [Row(f"verify-{profile}-{backend}-{frontend}", profile, backend, frontend)
            for profile, frontend in diagonals(catalog, backend)]
    every = (("http", transport), ("auth", "keycloak"), ("users", "keycloak"))
    rows += [Row(f"verify-{backend}-{store}", "event-modelling", backend, "none", (("persistence", store), *every))
             for store in STORES]
    where = production_target(catalog)
    if where is not None:
        # The identity answer is whichever one that target provisions, read off the catalog: it is the
        # target package's own option, so its name is the package's and never this module's.
        identity = next((option for option, held in catalog["axes"]["auth"]["options"].items()
                         if held.get(where, {}).get("provisions")), "none")
        production = (("persistence", "postgres"), ("http", transport), ("auth", identity), ("target", where))
        rows.append(Row(f"verify-production-event-modelling-{backend}", "event-modelling", backend, "none",
                        production))
    # Only the rows this backend can be generated with. The two diagonals name no answers and are always
    # plannable; the rest name stores, identity and a target, and a package that implements none of them —
    # the template's toy — is left with the two that prove what it does have.
    return [row for row in rows if plannable(catalog, row)]


def image_row(catalog: Mapping[str, Any], backend: str) -> Row | None:
    """The project whose production image `make build smoke-image` builds and starts for `backend`, or None
    where the catalog offers no managed target to build one for — there is no production image without a
    production to build it for."""
    where = production_target(catalog)
    if where is None:
        return None
    transport = catalog_axis_default(dict(catalog), "http", backend, where)
    return Row(f"built-{backend}", "event-modelling", backend, "none",
               (("target", where), ("persistence", "memory"), ("http", transport)))
