"""A fragment's names, family keys and backend rows, held to the shape the merge reads.

Leaf checks `language_directory`'s phase 1 runs over every `language.json` before anything is merged or imported:
what a name may be, what a family or a framework must declare, and what a backend row's keys must hold. Each says
why in the words a refusal line carries, or None (`contracts/language-package.md`).
"""
from __future__ import annotations

import re
from typing import Any

from .versions import parse_range

SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")


def name_fault(kind: str, value: str) -> str | None:
    """Why `value` cannot be a language, backend, family or framework name, or None."""
    if SLUG.fullmatch(value):
        return None
    return f"{kind} {value!r} is not a lower-case name (letters, digits and single dashes, starting with a letter)"


def strings(value: Any) -> bool:
    """Whether `value` is a list of strings."""
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def repeated(names: list[str]) -> str | None:
    """The first name a list gives more than once, or None."""
    return next((name for index, name in enumerate(names) if name in names[:index]), None)


def row_shape_fault(key: str, row: Any) -> str | None:
    """Why a backend row is not shaped the way the merge reads it, or None. The merge subscripts `label` and
    `targets`, iterates `options` and `defaults`, and copies `framework`; each is held to its type here."""
    if not isinstance(row, dict):
        return f"backend {key} is not an object"
    for required in ("label", "targets"):
        if required not in row:
            return f"backend {key} lacks {required}"
    for text in ("label", "framework"):
        if text in row and not isinstance(row[text], str):
            return f"backend {key}'s {text} is not a string"
    if "framework" in row and (fault := name_fault("framework", row["framework"])) is not None:
        return fault
    if not strings(row["targets"]):
        return f"backend {key}'s targets is not a list of strings"
    if (twice := repeated(row["targets"])) is not None:
        return f"backend {key}'s targets lists {twice} more than once"
    options = row.get("options", {})
    if not isinstance(options, dict):
        return f"backend {key}'s options is not an object"
    for axis, names in options.items():
        if not strings(names):
            return f"backend {key}'s {axis} options is not a list of strings"
        if (twice := repeated(names)) is not None:
            return f"backend {key}'s {axis} options lists {twice} more than once"
    defaults = row.get("defaults", {})
    if not isinstance(defaults, dict):
        return f"backend {key}'s defaults is not an object"
    for axis, name in defaults.items():
        if not isinstance(name, str):
            return f"backend {key}'s defaults: {axis} is not a string"
    return None


def family_fault(fragment: dict[str, Any]) -> str | None:
    """Why a fragment's family keys are refused, or None: `backends` may be empty only for a family that names its
    `default_framework` or ships a frontend — a package of browser apps alone — and a framework's `requires` names
    exactly its family with a range."""
    family, backends = fragment["family"], fragment["backends"]
    if "default_framework" in fragment:
        if not isinstance(fragment["default_framework"], str):
            return "language.json's default_framework is not a string"
        if (fault := name_fault("default_framework", fragment["default_framework"])) is not None:
            return fault
    if "requires" in fragment:
        requires = fragment["requires"]
        if "default_framework" in fragment:
            return "language.json's default_framework is a family's, and a package that requires its family names none"
        if not isinstance(requires, dict) or list(requires) != [family]:
            return f"language.json's requires must name exactly its family, {family}"
        if not isinstance(requires[family], str):
            return f"language.json's requires: {family} is not a string"
        try:
            parse_range(requires[family], "requires")
        except ValueError as error:
            return str(error)
        if not backends:
            return "language.json's backends is empty, and a package that requires its family adds a backend"
        for key, row in backends.items():
            if isinstance(row, dict) and "framework" not in row:
                return (
                    f"backend {key} has no framework, and a package that requires its family names one on each "
                    "backend"
                )
    elif not backends and "default_framework" not in fragment and not fragment.get("frontends"):
        return ("language.json's backends is empty, and a family with no backend of its own names its "
                "default_framework or ships a frontend")
    return None


#: What a frontend entry's text fields say, and where: `label` is the line `slipwai list` and the interview
#: offer it by, `stack` the words a generated README names the browser app's stack in, `gate` what its native
#: gate runs, as `docs/delivery.md` lists it beside the services'.
FRONTEND_TEXT = ("label", "stack", "gate")


def frontend_shape_fault(name: str, entry: Any) -> str | None:
    """Why one entry of a fragment's `frontends` block is not shaped the way the keel reads it, or None.

    The block is data rather than Python because two readers need it and only one imports the package: the
    keel, writing a browser app, and the pruner inside a generated project, taking a feature's files and
    dependencies back out (`project/pruner.py`). Each feature names the directory its files are copied from,
    the paths in a browser app it owns, and the npm dependencies it adds (`docs/frontend-protocol.md`).
    """
    if (fault := name_fault("frontend", name)) is not None:
        return fault
    if not isinstance(entry, dict):
        return f"frontend {name} is not an object"
    for text in FRONTEND_TEXT:
        if not isinstance(entry.get(text), str) or not entry[text].strip():
            return f"frontend {name} lacks {text}, a sentence"
    if not strings(entry.get("capabilities")):
        return f"frontend {name}'s capabilities is not a list of strings"
    if "lock-name" in entry and (not isinstance(entry["lock-name"], str)
                                 or name_fault("lock-name", entry["lock-name"]) is not None):
        return f"frontend {name}'s lock-name is not a lower-case name"
    if not strings(entry.get("marked", [])):
        return f"frontend {name}'s marked is not a list of paths"
    design = entry.get("design", {})
    if not isinstance(design, dict) or not all(
            isinstance(value, str) or (key == "imports" and strings(value)) for key, value in design.items()):
        return f"frontend {name}'s design is not an object of paths, with imports a list of lines"
    features = entry.get("features", {})
    if not isinstance(features, dict):
        return f"frontend {name}'s features is not an object"
    for feature, row in features.items():
        if not isinstance(row, dict):
            return f"frontend {name}'s feature {feature} is not an object"
        if not isinstance(row.get("files"), str):
            return f"frontend {name}'s feature {feature} names no files directory"
        if not strings(row.get("owned", [])):
            return f"frontend {name}'s feature {feature}'s owned is not a list of strings"
        dependencies = row.get("dependencies", {})
        if not isinstance(dependencies, dict) or not all(
                isinstance(key, str) and isinstance(value, str) for key, value in dependencies.items()):
            return f"frontend {name}'s feature {feature}'s dependencies is not an object of exact versions"
        if "where" in row and not isinstance(row["where"], str):
            return f"frontend {name}'s feature {feature}'s where is not a string"
    return None
