"""The target loader: a target package on disk, read for its row and imported for its answers.

The third kind of package, found in the same directory and by the same walk as the other two. Only the
manifest differs — `language.json`, `extension.json`, `target.json` — which is how each walk tells what is
its own without being told, and why a language's directory is skipped here rather than refused for lacking
something it never claimed to have.

**Two halves, for the reason the language's are two.** The manifest is read without importing anything, and
it is what the catalog's `targets` block gets: the label a prompt shows, the axes the target cannot take the
no-infrastructure answer to, the words its cloud refuses inside a project's name. The Python is imported from
the package's own directory and asked for `TARGET`, which is every answer the keel reads *while generating* —
the stacks, the scripts, the pages, the tools, the registry, the deploy steps. A listing, a menu and
`--target <name>` need only the first, so nothing imports a cloud's code to show its name.

**A refused target is refused alone, in one line.** Two clouds can be installed beside each other and one of
them broken; the other still generates projects. The same rule a language's refusal is held to, and for the
same reason: a package directory that generates nothing because one package is malformed makes every install
a risk somebody has to take all at once.

**The protocol is checked at import, not at use.** `target_protocol.faults` returns everything wrong at once
rather than the first thing, so a publisher fixing a package runs the suite once. Which of them apply is the
manifest's `managed` to say: a target the keel does not provision ships no stacks and is asked for none.
"""
from __future__ import annotations

import copy
import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .assets import this_command
from .errors import blame, one_line
from .language_directory import VARIABLE, Refused, parse_manifest
from .target_protocol import Target, faults
from .target_shape import catalogue_entry, validate
from .versions import below, satisfies

MANIFEST = "target.json"
#: Not a target at all: the directory holds another kind of package, or nothing the keel reads.
NO_MANIFEST = f"has no {MANIFEST}"


@dataclass(frozen=True)
class TargetPackage:
    """One target the walk kept: its name, the directory it is in, and its manifest as written."""

    name: str
    root: Path
    manifest: dict[str, Any]

    @property
    def entry(self) -> dict[str, Any]:
        """The row the catalog's `targets` block gets for it."""
        return catalogue_entry(self.manifest)

    @property
    def managed(self) -> bool:
        """Whether the keel provisions and deploys this target — its stacks, its images, its pipeline."""
        return bool(self.manifest.get("managed"))


def module_name(name: str) -> str:
    """The Python package a target's directory stands for: `slipwai_target_` and its name, dashes as `_`."""
    return f"slipwai_target_{name.replace('-', '_')}"


def named(name: str, root: Path) -> str:
    """How a refusal says which target: `target aws (/path/to/aws)`."""
    return f"target {name} ({root})"


def refusal(name: str, root: Path, fault: str) -> str:
    """The one line a refusal is. A manifest's text cannot make a second line out of it."""
    return one_line(f"{named(name, root)}: {fault}")


def holds_manifest(entry: Path) -> bool:
    """Whether this directory is a target at all, which is the one question the other walks ask it."""
    try:
        return (entry / MANIFEST).is_file()
    except OSError:
        return False


def schema_fault(name: str, manifest: dict[str, Any], core: str, installed: bool) -> str | None:
    """Why this keel cannot load the manifest's `core` range, ending on the move that fixes it.

    The same shape the other two kinds get: a range is a statement about two versions, and a message naming
    only one of them leaves the reader to guess which of them to move.
    """
    if satisfies(core, manifest["core"]):
        return None
    said = f"needs core schema {manifest['core']}, and this core speaks {core}"
    if below(core, manifest["core"]):
        return f"{said}: {this_command()} upgrade"
    if installed and not os.environ.get(VARIABLE):
        return f"{said}: {this_command()} target upgrade {name}"
    return f"{said}: it needs a version of {name} built for schema {core.split('.')[0]}"


