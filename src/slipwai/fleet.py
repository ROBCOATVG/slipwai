"""The fleet board: every column folded from the logs, and nothing kept anywhere else.

The first attempt had a checkpoint file that was the single source of status. It died at iteration two and
said "iteration 2" while twenty slices merged. MANDA had the same shape fail the other way: `model.yaml`
said `planned` for eight slices that were built and merged, because the field was written at plan time and
never reconciled.

**So the board stores nothing.** Every column is computed from the deck logs and the harbour log each time
it is drawn. A board that can be wrong about what happened is worse than no board, because it is believed.

**A stalled berth is told from a finished one.** They look identical in a status field — neither is writing
anything — and they are the two states it matters most to tell apart. The log tells them apart for free: a
berth whose last line is a `merged` has finished, and one whose last line is anything else and whose
heartbeat is older than the bound has stalled. That is the whole reason `heartbeat` is a line.

**What it does not have, it says it does not have.** A fairway with no lines is `not started`, not `0%`. A
number nobody wrote is `—`, not `0`. Both of those are the same rule as the rest: the board reports the log,
and where the log is silent the board is silent too.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .deck import recent
from .logs import Entry, Unreadable, deck_logs, fold, harbour_logs

#: Minutes since the last line after which a berth that has not finished is drawn as stalled. The default
#: where `harbour.json` says nothing: a wait with no bound is indistinguishable from a run that has stopped.
STALL_MINUTES = 15
#: How many lines the event feed carries. Enough to see what a stage did, short enough to read.
FEED = 40
#: What a column says where the log says nothing. Not `0`: a number nobody wrote is not a number that is zero.
NOTHING = "—"


@dataclass
class Fairway:
    """One fairway as its own log says it is."""

    name: str
    feature: str
    entries: list[Entry] = field(default_factory=list)

    @property
    def claimed(self) -> list[str]:
        return [str(e.fields["slice"]) for e in self.entries if e.kind == "claimed"]

    @property
    def merged(self) -> list[str]:
        return [str(e.fields["slice"]) for e in self.entries if e.kind == "merged"]

    @property
    def marks(self) -> list[str]:
        return [str(e.fields["mark"]) for e in self.entries if e.kind == "mark-set"]

    @property
    def parked(self) -> str:
        return next((str(e.fields["why"]) for e in reversed(self.entries) if e.kind == "parked"), "")

    @property
    def slice_now(self) -> str:
        """The slice being worked: the last claimed that has not merged."""
        merged = set(self.merged)
        return next((one for one in reversed(self.claimed) if one not in merged), "")

    @property
    def last(self) -> str:
        return self.entries[-1].t if self.entries else ""

    @property
    def tokens(self) -> int | None:
        """Thousands of input tokens this fairway's lines record, or None where none of them record any."""
        found = [e.fields["tokens"] for e in self.entries if isinstance(e.fields.get("tokens"), int | float)]
        return int(sum(found)) if found else None

    @property
    def unanswered(self) -> list[Entry]:
        """Every `told` from a person with no `read` receipt against it."""
        receipts = {str(e.fields["told"]) for e in self.entries if e.kind == "read"}
        return [e for e in self.entries if e.kind == "told" and e.t not in receipts]


def minutes_since(stamp: str, now: datetime | None = None) -> float | None:
    """Minutes since an ISO instant, or None where it is not one this can read."""
    try:
        when = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None
    return ((now or datetime.now(UTC)) - when).total_seconds() / 60.0


def state_of(fairway: Fairway, bound: float = STALL_MINUTES, now: datetime | None = None) -> str:
    """One word for what this fairway is doing, and `stalled` is the one that has to be earned.

    `finished` and `stalled` look identical in a status field — neither is writing anything — and they are
    the two it matters most to tell apart. The last line tells them apart for nothing.
    """
    if not fairway.entries:
        return "not started"
    if fairway.parked:
        return "parked"
    last = fairway.entries[-1]
    if last.kind == "merged" and not fairway.slice_now:
        return "finished"
    since = minutes_since(fairway.last, now)
    if since is not None and since > bound:
        return "stalled"
    return "working"


def read_log(path: Path, harbour: bool = False) -> tuple[list[Entry], str]:
    """One log's entries, or the fault that says why it could not be read.

    A log that cannot be read makes the board say so for that fairway rather than drawing it empty. An empty
    row and an unreadable one are different facts and a board that drew both the same would be guessing.
    """
    try:
        return fold(path.read_text(encoding="utf-8").splitlines(), harbour=harbour), ""
    except (OSError, UnicodeDecodeError) as fault:
        return [], f"{type(fault).__name__}"
    except Unreadable as fault:
        return [], str(fault)


