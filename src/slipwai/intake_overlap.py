"""Requirement ids a handed-over document names that this project's specifications already hold.

A document for a further feature is often cut from a larger one, and the larger one is what the first
specification was written from. The hand-over's agent is told to mention overlap; the board, at capture, says
the one thing it can say without judging: which ids appear in both. **A match on the ids and nothing else.**
`FR-003` in a document and `FR-003` in `specs/001-thing/spec.md` may be the same requirement or two features
that both started counting at one, and the board does not read either to find out. So this warns and never
refuses: the person captures or does not, and the assessment reads both.

**What a specification holds** is an id it lists — the head of a list item, a table row or a heading, as Spec
Kit writes `- **FR-001**: …` — and not one a sentence mentions, so a specification that says UTF-8 holds no
requirement called that. The shape is the one the records are checked for (`scripts/check-decisions.py` names
`FR-`, `SC-` and `NFR-`), with the letters left open: whatever this project's specifications list is what is
looked for. **What a document names** is that same token anywhere in its text.

A document is a stranger's and is only ever searched: no part of it becomes a pattern, a path or a line the
board acts on. No ids, no specification, or a file that does not read: no warning, and no error.
"""
from __future__ import annotations

import re
from pathlib import Path

from .passage import specifications

ID = r"[A-Z][A-Z0-9]{0,7}-\d{1,5}"
#: An id a specification lists: at the head of a list item, a table row or a heading, bold or not.
HELD = re.compile(rf"(?m)^[ \t]*(?:(?:[-*+]|\d+[.)])[ \t]+|\|[ \t]*|#{{1,6}}[ \t]+)\**({ID})\**(?![\w-])")
#: The same token anywhere in a document, whole: not `FR-0011`, not `XFR-001`.
NAMED = re.compile(rf"(?<![\w-])({ID})(?![\w-])")


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def held_ids(root: Path) -> dict[str, list[str]]:
    """Each id this project's specifications list, with the specifications that list it."""
    found: dict[str, list[str]] = {}
    for spec in specifications(root):
        where = spec.parent.relative_to(root).as_posix()
        for name in sorted(set(HELD.findall(read(spec)))):
            found.setdefault(name, []).append(where)
    return {name: sorted(places) for name, places in found.items()}


def overlap(root: Path, documents: list[Path]) -> list[dict]:
    """Each id a document names that a specification holds: the id, the documents, the specifications."""
    held = held_ids(root) if documents else {}
    if not held:
        return []
    named: dict[str, set[str]] = {}
    for document in documents:
        for name in set(NAMED.findall(read(document))) & held.keys():
            named.setdefault(name, set()).add(document.name)
    return [{"id": name, "documents": sorted(named[name]), "specifications": held[name]} for name in sorted(named)]


def warning(found: list[dict]) -> str:
    """What the page says beside the capture, or nothing."""
    if not found:
        return ""
    rows = ", ".join(f"{one['id']} ({', '.join(one['documents'])}; in {', '.join(one['specifications'])})"
                     for one in found)
    return (f"What you attached names requirement ids this project's specifications already hold: {rows}. "
            "This is a match on the ids only: the board has not compared what they say, and two features can "
            "number from one. You can still capture; the assessment reads both.")
