"""The other half of the loader: an extension on disk, read from the same directory a language is read from.

An extension is a package the way a language is — a directory, a manifest, and the files the manifest's hooks
name — and it is found in the same place, by the same walk. Only the manifest differs: `language.json` for one,
`extension.json` for the other, which is how a reader and the loader both tell them apart without being told.

**Two halves, because they are read for different reasons.** A language's fragment is merged into the catalog
and its Python is imported to answer the backend protocol; an extension's manifest contributes a catalogue
entry, a set of hooks and a directory of files to copy into a project, and imports nothing into this process.
Sharing one reader would mean one module holding both sets of rules and a `kind` branch in every function.

**What is copied is what runs or is read in a project.** `init.py`, whatever it calls, whatever it ships beside
it: the keel does not model an extension's internals, so it does not get to decide which of its files matter.
What it leaves behind is the manifest, because the project is not where it is read, and the package's own
repository — its workflows, tests and changelog — which `extension_given` names and nothing in a project runs.

**A refused extension is refused alone.** Same rule as a language's: one line naming the extension, its
directory and the fault, and the others load — an extension is optional dev tooling, and a project that cannot
be generated because something optional is malformed has the dependency backwards.
"""
from __future__ import annotations

import os
import posixpath
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .assets import this_command
from .errors import one_line
from .extension_shape import catalogue_entry, validate
from .guards import declared as guards_declared
from .hooks import declared
from .language_directory import VARIABLE, parse_manifest
from .versions import below, satisfies

MANIFEST = "extension.json"


@dataclass(frozen=True)
class Extension:
    """One extension the walk kept: its key, the directory it is in, and its manifest as written."""

    name: str
    root: Path
    manifest: dict[str, Any]

    @property
    def entry(self) -> dict[str, Any]:
        """What the catalogue's `extensions` block gets for it."""
        return catalogue_entry(self.manifest)

    @property
    def hooks(self) -> dict[str, dict]:
        """Its hooks, normalised, keyed by the point each attaches to."""
        return declared(self.manifest)

    @property
    def guards(self) -> dict[str, dict]:
        """Its guards, normalised, keyed by the moment each may refuse at. The second closed set: a hook is
        never fatal to a rung, and a guard may refuse one tool call."""
        return guards_declared(self.manifest)


def named(name: str, root: Path) -> str:
    """How a refusal says which extension: `extension codegraph (/path/to/codegraph)`."""
    return f"extension {name} ({root})"


def refusal(name: str, root: Path, fault: str) -> str:
    """The one line a refusal is. A manifest's text cannot make a second line out of it."""
    return one_line(f"{named(name, root)}: {fault}")


def holds_manifest(entry: Path) -> bool:
    """Whether this directory is an extension at all, which is the one question the language half asks it."""
    try:
        return (entry / MANIFEST).is_file()
    except OSError:
        return False


def schema_fault(name: str, manifest: dict[str, Any], core: str, installed: bool) -> str | None:
    """Why this keel cannot load the manifest's `core` range, ending on the command that moves whichever of
    the two is behind. The same shape a language's gets, for the same reason: a range is a statement about
    two versions, and a message naming only one of them leaves the reader to guess which to move."""
    if satisfies(core, manifest["core"]):
        return None
    said = f"needs core schema {manifest['core']}, and this core speaks {core}"
    if below(core, manifest["core"]):
        return f"{said}: {this_command()} upgrade"
    if installed and not os.environ.get(VARIABLE):
        return f"{said}: {this_command()} extension upgrade {name}"
    return f"{said}: it needs a version of {name} built for schema {core.split('.')[0]}"


def fault_in(name: str, root: Path, core: str, installed: bool = False) -> tuple[dict | None, str | None]:
    """The manifest of `root` a keel speaking schema `core` can load, or why it is refused."""
    manifest, fault = parse_manifest(root / MANIFEST, MANIFEST, f"has no {MANIFEST}")
    if fault is not None:
        return None, fault
    try:
        validate(manifest)
    except ValueError as error:
        return None, str(error)
    if manifest["key"] != name:
        return None, (f"extension.json's key is {manifest['key']}, and its directory is {name}. The two are "
                      f"one thing: `./init --extension {manifest['key']}` looks for the directory of that name")
    fault = schema_fault(name, manifest, core, installed)
    return (manifest, None) if fault is None else (None, fault)


def read(root: Path, core: str, installed: bool = False) -> tuple[list[Extension], list[str]]:
    """Every extension in `root` this keel can load, and a line for each it cannot.

    Only a directory holding an `extension.json` is looked at, so a language's directory is not refused here
    for lacking one — the two halves walk the same tree and each ignores what the other owns.
    """
    found: list[Extension] = []
    refusals: list[str] = []
    if not root.is_dir():
        return found, refusals
    try:
        entries = sorted(root.iterdir())
    except OSError:  # a directory the keel may not list holds no extension it can name
        return found, refusals
    for entry in entries:
        if entry.name.startswith(".") or not holds_manifest(entry):
            continue
        manifest, fault = fault_in(entry.name, entry, core, installed)
        if manifest is None:
            refusals.append(refusal(entry.name, entry, fault or f"has no {MANIFEST}"))
        else:
            found.append(Extension(entry.name, entry, manifest))
    return found, refusals


def files(root: Path) -> list[Path]:
    """Every file of the package but its manifest, relative to the package root, in a stable order.

    Stable because the files of a generated project are taken from this list (`extension_given` says which),
    and a project whose contents depend on the order a directory happened to be walked in is a project two
    generations disagree about.
    """
    found = (path.relative_to(root) for path in root.rglob("*")
             if path.is_file() and path.name != MANIFEST and ".git" not in path.parts)
    # On the string and not the `Path`: Windows compares a path without case, so the same package was listed in
    # another order there, and a promise of a stable order is a promise about every platform.
    return sorted(found, key=lambda path: path.as_posix())


def absent(root: Path, manifest: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Every hook and guard the manifest declares whose script the package does not ship, as (`hook` or `guard`,
    the point, the path it names), in that order.

    A hook is run as `scripts/extensions/<key>/<run>` in a project, and what a project is given is `files`; so a
    script that is not in that list is a hook that never runs, in every project, and nothing says so but one line
    per rung in a log (`codegraph` 1.0.0 and `hooks/sync.py`, #117). The default declarations are held to as written
    ones are: `project` fires `init.py` whether or not the manifest says it. Compared as the strings a project on a
    case-sensitive file system would look for, so a package that passes here passes there. A manifest's `tools` are
    names an agent calls, not files, and there is nothing of theirs to ship.
    """
    shipped = {path.as_posix() for path in files(root)}
    declarations = (("guard", guards_declared(manifest)), ("hook", declared(manifest)))
    return sorted((kind, name, str(body["run"])) for kind, found in declarations for name, body in found.items()
                  if posixpath.normpath(str(body["run"]).replace("\\", "/")) not in shipped)
