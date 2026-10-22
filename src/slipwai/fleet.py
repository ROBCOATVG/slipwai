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
# budget: 495 — every column of the board folded from the logs, including what waits on a person: a park,
# a told, the decisions nobody has read, and a question a headless stage posted and nobody has answered
# yet, beside a stream that was stopped and the several slices one stream now has in flight at once, and
# which `told` an answer or a claim has already taken up, which one is a session's note for another session
# rather than for the person, and whether unread decisions hold anything up
# and which slices in flight a session is on now, and which are claimed and waiting for a slot, and the
# lines of its own slice each park opens onto
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .deck import recent, said
from .logs import (
    Entry,
    Unreadable,
    cause_of,
    deck_logs,
    fairway_parks,
    fold,
    harbour_logs,
    held_slices,
    open_parks,
    paused,
    unmerged,
)
from .process_alive import alive
from .shell_environment import login_environment

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
    receipts: list[Entry] = field(default_factory=list)

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
        """Why the stream is parked: a park of the whole fairway, or slices parked on their own with nothing
        else of it in flight. One slice parked while its siblings run is a stream that is working."""
        parks = self.parks
        whole = fairway_parks(parks)
        if whole:
            return str(whole[-1].fields["why"])
        return str(parks[-1].fields["why"]) if parks and not self.slices_now else ""

    @property
    def parks(self) -> list[Entry]:
        return open_parks(self.entries, self.receipts, self.name)

    @property
    def paused(self) -> str:
        """The latest `until` of the parks that make this stream parked, where every one of them lifts by
        itself — a limit, or a time still ahead — and `""` where any of them waits on a person or the stream
        is not parked at all. One slice on a person beside seven on the harness is a stream on a person."""
        if not self.parked:
            return ""
        parks = self.parks
        whole = fairway_parks(parks)
        held = whole or parks
        lifting = paused(held)
        if len(lifting) != len(held):
            return ""
        return max((str(e.fields.get("until") or "") for e in lifting), default="") or "soon"

    def needs_met(self, park: Entry) -> set[int]:
        """Which of a park's needs have been ticked: a `need-met` receipt from the harbourmaster, or a
        person's `need-done` line the harbourmaster has not carried yet."""
        found = {int(e.fields.get("need", -1)) for e in self.receipts
                 if e.kind == "need-met" and str(e.fields.get("fairway", "")) == self.name
                 and str(e.fields.get("parked", "")) == park.t}
        found |= {int(e.fields.get("need", -1)) for e in self.entries
                  if e.kind == "need-done" and str(e.fields.get("parked", "")) == park.t}
        return found

    @property
    def slice_now(self) -> str:
        """The slice being worked: the last claimed that has not merged."""
        merged = set(self.merged)
        return next((one for one in reversed(self.claimed) if one not in merged), "")

    @property
    def slices_now(self) -> list[str]:
        """Every slice in flight — claimed, not merged, and not parked on its own — in the order claimed. A
        captain runs several of a stream's slices at once now, and a board that named the last of them
        drew the rest as nothing."""
        held = held_slices(self.parks)
        return [one for one in unmerged(self.entries) if one not in held]

    def at_work(self, bound: float = STALL_MINUTES, now: datetime | None = None) -> list[str]:
        """The slices in flight that a session is actually on: a line naming the slice — its `claimed`, a
        `heartbeat` the captain writes every minute while the session runs, a mark — within the stall bound.

        A claimed slice is carried on until it merges, so a fairway held to three abreast with seven claimed
        has four that are waiting for a slot and writing nothing. hr-test-2 drew all seven as working while
        only three had a session, and the slice nearest its merge was one of the four sitting idle.
        """
        heard: dict[str, str] = {}
        for entry in self.entries:
            named = str(entry.fields.get("slice", "") or "")
            if named:
                heard[named] = entry.t
        fresh = []
        for one in self.slices_now:
            since = minutes_since(heard.get(one, ""), now)
            if since is not None and since <= bound:
                fresh.append(one)
        return fresh

    def queued(self, bound: float = STALL_MINUTES, now: datetime | None = None) -> list[str]:
        """The slices in flight no session is on now: claimed, waiting for a slot to be carried on."""
        busy = set(self.at_work(bound, now))
        return [one for one in self.slices_now if one not in busy]

    @property
    def last(self) -> str:
        return self.entries[-1].t if self.entries else ""

    @property
    def tokens(self) -> int | None:
        """Thousands of input tokens this fairway's lines record, or None where none of them record any."""
        found = [e.fields["tokens"] for e in self.entries if isinstance(e.fields.get("tokens"), int | float)]
        return int(sum(found)) if found else None

    @property
    def asked(self) -> list[Entry]:
        """Every `question` no `decision` has answered by `id`. A headless `/launch` posts the chart's context
        question for a person and proceeds; a board showing only `told` and `parked` drew that as nothing."""
        answered = {str(e.fields.get("id", "")) for e in self.entries if e.kind == "decision"}
        return [e for e in self.entries if e.kind == "question" and str(e.fields.get("id", "")) not in answered]

    @property
    def unreviewed(self) -> list[Entry]:
        """Every `decision` a person has not read: no `read` names its instant, and no person took it. The
        rule `inbox.py` holds the ceiling to, so what the board offers to mark read is what the ceiling counts."""
        receipts = {str(e.fields["told"]) for e in self.entries if e.kind == "read"}
        return [e for e in self.entries if e.kind == "decision" and e.fields.get("decided_by") != "human"
                and e.t not in receipts]

    @property
    def unanswered(self) -> list[Entry]:
        """Every `told` nothing has answered: no `read` names it, no `decision` came after it, and it was not
        a person's answer to a park the captain has since taken up by claiming work again.

        A `read` receipt was the only way off this list and nothing wrote one, so every `go` and `decide for
        me` a person ever sent stayed under *Waiting on you* — and turned the Slices step red with "make
        cruise-tell answers a park" while the fleet ran and nothing was parked.
        """
        receipts = {str(e.fields["told"]) for e in self.entries if e.kind == "read"}
        found: list[Entry] = []
        parked = False
        for index, entry in enumerate(self.entries):
            if entry.kind == "parked":
                parked = True
            elif entry.kind == "claimed":
                parked = False
            if entry.kind != "told" or entry.t in receipts or for_someone_else(entry):
                continue
            later = self.entries[index + 1:]
            if any(e.kind == "decision" for e in later):
                continue
            if parked and any(e.kind == "claimed" for e in later):
                continue
            found.append(entry)
        return found


