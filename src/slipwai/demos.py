"""Who accepts a whole capability, and what the board reads off the logs because of it.

The owner's question settled it: "do we need accept if we're running skipper. I think it's just an
opportunity to add feedback." So the hand's verdict at a capability's walk is its acceptance unless the
project says otherwise, and the film the hand made is something a person looks at when they have time,
never something the run waits on. `.specify/cruise.json`'s `demos` says which: `hand`, the default, or
`person`, which is the board as it was — a capability due a demo, and Accept or Not yet beside it.

**Read here, and nowhere else in the keel**, because two readers turn on it and must agree: the board's fold
(`fleet.board`), which says what is owed a person, and the card that offers a film to comment on. The
toolkit's `clearance.py` and `capabilities.py` read the same key for themselves, since a generated project
has no slipwai to import.

An `accepted` line names who accepted with `by`. One the hand wrote is the acceptance under `hand`; under
`person` it is the last reading before a person's, and closes nothing. A line with no `by` is a person's, as
every such line was before this setting existed.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .logs import Entry, run_dir

CONFIG = ".specify/cruise.json"
#: The setting's two values: the hand's verdict accepts a capability, or a person's does.
HAND = "hand"
PERSON = "person"
#: Who an `accepted` line names when the hand wrote it.
WALKER = "sail-demo-hand"
#: Written beside a capability's film the first time a person opens it, so it stops being listed as
#: something to look at. Under the run folder, with the film, and never committed.
OPENED = "opened"


def setting(root: Path) -> str:
    """`hand` or `person`. Absent, unreadable or unknown is `hand`: a project written before the setting
    existed has nobody waiting on a demo, because nothing ever wrote the line that would have made one due."""
    try:
        held = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return HAND
    value = held.get("demos") if isinstance(held, dict) else None
    return PERSON if value == PERSON else HAND


def accepts(line: Entry, demos: str) -> bool:
    """Whether this `accepted` line accepts its capability under this setting."""
    return demos != PERSON or str(line.fields.get("by", "")) != WALKER


def acceptance(found: Iterable[tuple[str, list[Entry]]], demos: str) -> tuple[list[str], dict[str, str]]:
    """The capabilities accepted, and each one owed a person's demo against the fairway whose log said so.

    Under `hand` nothing is owed a person: a `demo-due` line, from a run that had the setting the other way
    or written by hand, is not a person being asked anything.
    """
    pairs = [(name, line) for name, entries in found for line in entries]
    accepted = {str(line.fields.get("capability")) for _, line in pairs
                if line.kind == "accepted" and accepts(line, demos)}
    due = {} if demos != PERSON else {
        str(line.fields.get("capability")): name for name, line in pairs
        if line.kind == "demo-due" and str(line.fields.get("capability")) not in accepted}
    return sorted(accepted), due


def walk(root: Path, feature: str, capability: str) -> Path:
    return run_dir(root) / "walks" / feature / capability


def opened(root: Path, feature: str, capability: str) -> bool:
    return (walk(root, feature, capability) / OPENED).is_file()


def mark_opened(root: Path, feature: str, capability: str) -> None:
    """Say a person has opened this film. For the route that serves a person's press of Play; the page's own
    load fetches the film's first bytes for its length, which is not anybody watching it."""
    where = walk(root, feature, capability)
    if where.is_dir() and not opened(root, feature, capability):
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        (where / OPENED).write_text(stamp + "\n", encoding="utf-8")
