"""What a project is given of an extension: what runs or is read there, and not the package's repository.

A package is a repository as well as a tool. It holds the workflows that verify it, the tests that prove it, the
changelog of its releases and the ignore file of its own checkout — and until #119 every one of those was copied
into every project under `scripts/extensions/<key>/`, because `extension_directory.files` is everything but the
manifest and that list was the copy. Nothing in a project runs a package's `tests/`; a workflow outside a
project's own `.github/` is run by nobody; and an agent reading the tree took all of it for the project's.

**Two lists, and a manifest only adds.** `WITHHELD` is the conventional repository-only paths, held back for
every package with no line in any manifest — so the packages already published shrink in a project without a
release, and an older keel still loads them. `withhold` in `extension.json` adds a package's own: a folder of
fixtures, a maintainer's notes. There is deliberately no way to *take back* a conventional path. A project's
copy is then the same shape whichever package it came from, and a reader never has to open a manifest to know
whether `tests/` is the project's.

**What runs is always given.** A script the manifest declares at a hook or a guard is given wherever it sits, and
so is every module of the package it imports, followed through — neither list can take away something a point
runs. The following is by reading the `import` statements: a module loaded by a computed name, or a file opened
as data, is not seen, and belongs outside the conventional paths.

**`README.md`, a licence and a notice are given.** The first is what a person or an agent in the project reads to
learn what the folder is. The others travel with the code they license: a project holds a copy of that code, and
a copy without its terms is one the project may not be entitled to keep. `CHANGELOG.md` is not: `VERSION` says
which release the copy is, and what earlier releases changed is the repository's history.

**The archive a release publishes is untouched.** This is about what is copied into a project; what is packed,
installed and checksummed is still the whole package.
"""
from __future__ import annotations

import ast
import posixpath
from pathlib import Path
from typing import Any

from .extension_directory import files
from .extension_shape import withheld as named
from .guards import declared as guards_declared
from .hooks import declared

#: The conventional ones, relative to the package root: a trailing `/` is a folder and everything in it. Only at
#: the root — a `tests/` inside a skill the package ships is that skill's, and may be something a tool there runs.
WITHHELD = (".github/", "changelog.d/", "tests/", "CHANGELOG.md", ".gitignore", ".gitattributes")
#: Held back at any depth: what an interpreter left behind in the publisher's checkout.
ANYWHERE = "__pycache__"


def repository_only(relative: str, more: tuple[str, ...] = ()) -> bool:
    """Whether one path of a package is on either list, before what a point runs is taken back off it."""
    if ANYWHERE in relative.split("/"):
        return True
    return any(relative.startswith(rule) if rule.endswith("/") else relative == rule for rule in (*WITHHELD, *more))


def run(manifest: dict[str, Any]) -> set[str]:
    """Every script the manifest declares at a hook or a guard, the two default declarations among them."""
    found = (*declared(manifest).values(), *guards_declared(manifest).values())
    return {posixpath.normpath(str(body["run"]).replace("\\", "/")) for body in found}


def modules(text: str) -> set[str]:
    """Each dotted name a script imports, and each name it takes from one — which may be a module too."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found |= {node.module, *(f"{node.module}.{alias.name}" for alias in node.names)}
    return found


def imported(root: Path, scripts: set[str], shipped: set[str]) -> set[str]:
    """Every file of the package those scripts import, followed through, looked for beside the importing file
    and at the package root: the two places an extension's script puts on its path."""
    found: set[str] = set()
    waiting = sorted(scripts)
    while waiting:
        script = waiting.pop()
        try:
            names = modules((root / script).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        for name in sorted(names):
            parts = name.split(".")
            # `a.b.c` is `a/__init__.py`, `a/b/__init__.py` and `a/b/c.py`, or `c` as a package of its own.
            stems = ["/".join(parts[:count]) for count in range(1, len(parts) + 1)]
            wanted = [f"{stem}/__init__.py" for stem in stems] + [f"{stems[-1]}.py"]
            for base in ("", posixpath.dirname(script)):
                for candidate in wanted:
                    path = posixpath.normpath(posixpath.join(base, candidate))
                    if path in shipped and path not in found and path not in scripts:
                        found.add(path)
                        waiting.append(path)
    return found


def split(root: Path, manifest: dict[str, Any]) -> tuple[list[Path], list[Path]]:
    """The package's files as what a project is given and what it is not, each in `files`' own order."""
    try:
        more = named(manifest)
    except ValueError:  # a manifest the loader refuses is not offered at all; here it adds nothing
        more = ()
    everything = files(root)
    shipped = {path.as_posix() for path in everything}
    try:
        scripts = run(manifest) & shipped
    except (ValueError, KeyError):
        scripts = set()
    runs = scripts | imported(root, scripts, shipped)
    kept: list[Path] = []
    back: list[Path] = []
    for path in everything:
        name = path.as_posix()
        (back if repository_only(name, more) and name not in runs else kept).append(path)
    return kept, back


def given(root: Path, manifest: dict[str, Any]) -> list[Path]:
    """The files of the package a project's `scripts/extensions/<key>/` holds, relative to the package root."""
    return split(root, manifest)[0]


def held_back(root: Path, manifest: dict[str, Any]) -> list[Path]:
    """The files of the package a project is not given: its repository's own."""
    return split(root, manifest)[1]
