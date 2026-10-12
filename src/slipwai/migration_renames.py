"""Apply the committed rename table to both old sides before a crossing's three-way merge.

No version 1 generator lives here. Paths and JSON keys move by the table; a text substitution is made only
in the files that declare the thing being renamed — a make target in a Makefile, a command under
`commands/`, a skill under `skills/` — because a row carries a bare word or a path and the same characters
are ordinary prose and ordinary code everywhere else in somebody's repository. A reference anywhere else is
left as written and read off the catch-up page, which lists every rename once (plan section 6, change 3).
A collision is a refusal, never an overwritten edit.
"""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

from .assets import ROOT, inside
from .errors import GenerationError

KINDS = {"file", "command", "skill", "make-target", "setting", "field"}
#: What a make target is declared in. `make` reads these names and no others.
MAKEFILES = {"Makefile", "makefile", "GNUmakefile"}


def table(root: Path = ROOT) -> list[dict[str, str]]:
    document = json.loads((root / "docs/rename.json").read_text(encoding="utf-8"))
    if document.get("v") != 1 or not isinstance(document.get("renames"), list):
        raise GenerationError("the rename table cannot be read; restore docs/rename.json with `slipwai upgrade`")
    seen: set[tuple[str, str]] = set()
    rows = []
    for row in document["renames"]:
        if not isinstance(row, dict) or row.get("kind") not in KINDS or not all(
            isinstance(row.get(key), str) and row[key] for key in ("from", "to")
        ):
            raise GenerationError("the rename table holds an incomplete row; restore it with `slipwai upgrade`")
        identity = (row["kind"], row["from"])
        if identity in seen:
            raise GenerationError(f"the rename table moves {identity} twice; restore it with `slipwai upgrade`")
        seen.add(identity)
        rows.append(row)
    return rows


def contained(value: str, remedy: str) -> str:
    """One path with nothing in it that could leave the project, or a refusal ending in `remedy`."""
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or ".." in path.parts or "\\" in value
            or any(part.lower() == ".git" for part in path.parts)):
        raise GenerationError(f"{value!r} reaches outside the project; {remedy}")
    return path.as_posix()


def relative(value: str) -> str:
    """A rename *table row*'s path as a project holds it.

    The table is written against the toolkit tree and its files land at their path relative to
    `assets/toolkit/`, so that prefix comes off here. Never applied to a project's own paths: a project
    with a real `assets/toolkit/house-rules.md` of its own had it relocated to `house-rules.md`.
    """
    return contained(value.removeprefix("assets/toolkit/"), "restore the table with `slipwai upgrade`")


def declares(kind: str, path: str) -> bool:
    """Whether this project file is one that declares things of this kind, and may be rewritten for it."""
    parts = PurePosixPath(path).parts
    if kind == "make-target":
        return parts[-1] in MAKEFILES or path.endswith(".mk")
    return ("commands" if kind == "command" else "skills") in parts


def keys(value: object, old: str, new: str) -> object:
    """A JSON document with a field renamed, retaining values and insertion order."""
    if isinstance(value, list):
        return [keys(item, old, new) for item in value]
    if not isinstance(value, dict):
        return value
    if old in value and new in value:
        raise GenerationError(f"both {old!r} and {new!r} are recorded; "
                              "keep the intended value before `slipwai migrate`")
    return {new if key == old else key: keys(item, old, new) for key, item in value.items()}


def moved(path: str, rows: list[dict[str, str]]) -> str:
    for row in rows:
        if row["kind"] not in {"file", "command", "skill"}:
            continue
        old, new = relative(row["from"]), relative(row["to"])
        if path == old or path.startswith(old + "/"):
            path = new + path[len(old):]
    return path


def renamed(files: dict[str, bytes], rows: list[dict[str, str]]) -> dict[str, bytes]:
    """A new tree, with every project edit retained or its collision named before anything writes."""
    answer: dict[str, bytes] = {}
    for path, body in files.items():
        destination = moved(contained(path, "remove or rename it before `slipwai migrate`"), rows)
        if destination in answer:
            raise GenerationError(f"renames collide at {destination}; resolve the duplicate before `slipwai migrate`")
        answer[destination] = body
    for row in rows:
        kind, old, new = row["kind"], row["from"], row["to"]
        if kind in {"field", "setting"}:
            destination = moved(relative(row.get("in", "project.json")), rows)
            if destination not in answer:
                continue
            try:
                document = json.loads(answer[destination])
            except (ValueError, UnicodeDecodeError) as error:
                raise GenerationError(f"{destination} cannot be read as JSON; "
                                      "repair it before `slipwai migrate`") from error
            changed = keys(document, old, new)
            if changed != document:
                answer[destination] = (json.dumps(changed, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        elif kind in {"make-target", "command", "skill"}:
            pattern = re.compile(rf"(?<![\w-]){re.escape(old)}(?![\w-])")
            for path, body in list(answer.items()):
                if not declares(kind, path):
                    continue
                try:
                    text = body.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                answer[path] = pattern.sub(new.replace("\\", "\\\\"), text).encode("utf-8")
    return answer


def files_of(root: Path) -> dict[str, bytes]:
    """The checked tree, without Git itself or disposable interpreter/build state."""
    answer = {}
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        disposable = {".git", "__pycache__", "node_modules", ".delivery-tools"}
        if any(part in disposable for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            try:
                contained = inside(root, name)
            except ValueError as error:
                raise GenerationError(f"{name} leaves the project; "
                                      "remove its symlink before `slipwai migrate`") from error
            answer[name] = contained.read_bytes()
    return answer
