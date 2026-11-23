#!/usr/bin/env python3
"""The careen's list, and the one writer that keeps it.

A fairway's careen — `fairways/<fairway>/careen.md` — is the list every slice of that fairway stows into, and
the hardening slice that closes it. For a long while each slice was told to write its rows straight into it,
while `check-slice-scope` refused `fairways/` to a slice: one file shared by every slice in the stream is
the shared-surface conflict that gate exists to stop. So a slice wrote the rows, was refused, moved them to
its capability's record, handed the careen back, and then conflicted with the mender's landing of its own
rows — five merge attempts for S62 on manda — while most stowed rows never reached the careen at all.

So there is one writer now. **A slice stows into its own capability's record**,
`specs/<feature>/capabilities/<capability>/stowed.md`, which is the slice's to write, in the careen's row
shape. **The harbourmaster carries those rows into the careen** on every merge that brings a `stowed.md`
in, under a section for that capability, as a plain file operation in the merge's own scratch worktree —
committed before the gate, so the gate runs on it and trunk moves once. A row already in the careen is
never added twice, so the same record carried by every later slice of the capability adds only its new rows.

**And the careen runs.** Once every planned slice of a fairway is merged and its careen has a row still
open, the captain starts `<fairway>-careen` as that fairway's next and last slice, whatever the release
state — a pre-launch product hoists no flag, so "before the flag is hoisted" alone was a moment that never
came, and the stream reported *every slice is claimed or merged* and went idle on a list nobody worked.

Standalone and dependency-free, like everything under `scripts/`.
"""
from __future__ import annotations

import re

#: The columns of one stowed row, in the careen and in a capability's `stowed.md` alike.
COLUMNS = ("Stowed", "By slice", "From", "Severity", "What it is", "State")
HEADER = "| " + " | ".join(COLUMNS) + " |"
RULE = "|" + "---|" * len(COLUMNS)
#: A capability's stowed record, as a merge's changed path names it.
STOWED = re.compile(r"^specs/[^/]+/capabilities/(?P<capability>[^/]+)/stowed\.md$")
#: What the careen slice of a fairway is called: one per fairway, after every planned slice.
SUFFIX = "-careen"
#: A separator row of a markdown table: nothing but pipes, dashes, colons and spaces.
SEPARATOR = re.compile(r"^\|[\s|:-]+\|$")


def careen_path(fairway: str) -> str:
    """Where a fairway's careen is, from the project's root."""
    return f"fairways/{fairway}/careen.md"


def stowed_path(feature: str, capability: str) -> str:
    """Where a capability's slices stow, from the project's root."""
    return f"specs/{feature}/capabilities/{capability}/stowed.md"


def careen_slice(fairway: str) -> str:
    """The id the careen slice of this fairway is claimed under: `slice/<fairway>-careen` is its branch."""
    return f"{fairway}{SUFFIX}"


def fairway_of(slice_id: str) -> str:
    """The fairway a careen slice closes, or `""` where the id is not a careen's."""
    return slice_id[:-len(SUFFIX)] if slice_id.endswith(SUFFIX) and len(slice_id) > len(SUFFIX) else ""


def cells(line: str) -> list[str]:
    """A table row's cells, stripped. `\\|` inside a cell is a pipe in the text, not a column."""
    inner = line.strip()[1:-1] if line.strip().endswith("|") else line.strip()[1:]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", inner)]


def rows(text: str) -> list[str]:
    """Every stowed row in a page, as written: table lines that are not a header, a rule or the template's
    own placeholder row."""
    found = []
    for line in text.splitlines():
        held = line.strip()
        if not held.startswith("|") or SEPARATOR.match(held):
            continue
        parts = cells(held)
        if len(parts) < len(COLUMNS) or parts[0] == COLUMNS[0] or parts[0].startswith("<"):
            continue
        found.append(held)
    return found


def key(row: str) -> tuple[str, ...]:
    """What makes two rows the same row: everything but its state, which the careen slice moves to `done`."""
    return tuple(" ".join(cell.split()) for cell in cells(row)[:len(COLUMNS) - 1])


def is_open(row: str) -> bool:
    """A row still owed: any state but `done`, which is the only way a row leaves the careen."""
    state = cells(row)[len(COLUMNS) - 1].lower() if len(cells(row)) >= len(COLUMNS) else ""
    return not state.startswith("done")


def open_rows(text: str) -> list[str]:
    return [row for row in rows(text) if is_open(row)]


def page(fairway: str) -> str:
    """A fairway's careen as the harbourmaster first writes it. Held to `slipwai.project.careen.careen_page`
    by the keel's suite, so the page a project is told about and the page it is given are one page."""
    return f"""# Careen — {fairway}

What this fairway stowed, and what its careen slice closes. The harbourmaster writes this file: on every
merge that brings a capability's `stowed.md` in, it appends that record's new rows under the capability's
own heading. A slice never writes here; it stows into its capability's record, and the careen slice is the
one that moves a row's state to `done`.

**Nothing CRITICAL is ever on this list.** Data of one actor reaching another, or an actor gaining a role,
is the next slice rather than something to look at later, and the stage that found it says so instead of
writing a row.

**Nor is any finding of these kinds, whatever its severity and whatever the bar.** A finding that leaves a feature unusable or untrustworthy for its actor is never deferred:

- `validation-bypass` — input coercion or a validation bypass on a state-changing route
- `document-forgery` — forgery or injection into a generated document — a PDF, an email
- `erasure-leak` — personal data that survives, or leaks, after deletion or erasure
- `money-arithmetic` — wrong arithmetic in a money or financial figure

**A row is a decision, not a note.** *What it is* says what is wrong and what closing it would take, in one
line a reader who was not there can act on. A row that only names a file is a row the careen slice has to
rediscover, which is the cost the stowing was supposed to avoid.
"""


def appended(text: str, fairway: str, capability: str, new: list[str]) -> tuple[str, int]:
    """The careen with these rows under `capability`'s heading, and how many were added.

    A row whose key — every cell but its state — is anywhere in the page already is not added again, so
    carrying a whole record on every merge adds only what that merge stowed, and a row the careen slice has
    since closed is not reopened by the record that first stowed it. An empty page is started from `page`.
    """
    held = {key(row) for row in rows(text)}
    adding = []
    for row in new:
        if key(row) not in held:
            held.add(key(row))
            adding.append(row)
    if not adding:
        return text, 0
    lines = (text if text.strip() else page(fairway)).splitlines()
    heading = f"## {capability}"
    at = next((index for index, line in enumerate(lines) if line.strip() == heading), None)
    if at is None:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", heading, "", HEADER, RULE, *adding]
    else:
        end = at + 1
        while end < len(lines) and not lines[end].strip():
            end += 1
        if end < len(lines) and lines[end].strip().startswith("|"):
            while end < len(lines) and lines[end].strip().startswith("|"):
                end += 1
            lines[end:end] = adding
        else:
            lines[at + 1:at + 1] = ["", HEADER, RULE, *adding]
    return "\n".join(lines) + "\n", len(adding)
