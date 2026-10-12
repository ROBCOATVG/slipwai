"""Project-wide deployment choice, and package-owned files for that choice.

The target's older ``SHAPES`` member names bootstrap/service phases. These rows name a skiff or a liner;
keeping them separate lets a package change compute without teaching the keel a provider name.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from .errors import GenerationError
from .loaded_targets import answer, root_of
from .target_protocol import DEPLOYMENT_SHAPES

CHOICES = ("skiff", "liner")


def selected(requested: str | None, *, existing: bool = False) -> str:
    """An old manifest means its existing liner; a new project starts small unless explicitly overridden.

    This used to take the product's state as well and answer `liner` for one already in service. Nothing
    ever gave it one: no manifest records a state — `project/metadata.py` writes no such field — and the
    only caller that could have, `recorded`, passes `existing=True`, which decides the answer before the
    state is looked at. A parameter steering by a mark nothing sets is worse than no parameter, because it
    reads as a rule somebody could rely on. The decision a person makes is `--shape`, and an existing
    manifest keeps what it has.
    """
    if requested is not None:
        if requested not in CHOICES:
            raise GenerationError(f"unknown deployment shape {requested!r}; use --shape skiff or --shape liner")
        return requested
    return "liner" if existing else "skiff"


def recorded(document: dict[str, Any]) -> str:
    """Missing is the pre-shape contract, which must never silently shrink a data-holding project."""
    return selected(document.get("shape"), existing=True)


def row(target: str, shape: str) -> dict[str, Any] | None:
    """A package row, or the legacy liner protocol when a package has not added deployment choices."""
    selected(shape)
    rows = answer(target, DEPLOYMENT_SHAPES, default={})
    if not rows and shape == "liner":
        return None
    found = rows.get(shape)
    if not isinstance(found, dict):
        raise GenerationError(f"target {target} does not offer {shape}; use --shape liner or install an updated target")
    for key in ("compute", "database", "guidance", "transition"):
        if not isinstance(found.get(key), str) or not found[key].strip():
            raise GenerationError(f"target {target} {shape} has no {key}; install an updated target package")
    environments = found.get("environments")
    if (not isinstance(environments, tuple) or not environments
            or any(not isinstance(name, str) or not name for name in environments)):
        raise GenerationError(f"target {target} {shape} has invalid environments; install an updated target package")
    expected = ("production",) if shape == "skiff" else ("staging", "production")
    if environments != expected:
        raise GenerationError(
            f"target {target} {shape} must have environments {expected}; install an updated target package"
        )
    stacks = found.get("stacks")
    if not isinstance(stacks, dict) or set(stacks) != {"bootstrap", "service"}:
        raise GenerationError(f"target {target} {shape} needs bootstrap and service stacks; install an updated target")
    for phase, files in stacks.items():
        check_files(target, files, prefix=f"{phase}/")
    check_files(target, found.get("scripts"), prefix="scripts/")
    return found


def check_files(target: str, files: object, *, prefix: str) -> None:
    """Both package sources and generated destinations stay in their declared trees, including symlinks."""
    if not isinstance(files, dict) or not files:
        raise GenerationError(f"target {target} shape has no {prefix} files; install an updated target package")
    root = root_of(target).resolve()
    for destination, source in files.items():
        for name in (destination, source):
            if (not isinstance(name, str) or "\\" in name or PurePosixPath(name).is_absolute()
                    or ".." in PurePosixPath(name).parts or PurePosixPath(name).as_posix() != name):
                raise GenerationError(f"target {target} shape has unsafe file {name!r}; install an updated target")
        if not destination.startswith(prefix) or not (root / source).resolve().is_relative_to(root):
            raise GenerationError(f"target {target} shape file escapes {prefix}; install an updated target package")
        if not (root / source).is_file():
            raise GenerationError(f"target {target} shape is missing {source}; install an updated target package")
