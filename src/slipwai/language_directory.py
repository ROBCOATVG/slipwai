"""Where languages live on disk, and how a package in that directory is read and imported.

A language is a directory: `language.json`, the fragment of the catalog it adds, and `slipwai_language_<name>/`,
the Python that answers the backend protocol. `SLIPWAI_LANGUAGES` names the one directory the keel looks in and
replaces the default, `~/.slipwai/packages`, whole; the same code runs in a checkout, the wheel and the
executable, and only what is in the directory differs.

**The default used to be `languages/`, and an install made under that name is moved on the way past** — the
directory holds extensions too, and one called `languages/` with `codegraph` in it is a small lie that costs
an hour later (decided 2026-10-06, carried by 8.3). It is one rename, made the first time anything asks
where packages are, because every verb asks: a move that waited for `upgrade` would leave every other
command finding nothing on a machine nobody had upgraded. The variable keeps its name, being one that is
already set in somebody's CI.

Two phases, because a package's Python imports the keel modules that import the catalog, and the catalog is built
from the fragments: `read` takes the fragments alone and refuses what they get wrong, and `import_package`
imports one package's Python later, when the registry is first asked for. Neither installs anything, touches
`sys.path` or reads an entry point. Every fault in either phase is one line, `language <name> (<directory>):
<fault>`, and a refused package is dropped while the others load.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .assets import moved_home, this_command
from .axes import under_current_names
from .errors import blame, one_line
from .language_shape import family_fault, name_fault, row_shape_fault
from .registry import Family, Language
from .versions import below, satisfies

VARIABLE = "SLIPWAI_LANGUAGES"
EXTENSION_MANIFEST = "extension.json"  # the other kind of package, read by `extension_directory`
TARGET_MANIFEST = "target.json"  # and the third, read by `target_directory`
#: The manifests that say a directory belongs to another walk. Here rather than in each of those modules
#: because this is the walk that has to know what is *not* its own, and the one they import from.
OTHER_MANIFESTS = (EXTENSION_MANIFEST, TARGET_MANIFEST)
NO_FRAGMENT = "has no language.json"  # not a language at all: removed, never installed back (T017)
# Each required key of `language.json`, with what it must be.
REQUIRED: tuple[tuple[str, type, str], ...] = (
    ("name", str, "a string"),
    ("core", str, "a string"),
    ("order", int, "an integer"),
    ("family", str, "a string"),
    ("backends", dict, "an object"),
)
# What a language, a backend, a family and a framework are called: a lower-case slug, as the built-ins' are. A name
# becomes a directory, a Python module, a path under `assets/` and a key; one that is not a slug is not a name.


class Refused(Exception):
    """A package that cannot load, said as the one line the user reads."""


@dataclass(frozen=True)
class Package:
    """One package phase 1 kept: its name, the directory it is in and its fragment as written."""

    name: str
    root: Path
    fragment: dict[str, Any]


def directory() -> Path:
    """The one directory the keel looks in: the variable if set, otherwise `~/.slipwai/packages`."""
    named = os.environ.get(VARIABLE)
    return Path(named) if named else moved_home(Path.home() / ".slipwai")



def module_name(name: str) -> str:
    """The Python package a language's directory stands for: `slipwai_language_` and its name, dashes as `_`."""
    return f"slipwai_language_{name.replace('-', '_')}"


def named(name: str, root: Path) -> str:
    """How a refusal and a claim say which package: `language go (/path/to/go)`."""
    return f"language {name} ({root})"


def refusal(name: str, root: Path, fault: str) -> str:
    """The one line a refusal is. A name, a directory and a fault can carry text a package controls, newlines
    included; none of it gets to make a second line."""
    return one_line(f"{named(name, root)}: {fault}")


def reinstalling(*names: str, back: bool = True) -> str:
    """The command that fixes an installed package's structural fault: take it out and put it back — a framework with
    the family whose fault it is, removed first and installed last (D116 #3) — or only take it out, where it is no
    language to put back (`back`, T017). What is taken out is the directory; what is put back is the package its
    `language.json` names, where that can be read. None under `SLIPWAI_LANGUAGES`: that directory is the
    person's own, often a working checkout, and no line tells them to delete it."""
    if os.environ.get(VARIABLE):
        return ""
    kept = frameworks_of(names)
    if kept:  # its frameworks out first and back after, each bringing its family; never the family's default
        back, put = True, [*(released(n) for n in reversed(names) if n not in families_of(kept)), *kept]
    else:
        put = [released(n) for n in reversed(names)]
    then = f", then {this_command()} language install {arguments(put)}"
    return f"{this_command()} language remove {arguments([*kept, *names])}" + (then if back else "")


