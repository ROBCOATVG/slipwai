"""The decision log: every decision this project took, readable, each with its own read receipt.

The board's only view of decisions was *N decision(s) nobody has read yet* under *Waiting on you*, opening
on the deck log's lines — `D95 (a): the source alone settles the item; no answer stored or parsed (as D68)`
— with a Mark read beside each. The line is the decision's id and its answer letter. The question, the
options, why, and what would reverse it are in `specs/<feature>/decisions.md`, which the board never showed,
and a person asked to say they had read a decision was shown the one form of it nobody can read.

**One entry per decision, from three places.** A deck `decision` line is what a read receipt names. The
`decisions.md` entry its `D<n>` names is what a person reads — taken from every checkout of the project,
because a slice in flight has written its decisions into its own branch's copy and trunk's is behind until
it merges. And the deck's `question` line with the same `id` is the question a person's own answer —
`decide for me` — was an answer to, which on its own reads as nothing at all.

**The receipt is the one the ceiling counts.** Mark read writes the deck `read` line, as before, so reading
here is what lets a stream parked at its decision ceiling go on. A decision taken before the fleet existed —
in clarify, in the chart — has no deck line and holds nothing up; its receipt is kept beside the logs in
`decisions-read.json`, so the log can still say which of those a person has read.

**Confirm is a record, as a read is.** A person confirming an entry `awaiting human confirmation` is kept
beside the logs in `decisions-confirmed.json`, with the read receipt; the board edits and commits nothing in
the project — see `confirm`. The cards are drawn by `decision_cards.py`.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .decision_entry import ID, SENTENCE, awaiting, is_id, parse
from .deck import entries, mark_read, streams
from .logs import logs_dir

#: Where a decision with no deck line is marked read: beside the logs, which Git already ignores.
UPSTREAM_READ = "decisions-read.json"
#: Where a person's Confirm is kept, beside the read receipts and for the same reason.
CONFIRMED = "decisions-confirmed.json"
_NUMBER = re.compile(rf"^\s*({ID})\b")
#: The parts of an entry shown under its decision, in this order.
SHOWN = ("Question", "Options", "Why", "Read against", "Confidence", "Would reverse if", "Written to", "Status")
#: Which feature's record the entry was read from: a confirmation is kept against it.
FROM = "_feature"


@dataclass
class Decision:
    """One decision as a person reads it, and how its read receipt is written."""

    key: str
    number: str
    title: str
    decision: str
    when: str
    slice: str = ""
    stream: str = ""
    decided_by: str = ""
    parts: dict[str, str] = field(default_factory=dict)
    read: bool = False
    yours: bool = False
    sentence: str = ""
    status: str = ""
    capability: str = ""
    feature: str = ""
    confirmed: str = ""

    @property
    def awaiting(self) -> bool:
        """Awaiting a person: the entry says so and nobody has confirmed it on the board since."""
        return awaiting(self.status) and not self.confirmed


def checkouts(root: Path) -> list[Path]:
    """This checkout first, then every other worktree of the same repository: the berths."""
    done = subprocess.run(["git", "-C", str(root), "worktree", "list", "--porcelain"], capture_output=True,
                          text=True, check=False)
    others = [Path(line[9:]) for line in done.stdout.splitlines() if line.startswith("worktree ")]
    return [root, *(one for one in others if one.resolve() != root.resolve())]


def written(root: Path) -> dict[str, dict[str, str]]:
    """Every `decisions.md` entry in any checkout. Trunk's copy wins where both have one; a berth adds the ones
    its slice has taken since it branched."""
    found: dict[str, dict[str, str]] = {}
    for place in checkouts(root):
        for path in sorted(place.glob("specs/*/decisions.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for number, parts in parse(text).items():
                found.setdefault(number, {**parts, FROM: path.parent.name})
    return found


def capabilities(root: Path) -> dict[str, str]:
    """Each slice's capability, as the chart names it: `slices: <id>: capability: <name>`."""
    found: dict[str, str] = {}
    for chart in sorted(root.glob("specs/*/chart.yaml")):
        current = ""
        for line in chart.read_text(encoding="utf-8", errors="replace").splitlines():
            if (named := re.match(r"^\s{2}([A-Za-z0-9_.-]+):\s*$", line)):
                current = named.group(1)
            elif current and (held := re.match(r"^\s{4}capability:\s*['\"]?([^'\"#]+?)['\"]?\s*$", line)):
                found.setdefault(current, held.group(1))
    return found


