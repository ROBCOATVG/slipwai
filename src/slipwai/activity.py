"""What each slice is doing now, read off the activity log its session's hooks write.

The voyage's columns say a slice is working and its chip says how far up the ladder; neither says what it is
doing this minute, which sub-agent is on it, or that it has spent fourteen minutes on a task its others took
six on. Every harness's session writes one line per thing that happened to `.slipwai/run/activity/<fairway>/
<slice>.jsonl` — `scripts/agents/session.py` from the harness's hooks, and the session itself for what only
it can say — so this reads one format whichever harness ran the slice, and never a harness's transcript.

**A line is a fact a person can read.** `start` and `done` bracket a sub-agent, `ran` and `failed` are a
command by the description its agent gave it, `edit` a file, `said` a sentence the session wrote for a
person, `wait` what it is about to wait on. The fold here is the slice's agents, its newest sentence, how
long it has been quiet, and the few patterns a person would step in for.

**Cheap enough for a poll.** The tail of each file only — a slice's log is rotated by its writer — and
nothing kept between polls but what the files say.
"""
from __future__ import annotations

import statistics
from pathlib import Path

from .logs import run_dir
from .stuck import (CIRCLE, KINDS, LAUNCH, LONG_FLOOR, QUIET, TAIL, agents_of, circling, minutes, now_stamp, stamp,
                    tail_lines, task_of, warnings)

__all__ = ["ACTIVITY", "CIRCLE", "KINDS", "LAUNCH", "LONG_FLOOR", "QUIET", "TAIL", "agents_of", "caption", "circling",
           "fold", "lines_of", "live", "log_path", "minutes", "newest", "now_stamp", "shared_waits", "stamp",
           "task_of"]

ACTIVITY = "activity"


def log_path(root: Path, fairway: str, slice_id: str) -> Path | None:
    """A slice's log, or nothing where the names would reach outside the folder."""
    home = (run_dir(root) / ACTIVITY).resolve()
    try:
        path = (home / fairway / f"{slice_id}.jsonl").resolve()
    except OSError:
        return None
    return path if path.is_relative_to(home) and fairway and slice_id else None


def lines_of(root: Path, fairway: str, slice_id: str) -> list[dict]:
    """The newest lines of one slice's log, oldest first. A line that is not a JSON object is skipped."""
    path = log_path(root, fairway, slice_id)
    return [] if path is None else tail_lines(path)


def fold(lines: list[dict], slice_id: str, now: float | None = None) -> dict:
    """One slice, now: its agents, the one running, its newest sentence, how long it has been quiet, and
    the warnings a person would act on (except the one that needs the other slices: `shared`). The
    warnings are `stuck.warnings`, which is what wakes the slice's captain too."""
    now = now_stamp() if now is None else now
    agents = agents_of(lines, slice_id, now)
    lines = [one for one in lines if one["kind"] != "link"]
    running = [one for one in agents if not one["ended"]]
    finished = [one["ended"] - one["started"] for one in agents if one["ended"]]
    said = next((one for one in reversed(lines) if one["kind"] == "said"), None)
    last = lines[-1] if lines else None
    waiting = last if last and last["kind"] == "wait" else None
    usual = statistics.median(finished) if finished else 0.0
    quiet = now - stamp(last["t"]) if last else 0.0
    current = running[-1] if running else None
    return {"slice": slice_id, "agents": agents, "running": running, "current": current,
            "said": str(said.get("what", "")) if said else "", "said_t": stamp(said["t"]) if said else 0.0,
            "waiting": str(waiting.get("what", "")) if waiting else "", "quiet": quiet,
            "last": str(last.get("what", "")) if last else "", "last_t": stamp(last["t"]) if last else 0.0,
            "warnings": warnings(lines, agents, now), "usual": usual}


def shared_waits(folds: list[dict]) -> None:
    """A slice waiting while another slice waits too: two slices queued on one machine's runs. Said on each."""
    waiting = [one for one in folds if one["waiting"]]
    for one in waiting:
        others = [other["slice"] for other in waiting if other is not one]
        if others:
            one["warnings"].append({"kind": "shared", "level": "red",
                                    "said": f"waiting on {one['waiting']} · {', '.join(others)} waiting too"})


def caption(found: dict, task: str = "") -> str:
    """The one line under a working slice's chip: what it is on, and how long ago it last did anything.

    What it is on is what it waits for, then the sub-agent's task, then the task its list says is next, then
    the newest sentence its session wrote for a person. Never its last command: `Read the berth memories
    about the database` is what an agent did a second ago, and a card that says so reads as where the slice
    is. The commands are the window's, a click away; here a slice with nothing better to say is `active`.
    """
    if not found["last_t"]:
        return ""
    current = found["current"]
    if found["waiting"]:
        head = f"waiting on {found['waiting']}"
    elif current and (current["task"] or current["what"]):
        head = " ".join(part for part in (current["task"], current["what"]) if part)
    else:
        head = task or found["said"] or (current["role"] if current else "") or "active"
    return f"{head} · {minutes(now_stamp() - found['last_t'])} ago"


#: What an opened card repeats from a slice's log: what was said, waited on or failed, a stage, a file — never
#: a command, which is a path and a pipe to a person and is the window's to show.
TOLD = ("said", "stage", "wait", "failed", "edit")


def newest(root: Path, fairway: str, slice_id: str, count: int = 3) -> list[dict]:
    """The last few things a slice's log says happened that a person can read, newest first."""
    told = [one for one in lines_of(root, fairway, slice_id) if one["kind"] in TOLD and one.get("what")]
    return [{"t": str(one["t"]), "kind": str(one["kind"]),
             "what": Path(str(one["what"])).name if one["kind"] == "edit" else str(one["what"])[:140]}
            for one in reversed(told[-count:])]


def live(root: Path, rows: list[dict[str, str]]) -> dict[str, dict]:
    """Every working slice's fold, keyed by fairway and slice, with the cross-slice warning added."""
    folds = {}
    for row in rows:
        if row.get("state") != "working" or not row.get("fairway"):
            continue
        lines = lines_of(root, row["fairway"], row["slice"])
        if lines:
            folds[f"{row['fairway']}/{row['slice']}"] = fold(lines, row["slice"])
    shared_waits(list(folds.values()))
    return folds
