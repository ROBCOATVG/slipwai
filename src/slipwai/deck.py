"""One stream's log, as a person reads it: a line each, in the words of what happened.

`fleet.py` folds every log into a board — eight columns and a count. That answers *is anything stuck*, and
the moment the answer is yes the next question is always the same one: **what has this stream actually been
doing?** The board cannot answer it, because the answer is forty lines of one file and the board is one row.

So this is the other half: the stream's own log, newest last, each line said rather than printed. A
`mark-set` is not `{"kind": "mark-set", "mark": "OrderPlaced"}`; it is *set OrderPlaced*, and the
difference between those two is whether somebody who is not holding the format in their head can read it.

**It says the kind it does not know.** A line of a kind this has no sentence for is shown as its kind and
its fields rather than skipped — the log grows, and a reader meeting an unfamiliar line should see that
there was one.
"""
from __future__ import annotations

from pathlib import Path

from .logs import Entry, Unreadable, deck_logs, deck_path, fold

#: How many lines one stream shows by default. Enough to cover a slice; short enough to read.
RECENT = 60


def said(entry: Entry) -> str:
    """One log line as a sentence. The kind and its fields where there is no sentence for it."""
    at = entry.fields
    kind = entry.kind
    if kind == "claimed":
        return f"claimed {at.get('slice')}"
    if kind == "mark-set":
        return f"set {at.get('mark')} — {at.get('slice')}"
    if kind == "demo":
        return f"demo of {at.get('slice')}: {at.get('verdict')}"
    if kind == "accepted":
        return f"accepted the {at.get('capability')} capability"
    if kind == "demo-due":
        return f"the {at.get('capability')} capability is ready to demo"
    if kind == "merged":
        return f"merged {at.get('slice')} as {str(at.get('commit'))[:8]}"
    if kind == "decision":
        return f"decided {at.get('id')}: {at.get('what')}"
    if kind == "told":
        return f"a person said: {at.get('message')}"
    if kind == "read":
        return f"read what was said at {at.get('told')}"
    if kind == "heartbeat":
        spent = at.get("tokens")
        return "still going" + (f", {spent}k spent" if spent is not None else "")
    if kind == "stowed":
        return f"stowed {at.get('what')} from {at.get('from')} — {at.get('slice')}"
    if kind == "parked":
        return f"parked: {at.get('why')}"
    if kind == "request":
        return f"asked to {at.get('what')}: {at.get('detail')}"
    if kind == "berth-request":
        return "asked for a berth"
    rest = ", ".join(f"{name}={value}" for name, value in at.items())
    return f"{kind}" + (f" ({rest})" if rest else "")


def streams(root: Path) -> list[tuple[str, str]]:
    """Every stream with a log, as (feature, fairway), in name order."""
    return [(path.parent.name, path.stem) for path in deck_logs(root)]


def feature_of(root: Path, fairway: str) -> str:
    """Which feature this stream's log is under, or `''` where it has none."""
    return next((feature for feature, name in streams(root) if name == fairway), "")


def entries(root: Path, fairway: str, feature: str = "") -> tuple[list[Entry], str]:
    """One stream's entries, and the fault where its log cannot be read.

    The fault is returned rather than raised, and the entries with it: a log that goes bad at line 90 has
    89 lines somebody still wants, and the whole point of looking at one stream is that something has
    gone wrong with it.
    """
    found = feature or feature_of(root, fairway)
    if not found:
        return [], f"{fairway} has no log here"
    path = root / deck_path(found, fairway)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as fault:
        return [], f"{path} cannot be read ({type(fault).__name__})"
    kept: list[Entry] = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            kept += fold([line])
        except Unreadable as fault:
            return kept, f"line {number} cannot be read: {fault}"
    return kept, ""


def recent(root: Path, fairway: str, limit: int = RECENT) -> tuple[list[tuple[str, str]], str]:
    """The last `limit` lines of one stream as (when, what), and the fault where there is one."""
    found, fault = entries(root, fairway)
    return [(one.t, said(one)) for one in found[-limit:]], fault
