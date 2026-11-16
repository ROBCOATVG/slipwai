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

**Confirm is the edit the record already asks a person for.** `decisions.md` says "a person overrides one by
editing its `Status`", and `/cruise` writes `confirmed by human <date>` when a person's word confirms one. So
Confirm does exactly that to an entry `awaiting human confirmation`, in the checkout whose copy the board read
it from, and writes the read receipt with it — see `confirm`. The cards are drawn by `decision_cards.py`.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .decision_entry import SENTENCE, awaiting, confirmed_status, parse
from .deck import entries, mark_read, streams
from .logs import logs_dir

#: Where a decision with no deck line is marked read: beside the logs, which Git already ignores.
UPSTREAM_READ = "decisions-read.json"
_NUMBER = re.compile(r"^\s*(D\d+)\b")
#: The parts of an entry shown under its decision, in this order.
SHOWN = ("Question", "Options", "Why", "Read against", "Confidence", "Would reverse if", "Written to", "Status")
#: Where the entry was read from: the file, kept beside its parts so Confirm edits the copy the board showed.
FROM = "_file"


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
    source: str = ""

    @property
    def awaiting(self) -> bool:
        return awaiting(self.status)


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
                found.setdefault(number, {**parts, FROM: str(path)})
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
    used: set[str] = set()
    found: list[Decision] = []
    for feature, fairway in streams(root):
        lines, _ = entries(root, fairway, feature)
        asked = {str(e.fields.get("id")): str(e.fields.get("what", "")) for e in lines if e.kind == "question"}
        receipts = {str(e.fields.get("told")) for e in lines if e.kind == "read"}
        for line in (e for e in lines if e.kind == "decision"):
            what, ident = str(line.fields.get("what", "")), str(line.fields.get("id", ""))
            named = _NUMBER.match(what)
            # The line's own `id` where its words do not open with the number: a launch's decisions carry
            # `id: D9` and a sentence, and read as "D9 (not in decisions.md)" beside the entry they were.
            number = named.group(1) if named else (ident if re.fullmatch(r"D\d+", ident) else "")
            entry = book.get(number, {})
            used.add(number)
            by = str(line.fields.get("decided_by", "")) or entry.get("Decided by", "")
            yours = by == "human"
            parts = _shown(entry)
            if ident in asked and "Question" not in parts:
                parts["Question"] = asked[ident]
            title = entry.get("title") or asked.get(ident) or (f"{ident} (not in decisions.md)" if ident else what)
            piece = str(line.fields.get("slice", "")) or _slice(entry.get("Slice", ""))
            found.append(Decision(f"deck:{fairway}:{line.t}", number or ident, title,
                                  entry.get("Decision") or what, line.t, piece, fairway,
                                  "you" if yours else by, parts, yours or line.t in receipts, yours,
                                  entry.get(SENTENCE, ""), entry.get("Status", ""), charted.get(piece, ""),
                                  entry.get(FROM, "")))
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
                              charted.get(piece, ""), entry.get(FROM, "")))
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
        elif kind == "md" and re.fullmatch(r"D\d+", rest):
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


def _copies(checkout: Path, number: str) -> list[Path]:
    """Every file in one checkout holding this entry: the feature's record, and a fairway's own copy it is
    rendered from, so `render-fairways --check` still finds the two agreeing."""
    heading = re.compile(rf"^## {re.escape(number)}\s*[—-]", re.MULTILINE)
    found = [*sorted(checkout.glob("specs/*/decisions.md")), *sorted(checkout.glob("fairways/**/decisions.md"))]
    return [path for path in found if heading.search(path.read_text(encoding="utf-8"))]


def _restatus(path: Path, number: str, day: str) -> bool:
    """Set this entry's `Status` line, and only this entry's, to confirmed. False where it does not await."""
    text = path.read_text(encoding="utf-8")
    head = re.search(rf"^## {re.escape(number)}\s*[—-].*$", text, re.MULTILINE)
    if not head:
        return False
    after = re.search(r"^## ", text[head.end():], re.MULTILINE)
    end = head.end() + after.start() if after else len(text)
    block = text[head.end():end]
    line = re.search(r"^(- \*\*Status:\*\*[ \t]*)(.*)$", block, re.MULTILINE)
    status = confirmed_status(line.group(2), day) if line else None
    if not line or status is None:
        return False
    block = block[:line.start(2)] + status + block[line.end(2):]
    path.write_text(text[:head.end()] + block + text[end:], encoding="utf-8")
    return True


def _clean(checkout: Path, paths: list[Path]) -> bool:
    shown = subprocess.run(["git", "-C", str(checkout), "status", "--porcelain", "--", *map(str, paths)],
                           capture_output=True, text=True, check=False)
    return shown.returncode == 0 and not shown.stdout.strip()


def confirm(root: Path, key: str, today: date | None = None) -> str:
    """A person confirms a decision that awaits them: what Confirm on its card does, and all it does.

    1. The entry's `Status` goes from `awaiting human confirmation` to `confirmed by human <date>` — the
       status `/cruise` writes when a person's word confirms one — in the checkout the board read the entry
       from (trunk's copy where trunk has it, else the berth whose slice wrote it), in its feature record and
       in any fairway copy that record is rendered from. Nothing else in the entry or the file changes.
    2. Where those files had no other uncommitted change, the edit is committed there on its own, so a merge
       the harbour makes into that checkout next is not refused over a file somebody left edited. Where they
       had one, the edit is left beside it uncommitted, and the answer says so, because committing would
       carry somebody else's half-written words with it.
    3. The decision's read receipt is written, as Mark read writes it, where it was not read already.
    """
    one = next((each for each in decisions(root) if each.key == key), None)
    if one is None:
        raise ValueError(f"{key!r} names no decision on this board")
    if not one.awaiting:
        raise ValueError(f"{one.number} is not awaiting confirmation; its status is {one.status or 'not written'}")
    if not one.source:
        raise ValueError(f"{one.number} has no entry in any decisions.md to confirm")
    source = Path(one.source)
    checkout = next((place for place in checkouts(root) if source.resolve().is_relative_to(place.resolve())),
                    root)
    paths = _copies(checkout, one.number)
    clean = _clean(checkout, paths)
    day = (today or date.today()).isoformat()
    changed = [path for path in paths if _restatus(path, one.number, day)]
    if not changed:
        raise ValueError(f"{one.number}'s `Status` line could not be found to change; edit it by hand")
    where = "trunk" if checkout.resolve() == root.resolve() else f"the berth at {checkout.name}"
    said = f"{one.number} confirmed in {where}"
    if clean:
        committed = subprocess.run(
            ["git", "-C", str(checkout), "commit", "--quiet", "-m",
             f"A person confirmed {one.number} on the board", "--", *map(str, changed)],
            capture_output=True, text=True, check=False)
        said += "" if committed.returncode == 0 else "; not committed, the commit was refused there"
    else:
        said += "; left uncommitted beside the change already in that file"
    if not one.read:
        said += "; " + mark(root, [key])
    return said
