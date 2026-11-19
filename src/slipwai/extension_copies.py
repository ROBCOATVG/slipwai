"""An elected extension's files in a project, held against the package installed on this machine.

A project's `scripts/extensions/<key>/` is a copy: written at generation from the package as installed then,
and brought forward by each `slipwai migrate`, whose replay carries the installed package's files as the
factory's side of the merge. So after a migration the copy is the installed package wherever the project left
it alone — and where it still differs, somebody changed it here, or a conflict went this project's way. Either
is the project's to decide, and neither used to be said: one project's CI called a path its copy of `ux-gates`
did not have for a day, and nothing named the copy as the thing that was behind.

This names them, for the catch-up page, and rewrites nothing. A file a project changed is a file it owns.
Whether the installed package is itself behind what is published is `slipwai upgrade --check`'s to say.
"""
from __future__ import annotations

import json
from pathlib import Path

from .assets import this_command
from .extension_directory import MANIFEST, files
from .language_directory import directory
from .layout import layout_of
from .toolkit import EXTENSION_ROOT

#: Where a project records what it elected; a project with no record is one this has nothing to say about.
ELECTED = ".slipwai/extensions.json"
#: How many differing files a line names before it counts the rest: a page is read, not grepped.
NAMED = 5


def elected(root: Path) -> list[str]:
    """The keys this project's record names, or none where it has no record it can read."""
    try:
        recorded = json.loads((root / ELECTED).read_text(encoding="utf-8")).get("extensions")
    except (OSError, ValueError, AttributeError):
        return []
    return [key for key in recorded if isinstance(key, str) and key] if isinstance(recorded, list) else []


def version(root: Path) -> str:
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip() or "no version"
    except (OSError, UnicodeDecodeError):
        return "no version"


def text(path: Path) -> str | None:
    """A file as the generator would write it, or None for one it would have skipped: not there, not text."""
    try:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n")
    except (OSError, UnicodeDecodeError):
        return None


def differing(copy: Path, package: Path) -> list[str]:
    """Each file of the installed package this project's copy lacks or holds differently. A file only the
    project has is its own, and a file the generator cannot write as text was never copied to compare."""
    found: list[str] = []
    for relative in files(package):
        installed = text(package / relative)
        if installed is not None and text(copy / relative) != installed:
            found.append(relative.as_posix())
    return sorted(found)  # as text: `files` orders paths, which Windows compares without case


def copies(root: Path, document: dict | None, packages: Path | None = None) -> list[str]:
    """The catch-up page's section naming each elected extension whose copy here is not the installed
    package; no lines at all where every copy is, or nothing is elected."""
    try:
        return section(root, document, directory() if packages is None else packages)
    except (OSError, ValueError, KeyError, TypeError):  # the merge is made: a page short a section, never a traceback
        return []


def section(root: Path, document: dict | None, where: Path) -> list[str]:
    place = layout_of(document).place(EXTENSION_ROOT) if document else EXTENSION_ROOT
    rows: list[str] = []
    for key in elected(root):
        copy, package = root / place / key, where / key
        if not (package / MANIFEST).is_file():
            rows.append(f"- `{key}` is elected here and not installed on this machine, so there was nothing to "
                        f"hold `{place}/{key}/` against: `{this_command()} extension install {key}`.")
            continue
        changed = differing(copy, package)
        if not changed:
            continue
        named = ", ".join(f"`{name}`" for name in changed[:NAMED])
        more = f" and {len(changed) - NAMED} more" if len(changed) > NAMED else ""
        rows.append(f"- `{key}` — this project's copy says {version(copy)}, the installed package is "
                    f"{version(package)}; {len(changed)} file(s) differ: {named}{more}. "
                    f"`diff -r {place}/{key} {package}` shows how.")
    if not rows:
        return []
    return [
        "", "## Extensions whose copy here is not the installed package", "",
        f"`{place}/<key>/` is this project's copy of each extension it elected. This migration merged in what "
        "the installed package changed since the last one; what still differs is a change made in this project, "
        "or a conflict resolved its way. Nothing was rewritten: for each, keep the difference on purpose, or "
        "copy the installed file over it and run `make agents` and `make verify`. Whether the installed package "
        f"is itself behind what is published is another question: `{this_command()} upgrade --check`.",
        "", *rows,
    ]