def fault_in(name: str, root: Path, core: str, installed: bool = False) -> tuple[dict | None, str | None]:
    """The manifest of `root` a keel speaking schema `core` can load, or why it is refused."""
    manifest, fault = parse_manifest(root / MANIFEST, MANIFEST, NO_MANIFEST)
    if fault is not None:
        return None, fault
    try:
        validate(manifest)
    except ValueError as error:
        return None, str(error)
    if manifest["name"] != name:
        return None, (f"{MANIFEST}'s name is {manifest['name']}, and its directory is {name}. The two are one "
                      f"thing: `--target {manifest['name']}` looks for the directory of that name")
    fault = schema_fault(name, manifest, core, installed)
    return (manifest, None) if fault is None else (None, fault)


def read(root: Path, core: str, installed: bool = False) -> tuple[list[TargetPackage], list[str]]:
    """Every target in `root` this keel can load, and a line for each it cannot.

    Only a directory holding a `target.json` is looked at, so a language's or an extension's directory is not
    refused here for lacking one — the three walks share a tree and each ignores what the others own.
    """
    found: list[TargetPackage] = []
    refusals: list[str] = []
    if not root.is_dir():
        return found, refusals
    try:
        entries = sorted(root.iterdir())
    except OSError:  # a directory the keel may not list holds no target it can name
        return found, refusals
    for entry in entries:
        if entry.name.startswith(".") or not holds_manifest(entry):
            continue
        manifest, fault = fault_in(entry.name, entry, core, installed)
        if manifest is None:
            refusals.append(refusal(entry.name, entry, fault or NO_MANIFEST))
        else:
            found.append(TargetPackage(entry.name, entry, manifest))
    return found, refusals


def forget(module: str) -> None:
    """Take a module and its submodules out of `sys.modules`."""
    for loaded in [loaded for loaded in sys.modules if loaded == module or loaded.startswith(f"{module}.")]:
        del sys.modules[loaded]


def import_package(package: TargetPackage) -> Target:
    """The package's `TARGET`, imported from its own directory, or `Refused` with the one line."""
    module = module_name(package.name)

    def refused(fault: str) -> Refused:
        return Refused(refusal(package.name, package.root, fault))

    init = package.root / module / "__init__.py"
    if not init.is_file():
        raise refused(f"has no Python package {module}")
    specification = importlib.util.spec_from_file_location(module, init, submodule_search_locations=[str(init.parent)])
    if specification is None or specification.loader is None:
        raise refused(f"has no Python package {module}")
    forget(module)
    imported = importlib.util.module_from_spec(specification)
    sys.modules[module] = imported
    try:
        specification.loader.exec_module(imported)
    except BaseException as error:  # a package's code can raise anything; none of it is the keel's to crash on
        forget(module)
        raise refused(f"{module} failed to import: {blame(error)}") from None
    try:
        return declared_target(package, imported, module, refused)
    except Refused:
        forget(module)
        raise
    except BaseException as error:  # a module `__getattr__` or a property of the `Target` runs package code too
        forget(module)
        raise refused(f"{module} failed to import: {blame(error)}") from None


def declared_target(package: TargetPackage, imported: Any, module: str, refused: Any) -> Target:
    """The imported module's `TARGET`, checked against the manifest and against the protocol, or `Refused`."""
    try:
        target = imported.TARGET
    except AttributeError:
        raise refused(f"{module} has no TARGET") from None
    if not isinstance(target, Target):
        raise refused(f"{module}'s TARGET is a {type(target).__name__}, not a Target") from None
    if target.name != package.name:
        raise refused(f"{MANIFEST} is {package.name} and its TARGET is {target.name}. One name: it is the "
                      f"directory, the module and what `--target <name>` is typed as") from None
    if found := faults(target, package.managed):
        raise refused("; ".join(found)) from None
    return target


def axis_fault(catalog: dict[str, Any], axis: str, option: str | None = None) -> str | None:
    """Why this keel cannot read that (axis, option), or None. The manifest's shape is the publisher's to
    get right; which axes and options exist is the keel's, so this is where it is said."""
    if axis not in catalog["axes"]:
        return f"names the {axis} axis, which this keel does not declare"
    if option is not None and option not in catalog["axes"][axis]["options"]:
        return f"names {axis} option {option}, which this keel does not declare"
    return None


