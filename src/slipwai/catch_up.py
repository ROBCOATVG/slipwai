"""The catch-up notes a migration leaves behind: what the versions it crossed ask of a project already built.

Every version's entry carries a **Catch-up** paragraph where there is anything to say — in `CHANGELOG.md`
once the version is out, in `changelog.d/` while it is being written — put there by the person who made the
change in the commit that made it, because that is the only moment anybody knows what it will cost somebody
else's repository. `AGENTS.md` has required it for a long time. Nothing read it.

Nothing could: the changelog is the keel's file and a generated project has no copy of it. Both supported
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
# budget: 370 — every page opens with the set-up section and ends naming the archive path it is moved to.
from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from . import changelog
from .assets import ROOT, VERSION
from .catalog import PACKAGES
from .catch_up_page import set_up, stated
from .manifest import answering, apps_from_manifest, loaded_versions, recorded_languages
from .versions import base

CHANGELOG = ROOT / "CHANGELOG.md"
# `## 1.8.0 — MINOR`, the heading every entry carries; `## 1.0.0` for the first, which nothing preceded.
ENTRY = re.compile(r"(?m)^## (\d+\.\d+\.\d+)(?: — (MAJOR|MINOR|PATCH))?$")
# An entry opens with its claim in bold — one sentence saying what changed for whoever runs this.
HEADLINE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
# The one bold run that is never a claim: the marker `OWED` reads the catch-up paragraph by. Without this,
# a fragment whose author left the claim unbolded has `Catch-up:` read as its claim — which printed as
# `- **Catch-up:** ...` in a list whose whole purpose is to name which change is asking.
MARKER = re.compile(r"^Catch-up\b", re.IGNORECASE)
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
    try:
        return () if release is None else tuple(int(piece) for piece in release.split("."))
    except ValueError:  # past Python's digit limit for an integer: not a version anyone wrote, listed whole
        return ()


def collapse(text: str) -> str:
    """A paragraph as one line: the changelog wraps its prose, and this is read as a list of obligations."""
    return " ".join(text.split())


def claim_of(body: str) -> str | None:
    """An entry's or a fragment's claim: its first bold run that is not the catch-up marker, or None."""
    for found in HEADLINE.finditer(body):
        said = collapse(found.group(1))
        if not MARKER.match(said):
            return said
    return None


# What each entry is read as: its number, its level, its claim, and the paragraph it wrote for a repository that
# already existed — None where its author wrote none. Either text may be several lines: a release still in
# flight is a set of fragments, and `in_flight` renders each of them as a line of its own.
Entry = tuple[str, str | None, str, str | None]
# How a fragment that left one half of itself out is named in the list, rather than being left out of it.
NO_CLAIM = "(a fragment that states no headline)"
NO_NOTE = "— its author wrote no catch-up paragraph, so what it costs a repository already built is unrecorded."
# The first entry, which nothing preceded: the lower bound when a manifest recorded no version at all.
FIRST = "1.0.0"


class Moved(NamedTuple):
    """A language package whose installed version is not the one the project recorded: its section of the notes."""

    name: str
    was: str | None  # what `generator.languages` recorded; None where it recorded nothing (1.x, or newly needed)
    now: str
    root: Path


def fragment_notes(found: list[changelog.Fragment]) -> list[tuple[str | None, str | None]]:
    """Each fragment's claim and its catch-up paragraph, **paired**, in the order the fragments are read.

    Paired because they are only useful together. A release in flight is a set of fragments, each written
    by whoever made that one change, and the two halves of a fragment answer different questions: the
    claim says what changed, the catch-up paragraph says what it costs a repository that already exists.
    Read apart and concatenated, forty catch-up paragraphs in a row have nothing saying which change each
    belongs to — which is what a migration onto 2.0.0 printed, and nobody could act on it.
    """
    read: list[tuple[str | None, str | None]] = []
    for _path, _level, body in found:
        note = OWED.search(body)
        read.append((claim_of(body), collapse(note.group(1)) if note else None))
    return read


def claimed(notes: list[tuple[str | None, str | None]]) -> str:
    """What the release being written changes: one line per fragment, in the order they are read."""
    lines = [f"- {claim}" for claim, _owed in notes if claim]
    return "\n".join(lines) or "(the fragments for this version state no headline)"


def owes(notes: list[tuple[str | None, str | None]]) -> str | None:
    """What it asks of a repository already built: one line per fragment, each naming its own change.

    Every fragment gets a line, including one whose author wrote no catch-up paragraph — said as that,
    because printing it as "asks nothing" would be a promise this module cannot make. None only where
    there are no fragments at all.
    """
    lines = [f"- **{claim or NO_CLAIM}** {owed or NO_NOTE}" for claim, owed in notes]
    return "\n".join(lines) or None


def in_flight(root: Path = ROOT, version: str = VERSION) -> list[Entry]:
    """The entry for the release being written, read off `changelog.d/` — empty where there is none.

    A project migrating onto `1.15.0.dev7` is owed whatever the fragments already ask of it, and until the
    release is cut they are the only place that is written. Every fragment contributes, because the entry
    is the fragments and a project owes all of it rather than the first of it — as a line each, with its
    own claim in front of it, which is what makes "all of it" a list somebody can work through.
    """
    release = base(version)
    found = changelog.fragments(root, tolerant=True)
    if release is None or not found or any(number == release for number, *_rest in released(root / CHANGELOG.name)):
        return []
    notes = fragment_notes(found)
    return [(release, changelog.level(found), claimed(notes), owes(notes))]


def entries(root: Path = ROOT, version: str = VERSION) -> list[Entry]:
    """Every entry, newest first: the one being written, then every one released — the keel's, or a language package's
    at `root` heading for `version`, under the same contract."""
    return in_flight(root, version) + released(root / CHANGELOG.name)


def released(changelog_file: Path = CHANGELOG) -> list[Entry]:
    """Every entry in the changelog, newest first — all of them out, each one a version somebody has.

    Read as UTF-8 rather than as the machine's locale, because `ENTRY` matches on the em-dash: read as
    cp1252 the heading is `## 2.0.0 â€" MINOR`, nothing matched, and every released version came back
    unreleased. Windows was the only runner that said so.
    """
    if not changelog_file.is_file():
        return []
    text = changelog_file.read_text(encoding="utf-8")
    found = list(ENTRY.finditer(text))
    read = []
    for index, match in enumerate(found):
        end = found[index + 1].start() if index + 1 < len(found) else len(text)
        body = text[match.end() : end].strip()
        note = OWED.search(body)
        read.append((
            match.group(1),
            match.group(2),
            claim_of(body) or "(this entry states no headline)",
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


def notes(
    name: str, was: str | None, now: str = VERSION, languages: list[Moved] | tuple[Moved, ...] = (),
    conflicts: Sequence[str] = (), when: datetime | None = None,
) -> str:
    """The page `migrate` writes into the project.

    Always a page: a file that says why there is nothing to list is opened once and answers the question,
    where an absent file is read as "nothing owed" — which is the one thing this must never say by accident.
    It opens with `set_up`, which names `conflicts` where the merge stopped at any, and ends naming the archive
    path it is moved to when done, from the versions and `when` it was written.
    """
    versions = crossed(was, now)
    reason, heading, listed = (
        (None, f"{len(versions)} version(s) taken, newest first", versions) if versions else unlisted(was, now)
    )
    lines = [
        f"# Catch up: {name}, {was or 'an unrecorded version'} to {now}",
        "",
        "`slipwai migrate` wrote this before it returned — whether the merge committed or stopped at conflicts "
        "— from the catch-up note in each version's entry in the factory's own `CHANGELOG.md`, and, under "
        "`Language`, in each language package's own, written by whoever made the change, in the commit that "
        "made it. It is what a merge could not do for you.",
        "",
        "Work it with `/catch-up`, which reads this file and runs `make verify` against it. This file is "
        "git-ignored and stays on this machine: archive it when the work is done, as its last step says.",
        # After the introduction and before anything that is owed: nothing below can be worked in a project
        # whose merge is unfinished or whose agent still reads the old pages.
        *set_up(conflicts),
    ]
    if reason is not None:
        lines += ["", "## Why the versions crossed could not be listed as such", "", f"Because {reason}"]
    lines += ["", f"## {heading}"]
    if not listed:
        lines += ["", "(nothing)"]
    lines += listing(listed)
    for moved in languages:
        lines += language_section(moved)
    lines += [
        "",
        "## Then",
        "",
        "`make verify`. A gate that is new in one of the versions above fails code that was correct when it "
        "was written; the entry that introduced it says what it now wants instead. Never edit a gate to make "
        "it pass — it came from the factory, the next migration brings it back, and a locally softened copy "
        "is a false green until then.",
        "",
        stated(was, now, when or datetime.now(UTC)),
        "",
    ]
    return "\n".join(lines)


def listing(listed: list[Entry]) -> list[str]:
    """Each entry as the notes print it: its number and level, its claim, and what it owes.

    A released entry's two halves are each one paragraph, written by whoever cut the release, and are
    printed as they were written. A release still in flight has a line per fragment (`in_flight`), and a
    list does not start on the same line as the words introducing it — so `**Owes:**` stands alone
    wherever what follows it is more than one line.
    """
    lines: list[str] = []
    for number, level, headline, owed in listed:
        said = "nothing recorded for a repository that already existed." if owed is None else owed
        apart = "\n" in said
        lines += ["", f"### {number}{f' — {level}' if level else ''}", "", headline, "",
                  *(["**Owes:**", "", said] if apart else [f"**Owes:** {said}"])]
    return lines


def language_section(moved: Moved) -> list[str]:
    """One language's part of the notes: what its own changelog says between the version recorded and the one that
    has just replayed the project (Story 4 scenario 2). With no recorded version, every entry — its history starts
    at the split, and which part of it this project already had is not recorded anywhere (scenario 8, D72)."""
    everything = [entry for entry in entries(moved.root, moved.now) if parts(entry[0]) <= parts(moved.now)]
    lines = ["", f"## Language {moved.name}, {moved.was or 'no recorded version'} to {moved.now}"]
    if moved.was is None:
        lines += ["", f"{moved.name} has no recorded version here: its history starts at the split, so every entry of "
                      "its changelog is listed, newest first."]
        listed = everything
    elif not parts(moved.was) or not parts(moved.now):
        lines += ["", f"`{moved.was}` or `{moved.now}` does not read as a version, so the entries crossed cannot be "
                      "told; every entry is listed."]
        listed = everything
    elif parts(moved.was) == parts(moved.now):
        lines += ["", f"Both are {base(moved.now)}: the entry as it stands today is below, read as a whole."]
        listed = [entry for entry in everything if parts(entry[0]) == parts(moved.now)]
    else:
        listed = [entry for entry in everything if parts(moved.was) < parts(entry[0])]
    return lines + (listing(listed) if listed else ["", "(nothing recorded in its changelog for these versions)"])


def moved_languages(document: dict) -> list[Moved]:
    """Every loaded package the project needs whose version is not the recorded one: the record's names, or for a
    1.x project with none, the packages answering its applications, each with no recorded version."""
    recorded = recorded_languages(document)
    names = list(recorded) if recorded is not None else list(answering(apps_from_manifest(document, allow_empty=True)))
    loaded, roots = loaded_versions(), {package.name: package.root for package in PACKAGES}
    was = recorded or {}
    return [Moved(name, was.get(name), loaded[name], roots[name])
            for name in sorted(names) if name in loaded and was.get(name) != loaded[name]]
