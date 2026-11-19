"""An extension file a project is no longer given, where the project had changed its copy: kept, never a conflict.

Since #119 a project's `scripts/extensions/<key>/` holds what runs or is read there, so the first migration
after it has the factory's side *deleting* each package's workflows, tests and changelog. Git does the rest
where the project left its copy as it was given: unchanged on one side and deleted on the other is deleted.
Where somebody changed one, git stops — deleted by the factory, modified here — and a person would be asked
to resolve a conflict over a file nothing reads.

The answer is known, so it is given: the project's file stays exactly as it is, staged as the merge's result,
and the catch-up page names it (`extension_copies.left`). Only a path `extension_given` holds back is settled
this way. A file the *package* dropped that this project had changed is a real conflict and still the
project's to decide, as is every other.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .extension_directory import MANIFEST
from .extension_given import repository_only
from .extension_shape import withheld
from .language_directory import directory
from .migration_manifest import conclude
from .migration_manifest import settled as manifest_settled
from .toolkit import EXTENSION_ROOT


def held_back(path: str, packages: Path) -> bool:
    """Whether a project-relative path is a file of an extension's copy that a project is no longer given."""
    _, found, inside = f"/{path}".partition(f"/{EXTENSION_ROOT}/")
    key, _, relative = inside.partition("/")
    if not found or not relative:
        return False
    try:
        more = withheld(json.loads((packages / key / MANIFEST).read_text(encoding="utf-8")))
    except (OSError, ValueError, AttributeError):
        more = ()
    return repository_only(relative, more)


def deleted_by_the_factory(root: Path, path: str) -> bool:
    """Whether the merge stopped on this path because the factory's side has no such file and this side has."""
    listed = subprocess.run(["git", "ls-files", "--unmerged", "--", path], cwd=root, text=True,
                            capture_output=True, check=False).stdout.splitlines()
    stages = {line.split("\t")[0].split()[-1] for line in listed if "\t" in line}
    return "2" in stages and "3" not in stages


def settled(root: Path, conflicts: tuple[str, ...], packages: Path | None = None) -> tuple[str, ...]:
    """The conflicts a merge in progress still has once the ones with a known answer are settled: an extension
    file a project is no longer given keeps this project's copy, and `project.json` is merged as a record."""
    where = directory() if packages is None else packages
    kept = [path for path in conflicts if held_back(path, where) and deleted_by_the_factory(root, path)]
    if not kept:
        return manifest_settled(root, conflicts)
    subprocess.run(["git", "add", "--", *kept], cwd=root, capture_output=True, check=True)
    left = tuple(path for path in conflicts if path not in kept)
    if not left:
        conclude(root)
        return left
    return manifest_settled(root, left)
