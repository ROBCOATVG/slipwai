"""Cutting a package's release: the entry assembled, the number written, the fragments gone.

A package carries its own `VERSION`, `CHANGELOG.md` and `changelog.d/`, and the conformance suite holds
the three together: a released `VERSION` must have an entry under that number and no fragments left over.
That rule exists because a version with no entry is a number nobody can find out the meaning of, and a
fragment left behind is a change that will be told to somebody twice.

Until now nothing gave a publisher a way to satisfy it. `VERSION` was a file to edit by hand, and editing
it by hand is exactly what the suite catches — which is how the first six packages were released and how
their first CI run failed. The keel has had `make release` since 8.1 doing precisely this for itself; this
is the same thing, for a package, through a verb.

**Cutting and building are different actions, and stay apart.** This rewrites the working tree: a person
runs it, reads the entry, commits and tags. `package release` builds a tarball from whatever the tree says
and is what CI runs from the tag — and a CI job that rewrote the changelog would be rewriting the commit
the tag already points at.
"""
from __future__ import annotations

from pathlib import Path

from .changelog import GUIDE, LEVELS, entry, fragments, implied, level
from .errors import GenerationError
from .language_release import read_package
from .versions import base, is_snapshot

CHANGELOG = "CHANGELOG.md"
#: Written above the first entry when a package has no changelog at all. Short on purpose: a package's
#: changelog is read by whoever installed it, and a preamble is not what they came for.
HEADER = """# Changelog

What changed in each release of this package.
"""


def released(text: str) -> list[str]:
    """Every version `CHANGELOG.md` already has an entry for."""
    return [line[3:].split(" — ")[0].strip() for line in text.splitlines() if line.startswith("## ")]


def faults(root: Path, found: list, release: str | None) -> list[str]:
    """Everything that would make this cut wrong, said at once rather than one per run."""
    said: list[str] = []
    if not found:
        said.append(f"changelog.d/ holds no fragment but {GUIDE}, so there is nothing to release. "
                    f"Write one: its first line is {', '.join(LEVELS)}, and the rest is what changed")
    for path, claim, body in found:
        if claim is None:
            said.append(f"{path.name}'s first line is not one of {', '.join(LEVELS)}")
        if not body.strip():
            said.append(f"{path.name} says nothing under its level")
    if found and release is None:
        said.append("no fragment claims a level, so there is no number these changes imply")
    return said


def cut(root: Path, release: str | None = None) -> tuple[str, str, int]:
    """Assemble the entry, write `VERSION`, delete the fragments. (version, level, fragments used).

    Nothing is written until everything can be: a cut that got as far as `VERSION` and then met a fragment
    it could not read would leave a number with no entry, which is the state this exists to prevent.
    """
    source = read_package(root)
    path = root / CHANGELOG
    text = path.read_text(encoding="utf-8") if path.is_file() else HEADER
    found = fragments(root)
    last = next(iter(released(text)), None)
    opening = source.version
    if is_snapshot(opening):
        opening = base(opening) or opening
    wanted = release or (implied(last, found) if last and found else None) or opening
    for fault in faults(root, found, wanted if found else None):
        raise GenerationError(fault)
    if wanted in released(text):
        raise GenerationError(f"{CHANGELOG} already has an entry for {wanted}. A release is cut once: "
                              f"name the next one with `--release`, or let the fragments imply it")
    at = text.index("\n## ") + 1 if "\n## " in text else len(text.rstrip()) + 2
    # The first release carries no level. It was bumped from nothing, and "MINOR relative to nothing"
    # means nothing — which is D38, and what the conformance suite holds every package to.
    whole = (text[:at].rstrip() + "\n\n" + entry(wanted, found, first=not released(text))
             + text[at:].lstrip("\n"))
    path.write_text(whole, encoding="utf-8")
    (root / "VERSION").write_text(f"{wanted}\n", encoding="utf-8")
    for fragment, _claim, _body in found:
        fragment.unlink()
    return wanted, "" if not released(text) else str(level(found) or ""), len(found)