def upstream_read(root: Path) -> set[str]:
    try:
        held = json.loads((logs_dir(root) / UPSTREAM_READ).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return set()
    return {str(one) for one in held} if isinstance(held, list) else set()


def _shown(entry: dict[str, str]) -> dict[str, str]:
    return {key: entry[key] for key in SHOWN if entry.get(key)}


def _slice(value: str) -> str:
    return value.strip("— ").strip()


def decisions(root: Path) -> list[Decision]:
    """Every decision, newest first."""
    book = written(root)
    charted = capabilities(root)
    sure = confirmations(root)
    used: set[str] = set()
    found: list[Decision] = []
    for feature, fairway in streams(root):
        lines, _ = entries(root, fairway, feature)
        asked = {str(e.fields.get("id")): str(e.fields.get("what", "")) for e in lines if e.kind == "question"}
        receipts = {str(e.fields.get("told")) for e in lines if e.kind == "read" and not e.fields.get("inbox")}
        for line in (e for e in lines if e.kind == "decision"):
            what, ident = str(line.fields.get("what", "")), str(line.fields.get("id", ""))
            named = _NUMBER.match(what)
            # The line's own `id` where its words do not open with the number: a launch's decisions carry
            # `id: D9` and a sentence, and read as "D9 (not in decisions.md)" beside the entry they were.
            number = named.group(1) if named else (ident if is_id(ident) else "")
            entry = book.get(number, {})
            used.add(number)
            by = str(line.fields.get("decided_by", "")) or entry.get("Decided by", "")
            yours = by == "human"
            parts = _shown(entry)
            if ident in asked and "Question" not in parts:
                parts["Question"] = asked[ident]
            title = entry.get("title") or asked.get(ident) or (f"{ident} (not in decisions.md)" if ident else what)
            piece = str(line.fields.get("slice", "")) or _slice(entry.get("Slice", ""))
            home = entry.get(FROM) or feature
            found.append(Decision(f"deck:{fairway}:{line.t}", number or ident, title,
                                  entry.get("Decision") or what, line.t, piece, fairway,
                                  "you" if yours else by, parts, yours or line.t in receipts, yours,
                                  entry.get(SENTENCE, ""), entry.get("Status", ""), charted.get(piece, ""),
                                  home, sure.get(f"{home}/{number or ident}", "")))
    marked = upstream_read(root)
    for number, entry in book.items():
        if number in used:
            continue
        piece = _slice(entry.get("Slice", ""))
        # A person's own answer is theirs whichever place it was read from. Only a deck line's `decided_by`
        # was looked at, so an entry `Decided by: human` with no deck line — an answer given in a
        # conversation and written straight into the record — was shown as somebody else's.
        yours = entry.get("Decided by", "").strip() == "human"
        found.append(Decision(f"md:{number}", number, entry.get("title", ""), entry.get("Decision", ""),
                              entry.get("When", ""), piece, entry.get("Stream", ""),
                              "you" if yours else entry.get("Decided by", ""), _shown(entry),
                              yours or number in marked, yours, entry.get(SENTENCE, ""), entry.get("Status", ""),
                              charted.get(piece, ""), entry.get(FROM, ""),
                              sure.get(f"{entry.get(FROM, '')}/{number}", "")))
    return sorted(found, key=lambda one: (one.when, one.number), reverse=True)


def mark(root: Path, keys: list[str]) -> str:
    """Write the read receipt for each decision named: the deck `read` line, or the upstream file."""
    by_stream: dict[str, list[str]] = {}
    upstream: list[str] = []
    for key in keys:
        kind, _, rest = key.partition(":")
        if kind == "deck" and ":" in rest:
            fairway, _, stamp = rest.partition(":")
            by_stream.setdefault(fairway, []).append(stamp)
        elif kind == "md" and is_id(rest):
            upstream.append(rest)
        else:
            raise ValueError(f"{key!r} names no decision")
    said = [mark_read(root, fairway, stamps) for fairway, stamps in by_stream.items()]
    if upstream:
        known = {one.number for one in decisions(root) if one.key.startswith("md:")}
        wanted = sorted(upstream_read(root) | (set(upstream) & known))
        path = logs_dir(root) / UPSTREAM_READ
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(wanted, indent=0) + "\n", encoding="utf-8")
        said.append(f"marked {len(set(upstream) & known)} earlier decision(s) read")
    return "; ".join(said) or "nothing to mark"


def confirmations(root: Path) -> dict[str, str]:
    """Every decision a person confirmed on the board, as `<feature>/<id>` → the instant they did."""
    try:
        held = json.loads((logs_dir(root) / CONFIRMED).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return {str(key): str(value) for key, value in held.items()} if isinstance(held, dict) else {}


def confirm(root: Path, key: str, now: datetime | None = None) -> str:
    """A person confirms a decision that awaits them: a record beside the logs, and the read receipt.

    The record is `decisions-confirmed.json`, keyed `<feature>/<id>` with the instant, kept where
    `decisions-read.json` is — which Git ignores — and read back by `decisions` so the card says the decision
    is confirmed. Nothing in any checkout's working tree is touched and nothing is committed: the board does
    not know whose name a commit would carry, a berth's `decisions.md` is its agent's while it works, and an
    entry is the owning stream's to rewrite. `/cruise` already writes `confirmed by human <date>` into the
    entry when its stream is told a person confirmed it; this does not tell it (a later stream carries the
    board's messages to streams), so the record is what the board shows until the entry itself says so.
    """
    one = next((each for each in decisions(root) if each.key == key), None)
    if one is None:
        raise ValueError(f"{key!r} names no decision on this board")
    if not one.awaiting:
        raise ValueError(f"{one.number} is not awaiting confirmation; its status is {one.status or 'not written'}")
    held = confirmations(root)
    held[f"{one.feature}/{one.number}"] = (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = logs_dir(root) / CONFIRMED
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(held, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    said = f"{one.number} confirmed"
    if not one.read:
        said += "; " + mark(root, [key])
    return said
