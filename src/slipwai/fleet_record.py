"""What the board says about a park's record and the fleet's processes, folded from the same logs.

Split from `fleet.py` at its budget. `fleet.py` folds the streams; this folds what the fleet-status plan
added on top of them: a park's needs with their ticks, the parks grouped by what they wait on, the numbers
under the headline, and each process with its own word on why it left. Nothing is kept here either.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .logs import Entry, paused
from .process_alive import alive


class Stream(Protocol):
    """What this reads off a fairway: `fleet.Fairway` is one, and naming the shape rather than the class
    keeps the two modules from importing each other."""

    name: str

    @property
    def parks(self) -> list[Entry]: ...

    @property
    def merged(self) -> list[str]: ...

    @property
    def asked(self) -> list[Entry]: ...

    @property
    def paused(self) -> str: ...

    @property
    def parked(self) -> str: ...

    def at_work(self, bound: float = ..., now: datetime | None = ...) -> list[str]: ...

    def queued(self, bound: float = ..., now: datetime | None = ...) -> list[str]: ...

#: Minutes since the last line after which a berth that has not finished is drawn as stalled. The default
#: where `harbour.json` says nothing: a wait with no bound is indistinguishable from a run that has stopped.
STALL_MINUTES = 15
#: How many lines the event feed carries. Enough to see what a stage did, short enough to read.
FEED = 40
#: What a column says where the log says nothing. Not `0`: a number nobody wrote is not a number that is zero.
NOTHING = "—"


def clock_of(until: str) -> str:
    """An instant from the log as a person reads a clock on this machine, `21:40`; the instant itself
    where it is not one this can read, and `""` for nothing."""
    if not until:
        return ""
    try:
        when = datetime.strptime(until, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return until
    return when.astimezone().strftime("%H:%M")


def need_rows(park: Entry, met: set[int]) -> list[dict[str, str]]:
    """A park's needs as the board draws them: what, who ticks it, how the fleet would, and whether it is."""
    needs = park.fields.get("needs")
    rows: list[dict[str, str]] = []
    for index, need in enumerate(needs if isinstance(needs, list) else []):
        if not isinstance(need, dict):
            continue
        held = need.get("check")
        check: dict = held if isinstance(held, dict) else {}
        how = ""
        if check.get("kind") == "text":
            how = f"{check.get('path', '')} holds {str(check.get('has', ''))!r}"
        elif check.get("kind") == "make":
            how = f"make {check.get('target', '')} passes on trunk"
        rows.append({"what": str(need.get("what", "")), "by": str(need.get("by", "person")), "how": how,
                     "met": "yes" if index in met else "no", "index": str(index)})
    return rows


#: The causes whose parks are one thing to a person however many slices stand on them: a limit lifts for all
#: of them at once, and the same list of needs on trunk is the same list however many times it was written.
#: A question, a missed gate, a crash is its own slice's and is not folded into a sibling's.
GROUPED = ("limit", "host", "ceiling", "trunk", "budget")


def groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The parks waiting on a person, folded by what they wait on rather than listed by slice.

    recap had eleven parks under *Waiting on you*: eight were one session limit and three were one change
    to trunk. A person reading eleven paragraphs found that out by reading them. A group is one cause and,
    for a change on trunk, one list of needs; it carries every slice standing on it, the ticks, the latest
    `until`, the `then` the newest park wrote, and the parks themselves for whatever answers them.
    """
    keyed: dict[tuple, dict[str, Any]] = {}
    for row in rows:
        if row.get("kind") != "parked" and not (row.get("kind") == "told" and row.get("needs")):
            continue
        cause = str(row.get("cause") or "other")
        key: tuple
        if row.get("kind") == "told":
            # A hand-back with needs: one change on trunk, grouped by what it asks for, like a host park.
            key = ("told", tuple(need["what"] for need in row.get("needs") or []))
        elif cause not in GROUPED:
            key = (cause, row["fairway"], row["t"], str(row.get("slice") or ""))
        elif cause == "limit":
            key = ("limit",)
        else:
            key = (cause, tuple(need["what"] for need in row.get("needs") or []))
        held = keyed.setdefault(key, {"kind": "group", "cause": cause, "slices": [], "fairways": [], "parks": [],
                                      "needs": [dict(need) for need in row.get("needs") or []],
                                      "t": row["t"], "until": "", "then": "", "what": "", "paused": "yes",
                                      "source": str(row.get("kind"))})
        held["slices"].append(str(row.get("slice") or row["fairway"]))
        if row["fairway"] not in held["fairways"]:
            held["fairways"].append(row["fairway"])
        held["parks"].append({"fairway": row["fairway"], "t": row["t"], "slice": str(row.get("slice") or "")})
        held["t"] = min(held["t"], row["t"])
        held["until"] = max(held["until"], str(row.get("until") or ""))
        if row["t"] >= max(park["t"] for park in held["parks"]):
            held["then"], held["what"] = str(row.get("then") or ""), str(row.get("what") or "")
            held["lines"] = row.get("lines") or []
        for mine, theirs in zip(held["needs"], row.get("needs") or [], strict=False):
            if theirs.get("met") == "yes":
                mine["met"] = "yes"
        if row.get("paused") != "yes":
            held["paused"] = "no"
    found = sorted(keyed.values(), key=lambda one: (one["paused"] == "yes", one["t"]))
    for one in found:
        one["clock"] = clock_of(one["until"])
        one["met"] = sum(1 for need in one["needs"] if need.get("met") == "yes")
    return found


#: Where `fleet.start` records what it started: `<name>.pid`, its output in `<name>.out`, and — since the
#: captain writes one — `<name>.exit`, the process's own word on why it left.
RUNNING = ".slipwai/running"


def processes(root: Path, found: Sequence[Stream], now: datetime | None = None) -> list[dict[str, str]]:
    """Every process the fleet has, or should have: the harbourmaster and one captain per stream.

    Each row says whether it is running, since when, why it left where it did, and what would start it —
    the question recap's person could not answer at 09:00, when a restart lit two captains that each read
    the standing parks and left within a second. `state` is `running`, `exited` or `not lit`; `why` is the
    `.exit` file the captain wrote; `starts_when` is read off the stream's own log, which is what the next
    captain lit for it would read.
    """
    place = root / RUNNING
    rows: list[dict[str, str]] = []
    streams = {one.name: one for one in found}
    names = ["harbourmaster", *(f"captain-{one.name}" for one in found)]
    for path in sorted(place.glob("captain-*.pid")) if place.is_dir() else []:
        if path.stem not in names and "--" not in path.stem:
            names.append(path.stem)
    for name in names:
        fairway = name.removeprefix("captain-") if name != "harbourmaster" else ""
        pid_file, exit_file = place / f"{name}.pid", place / f"{name}.exit"
        pid = 0
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip()) if pid_file.is_file() else 0
        except (OSError, ValueError):
            pid = 0
        live = pid > 0 and alive(pid)
        why, at = "", ""
        if not live and exit_file.is_file():
            try:
                said = json.loads(exit_file.read_text(encoding="utf-8"))
                why, at = str(said.get("why", "")), str(said.get("at", ""))
            except (OSError, ValueError, AttributeError):
                why = ""
        since = ""
        if pid_file.is_file():
            try:
                since = datetime.fromtimestamp(pid_file.stat().st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            except OSError:
                since = ""
        state = "running" if live else ("exited" if pid else "not lit")
        rows.append({"name": name, "role": "harbourmaster" if not fairway else "captain", "fairway": fairway,
                     "state": state, "since": since if live else (at or since), "why": why,
                     "starts_when": "" if live else starts_when(fairway, streams.get(fairway), why)})
    return rows


def starts_when(fairway: str, stream: Stream | None, why: str) -> str:
    """What would start this process again, in one sentence read off the stream's log."""
    if not fairway:
        return "the fleet is started again"
    if stream is not None and stream.paused:
        lifts = clock_of(stream.paused) if stream.paused != "soon" else ""
        return f"the pause ends at {lifts}" if lifts else "the harness runs sessions again"
    if stream is not None and stream.parked:
        return "one of its parks is cleared"
    if "nothing to start" in why:
        _, _, tail = why.partition(" — ")
        return f"something becomes startable (now {tail})" if tail else "something becomes startable"
    if "paused until" in why:
        return "the pause ends"
    return "the fleet is lit again"


def counts(found: Sequence[Stream], config: dict, bound: float = STALL_MINUTES,
           now: datetime | None = None) -> dict[str, object]:
    """The numbers under the headline: what is running, what waits for a slot, what is paused, what is
    parked on a person, what has merged, and how many may run at once. From the logs, like every column."""
    running = sum(len(one.at_work(bound, now)) for one in found)
    queued = sum(len(one.queued(bound, now)) for one in found)
    resting = sum(len(paused(one.parks)) for one in found)
    parked = sum(len(one.parks) for one in found) - resting
    boilers = config.get("boilers")
    return {"slots": boilers if isinstance(boilers, int) and not isinstance(boilers, bool) else NOTHING,
            "running": running, "queued": queued, "paused": resting, "parked": parked,
            "merged": sum(len(one.merged) for one in found),
            "questions": sum(len(one.asked) for one in found)}
