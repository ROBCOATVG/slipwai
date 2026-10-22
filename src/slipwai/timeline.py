"""The voyage as a timeline: every session in its slot, every park and pause, and the marks between them.

What the recap voyage needed and nobody had was the picture: two red lines where the harness refused the
fleet, a cascade of parks after each, two triangles where a person cleared them by hand, and a long empty
evening after the reset nobody acted on. It took reading a 29 MB output file to draw it. This draws it from
the deck and harbour logs, which already hold every edge of every bar.

A **run** is a slice from its `claimed` to the line that ended it — its park, its merge, its stop, or a park
of the whole stream — and runs of one stream are packed into lanes, first fit, so a stream given three
slots draws three lanes. A **pause** is a park with `cause: limit` or an `until`: it sits in the lane of the
run it ended, from the park to the time it lifted or lifts. A **park** on a person is a thin bar in the
stream's own `parked on you` lane, from the park to its receipt or to now. The **marks** are the limit
refusals, the receipts a person wrote, now, and the time an open pause lifts.

Nothing is kept here. The window is whatever the page asks for; the page draws it at whatever scale the
person picks, because the bars are positions in the whole voyage and the scale is only how wide it is drawn.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .logs import Entry, cause_of, now

#: How long a run with no end in the log is drawn after the last line naming its slice: a session whose
#: captain died leaves no park, and a bar to the present would draw a dead session as a live one.
TRAIL_MINUTES = 15
#: Receipts the harbourmaster writes by itself, which are not a person's clear.
BY_RULE = ("its time came", "needs met:", "trunk is no longer red",
           "answered by decisions", "the decisions it waited on have been read")


class Stream(Protocol):
    name: str
    entries: list[Entry]
    receipts: list[Entry]


def instant(stamp: str) -> datetime | None:
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


def stamp(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def later(a: str, minutes: float) -> str:
    at = instant(a)
    return stamp(at + timedelta(minutes=minutes)) if at else a


def receipts_of(stream: Stream) -> dict[str, Entry]:
    """Each park's receipt, by the park's instant."""
    return {str(e.fields.get("parked", "")): e for e in stream.receipts
            if e.kind == "cleared" and str(e.fields.get("fairway", "")) == stream.name}


def runs_and_parks(stream: Stream, at_now: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The runs of this stream's slices, and its parks, each with a start and an end."""
    runs: list[dict[str, Any]] = []
    open_runs: dict[str, dict[str, Any]] = {}
    last_heard: dict[str, str] = {}
    parks: list[dict[str, Any]] = []
    answered = receipts_of(stream)

    def end_run(slice_id: str, at: str) -> None:
        run = open_runs.pop(slice_id, None)
        if run is not None:
            run["to"] = max(run["from"], at)

    for e in stream.entries:
        named = str(e.fields.get("slice") or "")
        if named:
            last_heard[named] = e.t
        if e.kind == "claimed" and named:
            end_run(named, e.t)
            open_runs[named] = {"slice": named, "kind": "run", "from": e.t, "to": ""}
            runs.append(open_runs[named])
        elif e.kind in ("merged", "stopped") and named:
            end_run(named, e.t)
        elif e.kind == "parked":
            cause = cause_of(e)
            until = str(e.fields.get("until") or "")
            receipt = answered.get(e.t)
            resting = cause == "limit" or until > e.t
            if named:
                end_run(named, e.t)
            else:
                for slice_id in list(open_runs):
                    end_run(slice_id, e.t)
            if resting:
                lifted = receipt.t if receipt is not None else (until if until and until > at_now else at_now)
                to = min(lifted, until) if until and receipt is None else lifted
                to = max(to, until) if until and receipt is None and until <= at_now else to
            else:
                to = receipt.t if receipt is not None else at_now
            parks.append({"slice": named, "kind": "pause" if resting else "park", "from": e.t,
                          "to": max(e.t, to), "cause": cause, "why": str(e.fields.get("why", "")), "until": until,
                          "open": receipt is None})
    for slice_id, run in open_runs.items():
        trail = later(last_heard.get(slice_id, run["from"]), TRAIL_MINUTES)
        run["to"] = min(trail, at_now)
    return runs, parks