#: How a session addresses a note: `For the host, from L03's captain: …`, `For L02's captain, from L06's: …`.
ADDRESSED = re.compile(r"^\s*for\s+([^:,]{1,60})[:,]", re.IGNORECASE)


def for_someone_else(entry: Entry) -> bool:
    """A note one session left for another — `For the captain: …`, `For L02's captain, from L06's: …`.

    Sessions in berths abreast talk to each other through the deck log, because it is the one thing they
    share, and every such line sat under *Waiting on you* and turned the Slices step red while three
    slices ran with nothing blocked. Only a session's line is read for an address, and only one addressed
    to somebody other than the host is left out: an unaddressed note is still shown, because a note for
    the person that is missed costs more than one that is shown and dismissed.
    """
    if entry.fields.get("by") == "person":
        return False
    addressed = ADDRESSED.match(str(entry.fields.get("message", "")))
    if addressed is None:
        return False
    return not re.match(r"the\s+(host|person|human|owner)\b", addressed.group(1).strip(), re.IGNORECASE)


def minutes_since(stamp: str, now: datetime | None = None) -> float | None:
    """Minutes since an ISO instant, or None where it is not one this can read."""
    try:
        when = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None
    return ((now or datetime.now(UTC)) - when).total_seconds() / 60.0


def state_of(fairway: Fairway, bound: float = STALL_MINUTES, now: datetime | None = None,
             waiting: int | None = 0) -> str:
    """One word for what this fairway is doing, and `stalled` is the one that has to be earned.

    `finished` and `stalled` look identical in a status field — neither is writing anything — and they are
    the two it matters most to tell apart. The last line tells them apart for nothing.
    """
    if not fairway.entries:
        return "not started"
    if fairway.parked:
        # Paused is parked on nobody: the harness said when it would run again, and the harbourmaster
        # lifts the park at that time. The word on the board has to say that nothing here needs a person.
        return "paused" if fairway.paused else "parked"
    last = fairway.entries[-1]
    if last.kind == "stopped":
        # Asked to stop and said so. Not `stalled`, which is a captain that went quiet without a word, and
        # not `parked`, which waits on a person: lighting the fleet again carries the slice on.
        return "stopped"
    if last.kind == "merged" and not fairway.slices_now:
        if waiting is None:
            return "unknown"
        return "idle" if waiting else "finished"
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


