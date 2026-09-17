"""The catch-up notes a migration leaves behind: what the versions it crossed ask of a project already built.

Every version's entry carries a **Catch-up** paragraph where there is anything to say — in `CHANGELOG.md`
once the version is out, in `changelog.d/` while it is being written — put there by the person who made the
change in the commit that made it, because that is the only moment anybody knows what it will cost somebody
else's repository. `AGENTS.md` has required it for a long time. Nothing read it.

Nothing could: the changelog is the factory's file and a generated project has no copy of it. Both supported
installs put a `slipwai` on the `PATH` with no factory checkout behind it (`docs/executable.md`), and the
frozen executable unpacks its data to a temporary directory that exists only while the process runs — so an
agent working in a project cannot open the notes for the versions that project just took, however plainly
they are written.

So `migrate` writes them into the project before it returns — whether the merge committed or stopped at
conflicts — and `/catch-up` reads them there. That is the whole of this module: select the entries between
two versions, take each one's claim and its catch-up paragraph verbatim, and render them as a page. Nothing
here summarises, and nothing infers — an entry whose author wrote no catch-up paragraph is reported as
having written none, because printing it as "asked nothing" would be a promise this cannot make.

And the page is always written once the merge changed anything. When the versions crossed cannot be told —
a project made before 1.6.0 recorded no version, both sides are snapshots of one release, the changelog has
no entry between them — the file says which of those it is and lists what it can, because an absent file
reads as "nothing owed" and a project that crossed twenty versions with no record of it is owed the most.

The range needs no searching. `migrate` reads `updatedWith` from `project.json` before it merges and knows
the version it is merging, so the two bounds are already in its hands — where the manifest has them. One
written by a factory before 1.6.0 has no `generator` at all, and nothing in the project says which of the
versions before it did the scaffolding; every entry above the first is listed then, with that said first.
"""
from __future__ import annotations

import re

from . import changelog
from .assets import ROOT, VERSION
from .versions import base

CHANGELOG = ROOT / "CHANGELOG.md"
# `## 1.8.0 — MINOR`, the heading every entry carries; `## 1.0.0` for the first, which nothing preceded.
ENTRY = re.compile(r"(?m)^## (\d+\.\d+\.\d+)(?: — (MAJOR|MINOR|PATCH))?$")
# An entry opens with its claim in bold — one sentence saying what changed for whoever runs this.
HEADLINE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
# The paragraph written for a repository that already exists, up to the blank line that ends it.
OWED = re.compile(r"(?m)^\*\*Catch-up[^*]*\*\*[ \t]*(.*?)(?=\n\n|\Z)", re.DOTALL)


def parts(version: str) -> tuple[int, ...]:
    """A version as the numbers of the release it is or is heading for, so 1.10.0 sorts above 1.9.0 rather
    than below it — and a snapshot counts as its release.

    `1.13.0.dev4` was made from the entry headed `1.13.0` as it stood that day, so a project it generated
    has *had* what that entry describes so far, and one migrating to it takes that entry. What lands between
    two snapshots of the same number is not told apart: snapshots are for trying what is coming, and the
    entry is finished when the release is.
    """
    release = base(version)
    return () if release is None else tuple(int(piece) for piece in release.split("."))


def collapse(text: str) -> str:
    """A paragraph as one line: the changelog wraps its prose, and this is read as a list of obligations."""
    return " ".join(text.split())


# What each entry is read as: its number, its level, its claim, and the paragraph it wrote for a repository that
# already existed — None where its author wrote none.
Entry = tuple[str, str | None, str, str | None]
# The first entry, which nothing preceded: the lower bound when a manifest recorded no version at all.
FIRST = "1.0.0"


def in_flight() -> list[Entry]:
    """The entry for the release being written, read off `changelog.d/` — empty where there is none.

    A project migrating onto `1.15.0.dev7` is owed whatever the fragments already ask of it, and until the
    release is cut they are the only place that is written. Every fragment contributes: its claim and its
    catch-up paragraph are read the same way an assembled entry's are, and joined, because the entry is the
    fragments and a project owes all of it rather than the first of it.
    """
    release = base(VERSION)
    found = changelog.fragments()
    if release is None or not found or any(number == release for number, *_rest in released()):
        return []
    claims = [HEADLINE.search(body) for _path, _level, body in found]
    notes = [OWED.search(body) for _path, _level, body in found]
    headlines = [collapse(claim.group(1)) for claim in claims if claim]
    owed = [collapse(note.group(1)) for note in notes if note]
    return [(
        release,
        changelog.level(found),
        " ".join(headlines) or "(the fragments for this version state no headline)",
        " ".join(owed) or None,
    )]


def entries() -> list[Entry]:
    """Every entry, newest first: the one being written, then every one released."""
    return in_flight() + released()


def released() -> list[Entry]:
    """Every entry in the changelog, newest first — all of them out, each one a version somebody has."""
    if not CHANGELOG.is_file():
        return []
    text = CHANGELOG.read_text()
    found = list(ENTRY.finditer(text))
    read = []
    for index, match in enumerate(found):
        end = found[index + 1].start() if index + 1 < len(found) else len(text)
        body = text[match.end() : end].strip()
        headline = HEADLINE.search(body)
        note = OWED.search(body)
        read.append((
            match.group(1),
            match.group(2),
            collapse(headline.group(1)) if headline else "(this entry states no headline)",
            collapse(note.group(1)) if note else None,
        ))
    return read