def frameworks_of(names: tuple[str, ...]) -> list[str]:
    """The installed frameworks that require one of `names` and are not among them: `language remove` refuses a
    family while one stays, and a repair that drops one loses what the person asked for."""
    root = directory()
    found = []
    for entry in sorted(root.iterdir()) if root.is_dir() else []:
        fragment, fault = parse_fragment(entry / "language.json")
        requires = fragment.get("requires") if fault is None and isinstance(fragment, dict) else None
        if isinstance(requires, dict) and set(requires) & set(names) and entry.name not in names:
            found.append(entry.name)
    return found


def families_of(frameworks: list[str]) -> set[str]:
    """The families `frameworks` require, read from their `language.json`."""
    found: set[str] = set()
    for name in frameworks:
        fragment, _ = parse_fragment(directory() / name / "language.json")
        found |= set(fragment["requires"]) if isinstance(fragment, dict) else set()
    return found


def released(name: str) -> str:
    """The name the installed directory `name`'s `language.json` gives — what `language install` takes — or `name`
    where it gives none that could be one."""
    fragment, fault = parse_fragment(directory() / name / "language.json")
    given = fragment.get("name") if fault is None and isinstance(fragment, dict) else None
    return given if isinstance(given, str) and name_fault("language", given) is None else name


def arguments(names: list[str]) -> str:
    """Names as a verb's arguments, shell-quoted, after `--` where one would read as a flag."""
    return shlex.join(["--", *names] if any(name.startswith("-") for name in names) else names)


def reinstall(*names: str, back: bool = True) -> str:
    """`reinstalling`, as the ending of a refusal's line."""
    command = reinstalling(*names, back=back)
    return f"; {command}" if command else ""


def parse_manifest(path: Path, label: str, missing: str) -> tuple[Any, str | None]:
    """A package's manifest parsed, or the fault that says why it cannot be. Only a regular file is opened: a
    FIFO would block the verb on a read, and a directory or a device is no manifest. Whatever else the read or
    the parse can raise is the package's fault in a line, never a traceback at import of the catalog.

    `label` is the file's name as a message says it, and `missing` the fault for its absence, because the two
    kinds of package differ in exactly that: an extension lacking `extension.json` is not an extension, and a
    directory lacking `language.json` is not a language."""
    try:
        if not path.exists():
            return None, missing
        if not path.is_file():
            return None, f"{label} is not a regular file"
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return None, f"{label} is not valid UTF-8"
    except ValueError as error:  # a JSON error, or an integer past the interpreter's digit limit
        return None, f"{label} is not valid JSON: {error}"
    except RecursionError:
        return None, f"{label} is nested too deeply to read"
    except OSError as error:
        return None, f"{label} cannot be read: {type(error).__name__}"
    return (parsed, None) if isinstance(parsed, dict) else (None, f"{label} is not a JSON object")


def parse_fragment(path: Path) -> tuple[Any, str | None]:
    """`language.json` parsed, or the fault that says why it cannot be."""
    return parse_manifest(path, "language.json", NO_FRAGMENT)


def fault_in(name: str, root: Path, core: str, installed: bool = False) -> tuple[dict[str, Any] | None, str | None]:
    """The fragment of `root/language.json` a keel speaking schema `core` can load, or why it is refused. `installed`:
    the package is in the package directory, so the line ends on the command that fixes it there."""
    fragment, fault = parse_fragment(root / "language.json")
    if fault is None and (fault := shape_fault(name, fragment)) is None:
        try:
            fault = schema_fault(name, fragment, core, installed)
        except ValueError as error:  # a range that does not parse is a malformed language.json
            fault = str(error)
        else:
            return (under_current_names(fragment), None) if fault is None else (None, fault)
    return None, fault + (reinstall(name, back=fault != NO_FRAGMENT) if installed else "")



def fragment_fault(name: str, fragment: dict[str, Any], core: str) -> str | None:
    """Why a parsed fragment is refused, or None where this keel can load it."""
    try:
        return shape_fault(name, fragment) or schema_fault(name, fragment, core)
    except ValueError as error:
        return str(error)