def fairways(root: Path) -> tuple[list[Fairway], dict[str, str]]:
    """Every fairway with a deck log, in name order, and a line for each log that could not be read."""
    found: list[Fairway] = []
    faults: dict[str, str] = {}
    for path in deck_logs(root):
        entries, fault = read_log(path)
        if fault:
            faults[path.stem] = fault
        found.append(Fairway(path.stem, path.parent.name, entries))
    return found, faults


def harbour_log(root: Path) -> list[Entry]:
    """Every machine's harbour log, folded into one by the instant each line records.

    A board that read one machine's would show one machine's harbour and say nothing about the others,
    which is the failure mode the per-machine split exists to avoid rather than create. A log that cannot
    be read is skipped with its fault reported the way a deck log's is — one machine's broken file must not
    blank the board for all of them.
    """
    found: list[Entry] = []
    for path in harbour_logs(root):
        found.extend(read_log(path, harbour=True)[0])
    return sorted(found, key=lambda entry: entry.t)


def feed(found: list[Fairway], harbour: list[Entry], limit: int = FEED) -> list[tuple[str, str, str]]:
    """The last lines of both logs, merged by time. (when, who, what)."""
    lines = [(e.t, one.name, e.kind) for one in found for e in one.entries]
    lines += [(e.t, "harbour", e.kind) for e in harbour]
    return sorted(lines)[-limit:]


def spent(found: list[Fairway]) -> int | None:
    """Thousands of input tokens the whole harbour has recorded, or None where nothing records any."""
    counted = [one.tokens for one in found if one.tokens is not None]
    return sum(counted) if counted else None


def pressure(config: dict, harbour: list[Entry]) -> dict[str, object]:
    """Where the telegraph is, and what it has lit. Read from the file, with the log's own last word on it."""
    at = str(config.get("position", "unset"))
    banked = next((e for e in reversed(harbour) if e.kind == "fires-banked"), None)
    return {
        "position": at,
        "boilers": config.get("boilers", NOTHING),
        "fanout": config.get("fanout", NOTHING),
        "bunker_per_day": config.get("bunker_per_day", NOTHING),
        "banked": str(banked.fields.get("why", "")) if banked else "",
    }


def berths(found: list[Fairway], bound: float = STALL_MINUTES,
           now: datetime | None = None) -> list[dict[str, object]]:
    """The berth table: one row per fairway, each saying what it is on and when it last said anything."""
    rows: list[dict[str, object]] = []
    for one in found:
        since = minutes_since(one.last, now)
        rows.append({
            "fairway": one.name,
            "feature": one.feature,
            "slice": one.slice_now or NOTHING,
            "state": state_of(one, bound, now),
            "last": f"{since:.0f}m ago" if since is not None else NOTHING,
            "tokens": one.tokens if one.tokens is not None else NOTHING,
            "merged": len(one.merged),
            "marks": len(one.marks),
        })
    return rows


def inbox(found: list[Fairway]) -> list[dict[str, str]]:
    """Every open message and every park: the things waiting on a person, which is what a board is read for."""
    waiting: list[dict[str, str]] = []
    for one in found:
        waiting += [{"fairway": one.name, "kind": "told", "what": str(e.fields.get("message", "")), "t": e.t}
                    for e in one.unanswered]
        if one.parked:
            waiting.append({"fairway": one.name, "kind": "parked", "what": one.parked, "t": one.last})
    return sorted(waiting, key=lambda row: row["t"])


def board(root: Path, config: dict | None = None, now: datetime | None = None) -> dict[str, object]:
    """Everything the board shows, folded from the logs. Nothing here is stored anywhere."""
    found, faults = fairways(root)
    harbour = harbour_log(root)
    held = config or {}
    bound = float(held.get("wait_bound", STALL_MINUTES) or STALL_MINUTES)
    return {
        "berths": berths(found, bound, now),
        # Each stream's own lines, said rather than printed. The board answers "is anything stuck"; the
        # next question is always "what has this one been doing", and that is forty lines of one file.
        "streams": {one.name: recent(root, one.name)[0] for one in found},
        "pressure": pressure(held, harbour),
        "bunker": {"spent": spent(found), "allowed": held.get("bunker_per_day", NOTHING)},
        "inbox": inbox(found),
        "feed": feed(found, harbour),
        "unreadable": faults,
    }