def crossed(after: str | None, upto: str = VERSION) -> list[Entry]:
    """Every recorded version above `after` and at or below `upto`, newest first.

    Half-open at the bottom: a project recording `updatedWith` 1.6.2 has *had* 1.6.2, so what it has just
    taken is everything above it. A bound that cannot be read as a version gives nothing — `notes` says
    why, and lists what it can instead.
    """
    if not after or not parts(after) or not parts(upto):
        return []
    return [entry for entry in entries() if parts(after) < parts(entry[0]) <= parts(upto)]


def shared(version: str) -> list[Entry]:
    """The entry for the release `version` is, or is a snapshot of."""
    return [entry for entry in entries() if parts(entry[0]) == parts(version)]


def unlisted(was: str | None, now: str) -> tuple[str, str, list[Entry]]:
    """Why nothing was crossed, and what to list instead: the reason, the heading for the list, the entries.

    Each reason is one sentence about this project's provenance and one about what the list below it is, so
    the person reading it can judge the list rather than take it. Nothing here is a guess: where the lower
    bound is unknown the list is everything, said to be everything, and never a number picked for them.
    """
    everything = f"Every version above {FIRST}, newest first — read on from the one that made this project"
    if not was:
        return (
            f"`project.json` records no `generator.updatedWith`. Factory versions before 1.6.0 wrote none, so "
            "one of them made this project, and which one is not recorded anywhere in it. Every version since "
            f"{FIRST} is listed below; those at or below the one that made this project are already had and owe "
            "nothing, and the scaffold commit's date (`git log --reverse --author=factory@local`) against the "
            "factory's history says which that is. Where the line cannot be drawn, an entry that asks something "
            "is one to check rather than skip.",
            everything, crossed(FIRST, now),
        )
    if not parts(was):
        return (
            f"`project.json` records `generator.updatedWith` as `{was}`, which is not a version this can read, so "
            f"the lower bound is unknown. Every version since {FIRST} is listed below; those at or below the one "
            "that made this project are already had and owe nothing.",
            everything, crossed(FIRST, now),
        )
    if not parts(now):
        return (
            f"this slipwai's own version reads `{now}`, which is not a version this can read, so nothing can be "
            f"selected. Read the factory's `CHANGELOG.md` from {was} upwards instead.",
            "Nothing listed", [],
        )
    if parts(was) == parts(now):
        release = base(now)
        return (
            f"`{was}` and `{now}` are both {release} — a snapshot of that release, or the release itself — and the "
            "changelog keeps one entry per release, so what changed between the two is not told apart. The "
            f"{release} entry as it stands today is below; the part of it this project already had cannot be "
            "separated from the part it has just taken, so read it as a whole.",
            f"The one entry both versions belong to, {release}", shared(now),
        )
    if parts(was) > parts(now):
        return (
            f"this project recorded `{was}`, which is newer than the slipwai {now} that has just migrated it. What "
            "an older factory asks of a project that had a newer one is nothing this changelog records.",
            "Nothing listed", [],
        )
    if not CHANGELOG.is_file():
        return (
            "this slipwai carries no `CHANGELOG.md`, so nothing could be selected from it. Read the factory's own "
            f"changelog from {was} to {now} instead.",
            "Nothing listed", [],
        )
    return (
        f"this slipwai's `CHANGELOG.md` has no entry between {was} and {now}. Either nothing was recorded, or "
        "the entry for the version being taken has not been written yet.",
        "Nothing listed", [],
    )


def notes(name: str, was: str | None, now: str = VERSION) -> str:
    """The page `migrate` writes into the project.

    Always a page: a file that says why there is nothing to list is opened once and answers the question,
    where an absent file is read as "nothing owed" — which is the one thing this must never say by accident.
    """
    versions = crossed(was, now)
    reason, heading, listed = (
        (None, f"{len(versions)} version(s) taken, newest first", versions) if versions else unlisted(was, now)
    )
    lines = [
        f"# Catch up: {name}, {was or 'an unrecorded version'} to {now}",
        "",
        "`slipwai migrate` wrote this before it returned — whether the merge committed or stopped at conflicts "
        "— from the catch-up note in each version's entry in the factory's own `CHANGELOG.md`, written by "
        "whoever made the change, in the commit that made it. It is what a merge could not do for you.",
        "",
        "Work it with `/catch-up`, which reads this file and runs `make verify` against it. This file is "
        "git-ignored and disposable: delete it when the work is done, and the changelog stays the record.",
    ]
    if reason is not None:
        lines += ["", "## Why the versions crossed could not be listed as such", "", f"Because {reason}"]
    lines += ["", f"## {heading}"]
    if not listed:
        lines += ["", "(nothing)"]
    for number, level, headline, owed in listed:
        lines += [
            "",
            f"### {number}{f' — {level}' if level else ''}",
            "",
            headline,
            "",
            f"**Owes:** {owed}" if owed else
            "**Owes:** nothing recorded for a repository that already existed.",
        ]
    lines += [
        "",
        "## Then",
        "",
        "`make verify`. A gate that is new in one of the versions above fails code that was correct when it "
        "was written; the entry that introduced it says what it now wants instead. Never edit a gate to make "
        "it pass — it came from the factory, the next migration brings it back, and a locally softened copy "
        "is a false green until then.",
        "",
    ]
    return "\n".join(lines)