def shape_fault(name: str, fragment: dict[str, Any]) -> str | None:
    """Why a fragment is not one any the keel could read, or None."""
    lacking = [key for key, _, _ in REQUIRED if key not in fragment]
    if lacking:
        return f"language.json lacks {', '.join(lacking)}"
    for key, kind, article in REQUIRED:
        value = fragment[key]
        if not isinstance(value, kind) or isinstance(value, bool):
            return f"language.json's {key} is not {'non-empty ' if kind is dict else ''}{article}"
    if fragment["name"] != name:
        return f"language.json names {fragment['name']}, and its directory is {name}"
    if (fault := family_fault(fragment)) is not None:
        return fault
    backends = [("backend", key) for key in fragment["backends"]]
    named_here = [("language", name), ("family", fragment["family"]), *backends]
    for role, value in named_here:
        if (fault := name_fault(role, value)) is not None:
            return fault
    for key, row in fragment["backends"].items():
        shape = row_shape_fault(key, row)
        if shape is not None:
            return shape
    return None


def schema_fault(name: str, fragment: dict[str, Any], core: str, installed: bool = False) -> str | None:
    """Why this keel cannot load the fragment's `core` range, ending on the command that moves the one behind: the keel
    (`upgrade`), or an installed package built for an older keel (`language upgrade`). `ValueError` where the range
    does not parse."""
    if satisfies(core, fragment["core"]):
        return None
    said = f"needs core schema {fragment['core']}, and this core speaks {core}"
    if below(core, fragment["core"]) or installed:
        command = schema_command(name, fragment, core)
        return f"{said}: {command}" if command else said
    return f"{said}: it needs a version of {name} built for schema {core.split('.')[0]}"


def schema_command(name: str, fragment: dict[str, Any], core: str) -> str:
    """The command that moves whichever of the keel and an installed package is behind, or '' where neither is — and ''
    for the package under `SLIPWAI_LANGUAGES`, whose upgrade would replace the person's own directory."""
    if satisfies(core, fragment["core"]):
        return ""
    if below(core, fragment["core"]):
        return f"{this_command()} upgrade"
    return "" if os.environ.get(VARIABLE) else f"{this_command()} language upgrade {name}"


def read(root: Path, core: str, installed: bool = False) -> tuple[list[Package], list[str]]:
    """Phase 1: each package in `root` a keel speaking schema `core` can load, and a line for each it cannot —
    ending on its fix where `root` is the package directory being loaded (`installed`)."""
    packages: list[Package] = []
    refusals: list[str] = []
    if not root.is_dir():
        return packages, refusals
    try:
        entries = sorted(root.iterdir())
    except OSError:  # a directory the keel may not list holds no language it can name
        return packages, refusals
    for entry in entries:
        try:
            # An extension and a target live in the same directory and are read by their own modules.
            # Skipped rather than refused: "has no language.json" about a thing that never claimed to be one
            # is a line that sends its reader to fix something that is not broken.
            if entry.name.startswith(".") or not entry.is_dir():
                continue
            if any((entry / manifest).is_file() for manifest in OTHER_MANIFESTS):
                continue
        except OSError:
            continue
        fragment, fault = fault_in(entry.name, entry, core, installed)
        if fragment is None:
            refusals.append(refusal(entry.name, entry, fault or NO_FRAGMENT))
        else:
            packages.append(Package(entry.name, entry, fragment))
    return packages, refusals


def forget(module: str) -> None:
    """Take a module and its submodules out of `sys.modules`."""
    for loaded in [loaded for loaded in sys.modules if loaded == module or loaded.startswith(f"{module}.")]:
        del sys.modules[loaded]


def import_package(package: Package) -> Language:
    """Phase 2: import the package's Python from its own directory, or raise `Refused` with the one line."""
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
        return declared_language(package, imported, module, refused)
    except Refused:
        forget(module)
        raise
    except BaseException as error:  # a module `__getattr__` or a property of the `Language` runs package code too
        forget(module)
        raise refused(f"{module} failed to import: {blame(error)}") from None


def declared_language(package: Package, imported: Any, module: str, refused: Any) -> Language:
    """The imported module's `LANGUAGE`, checked against the fragment, or `Refused`."""
    try:
        language = imported.LANGUAGE
    except AttributeError:
        raise refused(f"{module} has no LANGUAGE") from None
    if not isinstance(language, Language):
        raise refused(f"{module}'s LANGUAGE is a {type(language).__name__}, not a Language")
    declared = sorted(package.fragment["backends"])
    found = sorted(backend.key for backend in language.backends)
    if declared != found:
        raise refused(f"language.json declares {', '.join(declared)} and its LANGUAGE declares {', '.join(found)}")
    named_here = [f.name for f in (language.families if isinstance(language.families, tuple | list) else ())
                  if isinstance(f, Family) and isinstance(f.name, str)]
    if extra := [name for name in named_here if name != package.fragment["family"]]:  # A78: only the family it names
        raise refused(f"its LANGUAGE declares family {', '.join(extra)}, which its language.json does not name")
    return language