def menu_faults(catalog: dict[str, Any], package: TargetPackage) -> list[str]:
    """Everything in this target's three menu blocks that this keel cannot resolve, all of them at once."""
    manifest = package.manifest
    found = [f"requires the {axis} axis, which this keel does not declare"
             for axis in manifest.get("requires", ()) if axis not in catalog["axes"]]
    for axis, options in manifest.get("offers", {}).items():
        found += [fault for option in options if (fault := axis_fault(catalog, axis, option)) is not None]
    for axis, options in manifest.get("provisions", {}).items():
        brought = manifest.get("axes", {}).get(axis, {})
        found += [fault for option in options
                  if option not in brought and (fault := axis_fault(catalog, axis, option)) is not None]
    for axis, options in manifest.get("axes", {}).items():
        if (fault := axis_fault(catalog, axis)) is not None:
            found.append(fault)
            continue
        found += [f"declares {axis} option {option}, which this keel already declares"
                  for option in options if option in catalog["axes"][axis]["options"]]
    return found


def claimed_options(packages: list[TargetPackage]) -> dict[tuple[str, str], list[str]]:
    """Each option a target brings, and the targets that bring it. An option belongs to one package, here
    for the reason `catalog_options.declare_options` gives: nothing chooses between two claimants."""
    found: dict[tuple[str, str], list[str]] = {}
    for package in packages:
        for axis, options in package.manifest.get("axes", {}).items():
            for option in options:
                found.setdefault((axis, option), []).append(package.name)
    return found


def offers_of(package: TargetPackage) -> dict[str, set[str]]:
    """Every keel option this target offers, by axis: what it says it offers, plus what it provisions —
    provisioning an option is offering it, and a manifest carries one statement of one fact."""
    found: dict[str, set[str]] = {axis: set(options) for axis, options in package.manifest.get("offers", {}).items()}
    brought = package.manifest.get("axes", {})
    for axis, options in package.manifest.get("provisions", {}).items():
        found.setdefault(axis, set()).update(set(options) - set(brought.get(axis, {})))
    return found


def merge_targets(catalog: dict[str, Any], packages: list[TargetPackage]) -> list[str]:
    """Fold each installed target into `catalog`, and return a line for each refused.

    Four contributions, and a target makes all of them or none: its row in the `targets` block, the keel
    options it offers, what each of those becomes there, and the answers that are its own. All or none
    because a catalog carrying an option offered under a target that is not in the `targets` block is one
    no default can be resolved against — the half-ported shape this factory refuses everywhere else.

    The two things refused here rather than in the manifest are the two that are facts about *this* keel: an
    axis or an option it does not declare, and a name something already holds. A manifest is right or wrong
    on its publisher's machine; neither of those can be known there.
    """
    refusals: list[str] = []
    claimed = claimed_options(packages)
    for package in packages:
        found = list(menu_faults(catalog, package))
        if package.name in catalog["targets"]:
            found.append(f"is already a target this catalog offers; two cannot both be `{package.name}`")
        for (axis, option), claimants in sorted(claimed.items()):
            if package.name not in claimants or len(claimants) < 2:
                continue
            others = ", ".join(sorted(name for name in claimants if name != package.name))
            found.append(f"declares {axis} option {option}, which {others} also declares; an option belongs "
                         f"to one target, and nothing here chooses between them")
        if found:
            refusals.append(refusal(package.name, package.root, "; ".join(found)))
            continue
        declare(catalog, package)
    return refusals


def declare(catalog: dict[str, Any], package: TargetPackage) -> None:
    """One target's whole contribution, written into the catalog. Called only once it is known to fit."""
    name = package.name
    catalog["targets"][name] = package.entry
    for axis, options in package.manifest.get("axes", {}).items():
        for option, declared in options.items():
            # Deep-copied: a catalog holding the manifest's own lists would let an edit of one change the
            # other, and this catalog is written into a generated project.
            entry = copy.deepcopy(declared)
            entry["backends"] = list(entry.get("backends", ()))
            entry["targets"] = [name]
            catalog["axes"][axis]["options"][option] = entry
    for axis, options in sorted(offers_of(package).items()):
        for option in sorted(options):
            catalog["axes"][axis]["options"][option]["targets"].append(name)
    for axis, options in package.manifest.get("provisions", {}).items():
        for option, as_what in options.items():
            catalog["axes"][axis]["options"][option][name] = {"provisions": as_what}