def lanes_of(stream: Stream, runs: list[dict[str, Any]], parks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Runs packed into lanes, first fit, each pause in the lane of the run it ended; then one lane of the
    parks on a person, where there are any."""
    packed: list[list[dict[str, Any]]] = []
    ends: list[str] = []
    lane_of: dict[tuple[str, str], int] = {}
    for run in sorted(runs, key=lambda one: one["from"]):
        index = next((n for n, end in enumerate(ends) if end <= run["from"]), None)
        if index is None:
            packed.append([])
            ends.append("")
            index = len(packed) - 1
        packed[index].append(run)
        ends[index] = max(ends[index], run["to"])
        lane_of[(run["slice"], run["to"])] = index
    on_you: list[dict[str, Any]] = []
    for park in parks:
        if park["kind"] == "pause" and park["slice"]:
            index = lane_of.get((park["slice"], park["from"]))
            if index is not None:
                packed[index].append(park)
                ends[index] = max(ends[index], park["to"])
                continue
        on_you.append(park)
    lanes = [{"fairway": stream.name, "name": stream.name if len(packed) == 1 else f"{stream.name} · slot {n + 1}",
              "spans": spans} for n, spans in enumerate(packed)]
    if on_you:
        lanes.append({"fairway": stream.name, "name": f"{stream.name} · parked", "spans": on_you})
    if not lanes:
        lanes.append({"fairway": stream.name, "name": stream.name, "spans": []})
    return lanes


def marks_of(found: Sequence[Stream], parks: list[dict[str, Any]], at_now: str) -> list[dict[str, str]]:
    """The vertical lines: a limit refusal, a person's clear, now, and when an open pause lifts. One per
    minute per kind, because eight parks in one second are one refusal."""
    marks: dict[tuple[str, str], dict[str, str]] = {}
    for park in parks:
        if park["cause"] == "limit":
            marks.setdefault(("limit", park["from"][:16]), {"t": park["from"], "kind": "limit", "label": "limit"})
    for stream in found:
        for e in stream.receipts:
            if e.kind != "cleared" or str(e.fields.get("fairway", "")) != stream.name:
                continue
            what = str(e.fields.get("what", ""))
            if any(what.startswith(rule) for rule in BY_RULE):
                continue
            marks.setdefault(("person", e.t[:16]), {"t": e.t, "kind": "person", "label": "you cleared a park"})
    lifts = max((park["until"] for park in parks if park["open"] and park["kind"] == "pause" and park["until"]),
                default="")
    if lifts and lifts > at_now:
        marks[("reset", lifts)] = {"t": lifts, "kind": "reset", "label": "resumes"}
    marks[("now", at_now)] = {"t": at_now, "kind": "now", "label": "now"}
    return sorted(marks.values(), key=lambda one: one["t"])


def spans(found: Sequence[Stream], at_now: str = "") -> dict[str, Any]:
    """The whole voyage as lanes of spans and a list of marks, with the window they fall in."""
    at_now = at_now or now()
    lanes: list[dict[str, Any]] = []
    every_park: list[dict[str, Any]] = []
    for stream in found:
        runs, parks = runs_and_parks(stream, at_now)
        lanes += lanes_of(stream, runs, parks)
        every_park += parks
    marks = marks_of(found, every_park, at_now)
    starts = [span["from"] for lane in lanes for span in lane["spans"]] + [mark["t"] for mark in marks]
    ends = [span["to"] for lane in lanes for span in lane["spans"]] + [mark["t"] for mark in marks]
    begin = min(starts) if starts else at_now
    finish = max(ends) if ends else at_now
    # Round the window out to the hour either side, so the first bar is not on the left edge.
    opened = instant(begin)
    closed = instant(finish)
    if opened is not None:
        begin = stamp(opened.replace(minute=0, second=0))
    if closed is not None:
        finish = stamp((closed + timedelta(hours=1)).replace(minute=0, second=0))
    return {"from": begin, "to": finish, "now": at_now, "lanes": lanes, "marks": marks}
