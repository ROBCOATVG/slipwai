"""The catalog, as the keel's `catalog.json` with every loaded language's fragment folded in.

The keel's file lists the backends it still carries, each with an `order`; a fragment (`language.json`) declares one
for itself. The merge sorts every backend by `(order, where it was declared)` — the keel's rows before a fragment's
at a tie, a fragment's in the order it lists them — strips the key, and orders each option's `backends` and each
per-backend default the same way, so one order is the menus', `--help`'s and the registry's.

A fragment is checked against the keel here, not trusted: a backend key another package or the keel holds, an axis,
option or target the keel does not declare, a default the backend's own options cannot take. One package that
fails any of it is refused alone, in the one line `language_directory` fixes, and the rest merge.

A framework package (one that `requires` its family) joins its family rather than claiming it, and is held to the
family package's `VERSION`, read as the release a snapshot is heading for (ADR 0004). A family with no backend of
its own names the framework it defaults to, which becomes `default.framework` only where two or more of the
family's backends merged and one of them answers it.
"""
from __future__ import annotations

import copy
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .assets import this_command
from .catalog_options import declare_options
from .language_directory import (
    NO_FRAGMENT,
    VARIABLE,
    Package,
    named,
    parse_fragment,
    refusal,
    reinstall,
    reinstalling,
    schema_command,
    shape_fault,
)
from .versions import base, below, is_release, is_snapshot, satisfies


def claims(packages: list[Package]) -> dict[str, list[Package]]:
    """Each backend key, and the packages whose fragments declare it."""
    found: dict[str, list[Package]] = {}
    for package in packages:
        for key in package.fragment["backends"]:
            found.setdefault(key, []).append(package)
    return found


def family_claims(packages: list[Package]) -> dict[str, list[Package]]:
    """Each family name a fragment gives, and the packages that give it."""
    found: dict[str, list[Package]] = {}
    for package in packages:
        found.setdefault(package.fragment["family"], []).append(package)
    return found


def is_framework(package: Package) -> bool:
    """Whether a package is a framework of a family it requires, rather than a family of its own."""
    return "requires" in package.fragment