def fairways(root: Path, receipts: list[Entry] | None = None) -> tuple[list[Fairway], dict[str, str]]:
    """Every fairway with a deck log, in name order, and a line for each log that could not be read."""
    receipts = harbour_log(root) if receipts is None else receipts
    found: list[Fairway] = []
    faults: dict[str, str] = {}
    for path in deck_logs(root):
        entries, fault = read_log(path)
        if fault:
            faults[path.stem] = fault
        found.append(Fairway(path.stem, path.parent.name, entries, receipts))
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
        "browsers": config.get("browsers", NOTHING),
        "bunker_per_day": config.get("bunker_per_day", NOTHING),
        "banked": str(banked.fields.get("why", "")) if banked else "",
    }


def berths(found: list[Fairway], bound: float = STALL_MINUTES,
           now: datetime | None = None, ready: dict[tuple[str, str], list[str]] | None = None,
           clearance_faults: set[str] | None = None) -> list[dict[str, object]]:
    """The berth table: one row per fairway, each saying what it is on and when it last said anything."""
    rows: list[dict[str, object]] = []
    for one in found:
        since = minutes_since(one.last, now)
        pending = [slice_id for slice_id in (ready or {}).get((one.feature, one.name), [])
                   if slice_id not in set(one.claimed) | set(one.merged)]
        count = None if one.feature in (clearance_faults or set()) else len(pending)
        parks = one.parks
        lifting = paused(parks)
        rows.append({
            "fairway": one.name,
            "feature": one.feature,
            "slice": ", ".join(one.at_work(bound, now)) or NOTHING,
            "queued": ", ".join(one.queued(bound, now)) or NOTHING,
            "state": state_of(one, bound, now, count),
            "waiting": count if count is not None else NOTHING,
            "last": f"{since:.0f}m ago" if since is not None else NOTHING,
            "tokens": one.tokens if one.tokens is not None else NOTHING,
            "merged": len(one.merged),
            "marks": len(one.marks),
            # The parks split by who lifts them: the harbourmaster, at a time, or a person.
            "paused": len(lifting),
            "parked": len(parks) - len(lifting),
            "until": clock_of(one.paused) if one.paused and one.paused != "soon" else "",
        })
    return rows


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
        if row.get("kind") != "parked":
            continue
        cause = str(row.get("cause") or "other")
        if cause not in GROUPED:
            key: tuple = (cause, row["fairway"], row["t"], str(row.get("slice") or ""))
        elif cause == "limit":
            key = ("limit",)
        else:
            key = (cause, tuple(need["what"] for need in row.get("needs") or []))
        held = keyed.setdefault(key, {"kind": "group", "cause": cause, "slices": [], "fairways": [], "parks": [],
                                      "needs": [dict(need) for need in row.get("needs") or []],
                                      "t": row["t"], "until": "", "then": "", "what": "", "paused": "yes"})
        held["slices"].append(str(row.get("slice") or row["fairway"]))
        if row["fairway"] not in held["fairways"]:
            held["fairways"].append(row["fairway"])
        held["parks"].append({"fairway": row["fairway"], "t": row["t"], "slice": str(row.get("slice") or "")})
        held["t"] = min(held["t"], row["t"])
        held["until"] = max(held["until"], str(row.get("until") or ""))
        if row["t"] >= max(park["t"] for park in held["parks"]):
            held["then"], held["what"] = str(row.get("then") or ""), str(row.get("what") or "")
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


#: How many of a park's own lines its drawer on the board shows.
DRAWER = 20