def requires_fault(
    package: Package, kept: Mapping[str, Package], installed: bool = False, schema: str = ""
) -> str | None:
    """Why a framework cannot load beside the family packages `kept`, or None: its family package missing (or not
    declaring that family), its `VERSION` unreadable, or outside the range. A snapshot is held as its release.
    `installed`: the packages are the package directory's, read by a keel speaking `schema`, so the line ends on the
    command that fixes it (D116 #2)."""
    ((family, wanted),) = package.fragment["requires"].items()
    need = f"requires {family} {wanted}"
    home = kept.get(family)
    if home is None or is_framework(home) or home.fragment["family"] != family:
        return need + family_missing(package, family, schema, installed)
    broken = reinstall(package.name, family) if installed else ""
    try:
        version = (home.root / "VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return f"{need}; {family} has no VERSION{broken}"
    except (OSError, UnicodeDecodeError):
        return f"{need}; {family}'s VERSION cannot be read{broken}"
    held = base(version) if is_release(version) or is_snapshot(version) else None
    if held is None:
        return f"{need}; {family}'s VERSION ({version!r}) is not a release or a snapshot{broken}"
    try:
        if satisfies(held, wanted):
            return None
        behind = below(held, wanted)
    except ValueError:  # defensive: `parse` already keeps every number short enough to read
        return f"{need}; {family}'s VERSION ({version!r}) is not a release or a snapshot{broken}"
    # No move over SLIPWAI_LANGUAGES: either upgrade would replace the person's own directory.
    moves = f"; {this_command()} language upgrade {family if behind else package.name}" if own(installed) else ""
    return f"{need}; {family} {version} is loaded" + (f", held as {held}" if held != version else "") + moves


def own(installed: bool) -> bool:
    """Whether a line may name a command that replaces an installed package: the default directory's, never one
    `SLIPWAI_LANGUAGES` names (D116 #3, D124)."""
    return installed and not os.environ.get(VARIABLE)


def family_missing(package: Package, family: str, schema: str, installed: bool = True, imported: bool = False) -> str:
    """The ending of a framework's line whose family did not load. Absent, it is not loaded, and installing it is the
    fix; installed and refused itself (at import: `imported`), the command its own line ends on, so this line stands
    alone (D122 2) — never `install`, which would answer "already installed" (S11 N004) — or, where that line ends on
    none, that it says the fault. `installed` False (admission): only that it is not loaded."""
    root = package.root.parent / family
    if not installed:
        return f"; {family} is not loaded"
    if not root.is_dir():
        return f"; {family} is not loaded; {this_command()} language install {family}"
    command = fix(family, root, schema, imported)
    return f"; {family} is installed and refused" + (f": {command}" if command else ", as its own line says")


def fix(name: str, root: Path, core: str, imported: bool = False) -> str:
    """The command the installed package `name`'s own refusal line ends on, read from its directory as that line was
    made, or '' where it ends on none: built for another keel, the upgrade that moves it; a `language.json` the
    keel cannot read, or Python that would not import (`imported`), remove-then-install (remove alone with
    no `language.json`);
    refused beside another package (a claim both make), nothing. The one place a refused family's fix is found for a
    framework's line (D122 2); the command is never parsed back out of the family's text."""
    fragment, fault = parse_fragment(root / "language.json")
    if fault is None and not isinstance(fragment, dict):
        fault = "language.json is not a JSON object"
    if fault is None and (fault := shape_fault(name, fragment)) is None:
        try:
            moves = schema_command(name, fragment, core)
        except ValueError:  # a range that does not parse is a malformed language.json
            return reinstalling(name)
        return moves or (reinstalling(name) if imported else "")
    return reinstalling(name, back=fault != NO_FRAGMENT)


def framework_defaults(catalog: dict[str, Any], packages: list[Package]) -> None:
    """Each family package's `default_framework` into `default.framework`, where two or more of the family's backends
    are in `catalog` and one answers it; one backend is one answer, and a default none answers is no default."""
    defaults = catalog["default"].setdefault("framework", {})
    for package in packages:
        chosen, family = package.fragment.get("default_framework"), package.fragment["family"]
        members = [row for row in catalog["backends"].values() if row.get("family") == family]
        answered = any(row.get("framework") == chosen for row in members)
        if chosen is not None and not is_framework(package) and len(members) > 1 and answered:
            defaults[family] = chosen


def framework_claims(packages: list[Package]) -> dict[tuple[str, str], list[Package]]:
    """Each `(family, framework)` a fragment's rows give, and the packages that give it."""
    found: dict[tuple[str, str], list[Package]] = {}
    for package in packages:
        for row in package.fragment["backends"].values():
            if "framework" in row:
                found.setdefault((package.fragment["family"], row["framework"]), []).append(package)
    return found


def framework_faults(
    core: Mapping[str, Any], package: Package, frameworks: dict[tuple[str, str], list[Package]]
) -> list[str]:
    """A framework of a family claimed by another package too (both are refused, as a backend key is: D45), or by
    one of the keel's own rows of that family. Judged in turn, the first to sort would otherwise take the name."""
    family, faults = package.fragment["family"], []
    named_here = (row["framework"] for row in package.fragment["backends"].values() if "framework" in row)
    for framework in dict.fromkeys(named_here):
        if any(row.get("family") == family and row.get("framework") == framework for row in core["backends"].values()):
            faults.append(f"declares framework {framework} of family {family}, which core already has")
        faults += [
            f"declares framework {framework} of family {family}, which {named(other.name, other.root)} also declares"
            for other in frameworks[(family, framework)] if other is not package
        ]
    return list(dict.fromkeys(faults))


def faults_in(
    core: Mapping[str, Any], package: Package, held: dict[str, list[Package]], families: dict[str, list[Package]],
    frameworks: dict[tuple[str, str], list[Package]],
) -> list[str]:
    """Everything wrong with one fragment beside the keel and the other packages."""
    faults: list[str] = framework_faults(core, package, frameworks)
    family = package.fragment["family"]
    # A family the keel's backends already name may be shared; one keel does not have is declared by one package alone.
    # A framework joins the family it requires and is never a claim on it.
    if family not in {row.get("family") for row in core["backends"].values()} and not is_framework(package):
        faults += [
            f"declares family {family}, which {named(other.name, other.root)} also declares"
            for other in families[family] if other is not package and not is_framework(other)
        ]
    for key, row in package.fragment["backends"].items():
        if key in core["backends"]:
            faults.append(f"declares backend {key}, which core already has")
        for other in held[key]:
            if other is not package:
                faults.append(f"declares backend {key}, which {named(other.name, other.root)} also declares")
        faults += row_faults(core, key, row, package.fragment.get("axes", {}))
    return faults


def row_faults(
    core: Mapping[str, Any], key: str, row: Mapping[str, Any], brought: Mapping[str, Any] | None = None,
) -> list[str]:
    """What a fragment's row says that neither the keel nor the fragment itself declares.

    `brought` is the fragment's own `axes` block: a package answering an option it declares is answering
    one that exists, and checking it against the keel alone would refuse every package that brings a
    framework — which is every language package there is.
    """
    faults: list[str] = []
    options: Mapping[str, list[str]] = row.get("options", {})
    # A target this installation has no row for, and an option no installed target offers, are not faults:
    # they are answers this machine cannot reach, and `reachable` prunes them. An *axis* is different — the
    # keel declares every axis there is, so one it does not have is a mistake in the package, not a gap.
    for axis in options:
        if axis not in core["axes"]:
            faults.append(f"backend {key} answers axis {axis}, which core does not declare")
    for axis, name in row.get("defaults", {}).items():
        if axis not in core["default"]:
            faults.append(f"backend {key} defaults axis {axis}, which core does not declare")
        elif not isinstance(core["default"][axis], dict):
            faults.append(
                f"backend {key} defaults {axis}, and core's {axis} default is one answer, not one per backend"
            )
        elif name not in options.get(axis, []):
            faults.append(
                f"backend {key} defaults {axis} to {name}, which is not among its {axis} options "
                f"({', '.join(options.get(axis, []))})"
            )
    return faults


def reachable(merged: Mapping[str, Any], row: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """`row` with every answer this catalogue cannot reach taken out of it, and a line per answer taken.

    Which clouds are installed is a fact about a machine, not about a package. Every published language
    names every cloud it has deployment answers for, and a person installs the clouds they deploy to —
    most often none. Refusing the whole backend for the gap is what left a person with a language
    installed and `--language {}` offered, and `generate --target none` — the local-only path, which needs
    no cloud at all — refused outright.

    So the answer is pruned and the backend keeps the rest, which is only what the keel already does one
    level up: `merge_targets` drops an option no installed target offers, which is why `auth0` sits in
    `catalog.json` and not in `CORE` until a cloud that offers it arrives. This makes the two agree.

    A default whose option has just been pruned goes with it rather than being left dangling: a default is
    a pointer into the options beside it, and one pointing at an answer that is no longer there would be
    read as a choice nobody can take. Pruning cannot hide a typo for long — a package's own CI installs
    the siblings it names (`package_sources`), so a target that exists nowhere fails there, which is the
    gate that can tell a misspelling from an absence. This one cannot.
    """
    targets = [one for one in row.get("targets", []) if one in merged["targets"]]
    options = {
        axis: [name for name in names if name in merged["axes"][axis]["options"]]
        for axis, names in row.get("options", {}).items()
    }
    defaults = {axis: name for axis, name in row.get("defaults", {}).items() if name in options.get(axis, [])}
    gone = [f"target {one}" for one in row.get("targets", []) if one not in targets]
    gone += [f"{axis} option {name}" for axis, names in row.get("options", {}).items()
             for name in names if name not in options[axis]]
    return {**row, "targets": targets, "options": options, "defaults": defaults}, gone


def merge(
    core: dict[str, Any], packages: list[Package], installed: bool = False
) -> tuple[dict[str, Any], dict[str, str], dict[str, list[str]]]:
    """The keel with every package folded in, a line for each package refused, and the answers pruned.

    The third is not a refusal and must never be printed as one: an answer this installation cannot reach
    is a gap in what is installed, not a fault in the package. It is what `slipwai list` says under the
    language, because that is where a person asks what they can have. `core` is left as it
    was; `installed` as `requires_fault`'s."""
    held, families, frameworks = claims(packages), family_claims(packages), framework_claims(packages)
    refused: dict[str, str] = {}
    for package in packages:
        faults = faults_in(core, package, held, families, frameworks)
        if faults:
            refused[package.name] = refusal(package.name, package.root, "; ".join(faults))
    homes = {package.name: package for package in packages if package.name not in refused}
    for package in [package for package in packages if package.name in homes and is_framework(package)]:
        if (fault := requires_fault(package, homes, installed, str(core.get("schemaVersion", "")))) is not None:
            refused[package.name] = refusal(package.name, package.root, fault)
    kept = [package for package in packages if package.name not in refused]
    merged = copy.deepcopy(core)
    declared = declare_options(merged, kept)
    for name, fault in declared.items():
        refused.setdefault(name, fault)
    kept = [package for package in kept if package.name not in declared]
    rows: list[tuple[str, dict[str, Any], int]] = [
        (key, row, row.get("order", 0)) for key, row in merged["backends"].items()
    ]
    # Pruned here, after `declare_options`, because that is the first moment the catalogue is whole: the
    # keel's rows, every installed target's, and every kept package's own. What a row may answer is what
    # is in it now.
    pruned: dict[tuple[str, str], dict[str, Any]] = {}
    unreachable: dict[str, list[str]] = {}
    for package in kept:
        for key, row in package.fragment["backends"].items():
            pruned[(package.name, key)], gone = reachable(merged, row)
            if gone:
                unreachable.setdefault(package.name, []).extend(gone)
    for package in kept:
        fragment = package.fragment
        for key, row in fragment["backends"].items():
            built: dict[str, Any] = {"family": fragment["family"]}
            if "framework" in row:
                built["framework"] = row["framework"]
            rows.append((key, {**built, "label": row["label"],
                               "targets": pruned[(package.name, key)]["targets"]}, fragment["order"]))
    rows.sort(key=lambda entry: entry[2])
    merged["backends"] = {key: {k: v for k, v in row.items() if k != "order"} for key, row, _ in rows}
    rank = {key: index for index, (key, _, _) in enumerate(rows)}
    for package in kept:
        for key in package.fragment["backends"]:
            row = pruned[(package.name, key)]
            for axis, names in row["options"].items():
                for name in names:
                    merged["axes"][axis]["options"][name]["backends"].append(key)
            for axis, name in row["defaults"].items():
                merged["default"][axis][key] = name
    for axis in merged["axes"].values():
        for option in axis["options"].values():
            option["backends"].sort(key=lambda key: rank[key])
    for axis, answer in merged["default"].items():
        if isinstance(answer, dict) and set(answer) <= set(rank):
            merged["default"][axis] = {key: answer[key] for key in sorted(answer, key=lambda key: rank[key])}
    framework_defaults(merged, kept)
    return merged, refused, unreachable


def retract(catalog: dict[str, Any], package: Package) -> None:
    """Take a package's backends back out of a merged catalog, in place: its rows, list entries and defaults."""
    keys = set(package.fragment["backends"])
    for key in keys:
        catalog["backends"].pop(key, None)
    for axis in catalog["axes"].values():
        for option in axis["options"].values():
            option["backends"] = [key for key in option["backends"] if key not in keys]
    # Only an axis's default is keyed by backend; `framework`, beside them, is keyed by family, and a backend a
    # package named for a family the keel has (`java`) must not take that family's default with it.
    for axis in catalog["axes"]:
        answer = catalog["default"].get(axis)
        if isinstance(answer, dict):
            for key in keys:
                answer.pop(key, None)
    # A family default stays only while two of the family's backends are left and one answers it.
    defaults = catalog["default"].get("framework")
    for family, chosen in list(defaults.items()) if isinstance(defaults, dict) else []:
        members = [row for row in catalog["backends"].values() if row.get("family") == family]
        if len(members) < 2 or not any(row.get("framework") == chosen for row in members):
            del defaults[family]