def inbox(found: list[Fairway], bound: float = STALL_MINUTES, now: datetime | None = None,
          ceiling: int | None = None) -> list[dict[str, Any]]:
    """Every open message, question and park: the things waiting on a person, which is what a board is for.

    Unread decisions are listed for reading, and say whether they hold anything up: `blocking` is `yes` only
    past the decision ceiling, where the captain parks. Below it they are a thing to read, not a wait, and
    the Slices step reads them that way."""
    waiting: list[dict[str, Any]] = []
    for one in found:
        waiting += [{"fairway": one.name, "kind": "told", "what": str(e.fields.get("message", "")), "t": e.t}
                    for e in one.unanswered]
        waiting += [{"fairway": one.name, "kind": "question",
                     "what": f"{e.fields.get('id')} ({e.fields.get('slice')}): {e.fields.get('what')}", "t": e.t}
                    for e in one.asked]
        if one.unreviewed:
            # One row per stream, not one per decision: twenty decisions are one thing a person sits down
            # to read, and twenty rows would bury the park that is waiting behind them.
            over = ceiling is not None and len(one.unreviewed) > ceiling
            waiting.append({"fairway": one.name, "kind": "decisions", "t": one.unreviewed[0].t,
                            "what": f"{len(one.unreviewed)} decision(s) nobody has read yet"
                                    + (f", over the ceiling of {ceiling}" if over else ""),
                            "blocking": "yes" if over else "no",
                            "decisions": [{"t": e.t, "id": str(e.fields.get("id", "")),
                                           "what": str(e.fields.get("what", ""))} for e in one.unreviewed]})
        lifting = paused(one.parks)
        for park in one.parks:
            waited = minutes_since(park.t, now)
            named = str(park.fields.get("slice") or "")
            # The drawer under a park is that slice's own story. The fairway's tail with three slices
            # running was every other slice's heartbeats, which drew a parked L04 as if it were going.
            own = [e for e in one.entries if e.kind != "heartbeat"
                   and (not named or str(e.fields.get("slice") or "") == named)]
            # Waiting on you: the harbourmaster only writes the receipt once a person has answered — or,
            # for a park that lifts by itself, once its time comes, which is `paused` and not a wait on you.
            resting = park in lifting
            waiting.append({"fairway": one.name, "kind": "parked", "what": str(park.fields["why"]),
                            "t": park.t, "waited": f"{max(0.0, waited):.0f}m" if waited is not None else NOTHING,
                            "slice": named, "lines": [(e.t, said(e)) for e in own[-DRAWER:]],
                            "waiting_on": "the harness" if resting else "you",
                            "overdue": "yes" if waited is not None and waited > bound and not resting else "no",
                            # The record, where the park carries one: see `logs.OPTIONAL`.
                            "cause": cause_of(park), "until": str(park.fields.get("until") or ""),
                            "then": str(park.fields.get("then") or ""),
                            "needs": need_rows(park, one.needs_met(park)),
                            "paused": "yes" if resting else "no"})
    return sorted(waiting, key=lambda row: row["t"])


#: Where `fleet.start` records what it started: `<name>.pid`, its output in `<name>.out`, and — since the
#: captain writes one — `<name>.exit`, the process's own word on why it left.
RUNNING = ".slipwai/running"


def processes(root: Path, found: list[Fairway], now: datetime | None = None) -> list[dict[str, str]]:
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


def starts_when(fairway: str, stream: Fairway | None, why: str) -> str:
    """What would start this process again, in one sentence read off the stream's log."""
    if not fairway:
        return "the fleet is started"
    if stream is not None and stream.paused:
        lifts = clock_of(stream.paused) if stream.paused != "soon" else ""
        return f"the pause ends at {lifts}" if lifts else "the harness runs sessions again"
    if stream is not None and stream.parked:
        return "a park is cleared"
    if "nothing to start" in why:
        _, _, tail = why.partition(" — ")
        return f"a slice may start; now {tail}" if tail else "a slice may start"
    if "paused until" in why:
        return "the pause ends"
    return "the fleet is lit"


def counts(found: list[Fairway], config: dict, bound: float = STALL_MINUTES,
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


def inbox_detail(row: dict) -> str:
    """The same wait clock in the terminal, page and agent inbox, with the age visible first."""
    if not row.get("waited"):
        return str(row["what"])
    if row.get("paused") == "yes":
        lifts = clock_of(str(row.get("until") or ""))
        return f"paused{' until ' + lifts if lifts else ''}, nothing needed from you: {row['what']}"
    overdue = " (past wait bound)" if row.get("overdue") == "yes" else ""
    return f"waiting on {row['waiting_on']} for {row['waited']}{overdue}: {row['what']}"


def clearance_ready(root: Path, feature: str = "") -> tuple[str, dict[str, list[str]], str]:
    """The ready set, by fairway: the one answer the berth table needs out of the clearance query."""
    feature, result, fault = clearance_query(root, feature)
    if fault or not result:
        return feature, {}, fault
    ready = result.get("ready")
    if not isinstance(ready, dict) or any(not isinstance(ids, list) for ids in ready.values()):
        return feature, {}, "clearance returned no ready set"
    return feature, {str(f): [str(s) for s in ids] for f, ids in ready.items()}, ""


def project_python() -> str:
    """The interpreter the project's own scripts run under: the `python3` the login shell finds, which is the
    one `./init` installed PyYAML into — not this process's, which is the keel's own environment and reads
    no YAML by design. The keel's as a fallback, so a machine with no other python still gets an answer.
    The walk is spelled out rather than borrowed from `shutil.which`, which a suite elsewhere stands in for."""
    import os

    for directory in (login_environment().get("PATH") or "").split(os.pathsep):
        candidate = Path(directory) / "python3"
        if directory and candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return sys.executable


def clearance_query(root: Path, feature: str = "") -> tuple[str, dict, str]:
    """Read the project's existing clearance rule through its offline JSON port, never duplicate it: the
    whole answer — the ready set, every slice's state, the schedule — and a fault where it could not be."""
    charts = [path for path in sorted((root / "specs").glob("*/chart.yaml"))
              if not feature or path.parent.name == feature]
    if not charts:
        return feature, {}, ""
    feature = charts[0].parent.name
    try:
        manifest = json.loads((root / "project.json").read_text(encoding="utf-8"))
        delivery = str((manifest.get("layout") or {}).get("delivery") or ".")
    except (OSError, ValueError, UnicodeDecodeError, AttributeError):
        delivery = "."
    script = root / delivery / "scripts/agents/clearance.py"
    if not script.resolve().is_relative_to(root.resolve()) or not script.is_file():
        return feature, {}, ("the project's clearance script is missing or outside the checkout. "
                             "Run `slipwai migrate` to restore it")
    try:
        parsed = ast.parse(script.read_text(encoding="utf-8"))
        supported = any(isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "QUERY_VERSION" for target in node.targets)
            and isinstance(node.value, ast.Constant) and node.value.value == 1 for node in parsed.body)
        if not supported:
            return feature, {}, ("the project's clearance script has no offline JSON query port. "
                                 "Run `slipwai migrate` to update it")
        done = subprocess.run([project_python(), "-B", str(script.resolve()), "--json", "--feature", feature],
                              capture_output=True, text=True, timeout=15, env=login_environment())
        try:
            result = json.loads(done.stdout)
        except ValueError as fault:
            raise ValueError((done.stderr or done.stdout).strip() or str(fault)) from None
        if not isinstance(result, dict) or result.get("v") != 1:
            raise ValueError("clearance returned no v1 object")
        if done.returncode != 0 or result.get("error"):
            return feature, {}, str(result.get("error") or done.stderr or "clearance query failed")
        if result.get("feature") != feature:
            raise ValueError(f"clearance returned {result.get('feature')!r} instead of {feature!r}")
        return feature, result, ""
    except (OSError, ValueError, SyntaxError, subprocess.TimeoutExpired) as fault:
        return feature, {}, (f"clearance could not be read ({fault}). Run "
                             f"`python3 {script} --json --feature {feature}` and repair the reported fault")


def ceiling_of(held: dict) -> int | None:
    """The decision ceiling the harbour runs to, or None where it says none a reader can use."""
    try:
        return int(held["decision_ceiling"])
    except (KeyError, TypeError, ValueError):
        return None


def board(root: Path, config: dict | None = None, now: datetime | None = None) -> dict[str, object]:
    """Everything the board shows, folded from the logs. Nothing here is stored anywhere."""
    harbour = harbour_log(root)
    found, faults = fairways(root, harbour)
    held = config or {}
    bound = float(held.get("wait_bound", STALL_MINUTES) or STALL_MINUTES)
    ready: dict[tuple[str, str], list[str]] = {}
    clearance_faults: set[str] = set()
    for chart in sorted((root / "specs").glob("*/chart.yaml")):
        feature, cleared, fault = clearance_ready(root, chart.parent.name)
        ready.update({(feature, fairway): slices for fairway, slices in cleared.items()})
        if fault:
            clearance_faults.add(feature)
            faults["clearance"] = str(faults.get("clearance", "")) + f"{feature}: {fault}\n"
    accepted = [str(e.fields["capability"]) for one in found for e in one.entries if e.kind == "accepted"]
    due = [str(e.fields["capability"]) for one in found for e in one.entries if e.kind == "demo-due"]
    waiting = inbox(found, bound, now, ceiling_of(held))
    return {
        "berths": berths(found, bound, now, ready, clearance_faults),
        # The parks folded by what they wait on, and the numbers under the headline: both from the same
        # rows the inbox lists one by one, so the two never disagree.
        "groups": groups(waiting),
        "counts": counts(found, held, bound, now),
        "processes": processes(root, found, now),
        # The acceptance facts, for the voyage's last stage: a demo owed is a capability due and not yet
        # accepted, and accepted is the only line a capability ends on.
        "accepted": sorted(set(accepted)),
        "demo_due": sorted(set(due) - set(accepted)),
        "demo_due_in": {str(e.fields["capability"]): one.name for one in found for e in one.entries  # whose
                        if e.kind == "demo-due" and str(e.fields["capability"]) not in accepted},
        # Each stream's own lines, said rather than printed. The board answers "is anything stuck"; the
        # next question is always "what has this one been doing", and that is forty lines of one file.
        "streams": {one.name: recent(root, one.name)[0] for one in found},
        "pressure": pressure(held, harbour),
        "bunker": {"spent": spent(found), "allowed": held.get("bunker_per_day", NOTHING)},
        "inbox": waiting,
        "feed": feed(found, harbour),
        "unreadable": faults,
    }
