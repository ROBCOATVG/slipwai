"""What each slice is doing now, read off the activity log its session's hooks write.

The voyage's columns say a slice is working and its chip says how far up the ladder; neither says what it is
doing this minute, which sub-agent is on it, or that it has spent fourteen minutes on a task its others took
six on. Every harness's session writes one line per thing that happened to `.slipwai/activity/<fairway>/
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

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path

ACTIVITY = ".slipwai/activity"
#: How much of a slice's log a poll reads: the newest lines are all a strip or a window shows.
TAIL = 256 * 1024
#: How long a slice may go without a line before the strip says it is quiet.
QUIET = 8 * 60
#: A sub-agent on one task this long, and past twice its slice's usual, is said to be taking long.
LONG_FLOOR = 10 * 60
#: The same command failing this many times running is an agent going round in circles.
CIRCLE = 3
KINDS = ("start", "done", "ran", "failed", "edit", "said", "wait", "link", "stage")


def stamp(text: str) -> float:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def now_stamp() -> float:
    return datetime.now(UTC).timestamp()


def log_path(root: Path, fairway: str, slice_id: str) -> Path | None:
    """A slice's log, or nothing where the names would reach outside the folder."""
    home = (root / ACTIVITY).resolve()
    try:
        path = (home / fairway / f"{slice_id}.jsonl").resolve()
    except OSError:
        return None
    return path if path.is_relative_to(home) and fairway and slice_id else None


def lines_of(root: Path, fairway: str, slice_id: str) -> list[dict]:
    """The newest lines of one slice's log, oldest first. A line that is not a JSON object is skipped."""
    path = log_path(root, fairway, slice_id)
    if path is None or not path.is_file():
        return []
    try:
        with path.open("rb") as held:
            size = held.seek(0, 2)
            held.seek(max(0, size - TAIL))
            raw = held.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    found = []
    for line in raw.splitlines()[1 if size > TAIL else 0:]:
        try:
            one = json.loads(line)
        except ValueError:
            continue
        if isinstance(one, dict) and one.get("kind") in KINDS and one.get("t"):
            found.append(one)
    return found


def task_of(what: str, slice_id: str) -> tuple[str, str]:
    """A brief like `L10 T018: R17 redraft confirm` as its task and its words: `T018`, `R17 redraft confirm`."""
    words = what.strip()
    if words.startswith(f"{slice_id} "):
        words = words[len(slice_id) + 1:]
    head, colon, rest = words.partition(":")
    if colon and head and " " not in head.strip():
        return head.strip(), rest.strip()
    return "", words


def agents_of(lines: list[dict], slice_id: str) -> list[dict]:
    """Every sub-agent the log saw start, with what it was given, when it ran and what it handed back.

    A sub-agent is started under the call that briefed it and works under the name the harness gave it, so
    a `link` line — the harness saying it started one of a type — ties the oldest unlinked start of that type
    to the name its own commands will carry. A harness that never says leaves the commands with the session."""
    agents: dict[str, dict] = {}
    alias: dict[str, str] = {}
    for one in lines:
        name = str(one.get("agent") or "")
        name = alias.get(name, name)
        if one["kind"] == "link" and name:
            waiting = [a for a in agents.values() if not a["ended"] and not a["linked"]
                       and a["role"] == str(one.get("role", ""))]
            if waiting:
                waiting[0]["linked"] = True
                alias[name] = waiting[0]["agent"]
            continue
        if one["kind"] == "done" and one.get("id"):
            alias.setdefault(str(one["id"]), name)
        if one["kind"] == "start" and name:
            task, words = task_of(str(one.get("what", "")), slice_id)
            agents[name] = {"agent": name, "role": str(one.get("role", "")), "model": str(one.get("model", "")),
                            "task": str(one.get("task") or task), "what": words, "started": stamp(one["t"]),
                            "ended": 0.0, "commit": "", "last": "", "last_t": stamp(one["t"]), "linked": False}
        elif one["kind"] == "done" and name in agents:
            agents[name].update(ended=stamp(one["t"]), commit=str(one.get("commit", "")))
        elif name in agents and one["kind"] in ("ran", "failed", "edit", "wait"):
            agents[name].update(last=str(one.get("what", "")), last_t=stamp(one["t"]))
    return sorted(agents.values(), key=lambda one: one["started"])


def circling(lines: list[dict]) -> str:
    """The command an agent has failed `CIRCLE` times running, or nothing."""
    by_agent: dict[str, list[dict]] = {}
    for one in lines:
        if one["kind"] in ("ran", "failed"):
            by_agent.setdefault(str(one.get("agent") or "session"), []).append(one)
    for runs in by_agent.values():
        tail = runs[-CIRCLE:]
        if len(tail) == CIRCLE and all(one["kind"] == "failed" for one in tail) \
                and len({str(one.get("what", "")) for one in tail}) == 1:
            return str(tail[-1].get("what", ""))
    return ""


def fold(lines: list[dict], slice_id: str, now: float | None = None) -> dict:
    """One slice, now: its agents, the one running, its newest sentence, how long it has been quiet, and
    the warnings a person would act on (except the one that needs the other slices: `shared`)."""
    now = now_stamp() if now is None else now
    agents = agents_of(lines, slice_id)
    lines = [one for one in lines if one["kind"] != "link"]
    running = [one for one in agents if not one["ended"]]
    finished = [one["ended"] - one["started"] for one in agents if one["ended"]]
    said = next((one for one in reversed(lines) if one["kind"] == "said"), None)
    last = lines[-1] if lines else None
    waiting = last if last and last["kind"] == "wait" else None
    warnings = []
    usual = statistics.median(finished) if finished else 0.0
    for one in running:
        took = now - one["started"]
        if took > LONG_FLOOR and usual and took > 2 * usual:
            warnings.append({"kind": "long", "level": "amber",
                             "said": f"{minutes(took)} on {one['task'] or 'one task'} · "
                                     f"its others took {minutes(usual)}"})
    loop = circling(lines)
    if loop:
        warnings.append({"kind": "circles", "level": "red", "said": f"failed {CIRCLE} times running: {loop}"})
    quiet = now - stamp(last["t"]) if last else 0.0
    if last and quiet > QUIET:
        warnings.append({"kind": "quiet", "level": "red", "said": f"nothing for {minutes(quiet)}"})
    current = running[-1] if running else None
    return {"slice": slice_id, "agents": agents, "running": running, "current": current,
            "said": str(said.get("what", "")) if said else "", "said_t": stamp(said["t"]) if said else 0.0,
            "waiting": str(waiting.get("what", "")) if waiting else "", "quiet": quiet,
            "last": str(last.get("what", "")) if last else "", "last_t": stamp(last["t"]) if last else 0.0,
            "warnings": warnings, "usual": usual}


def shared_waits(folds: list[dict]) -> None:
    """A slice waiting while another slice waits too: two slices queued on one machine's runs. Said on each."""
    waiting = [one for one in folds if one["waiting"]]
    for one in waiting:
        others = [other["slice"] for other in waiting if other is not one]
        if others:
            one["warnings"].append({"kind": "shared", "level": "red",
                                    "said": f"waiting on {one['waiting']} · {', '.join(others)} waiting too"})


def minutes(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h {seconds % 3600 // 60}m"


def caption(found: dict) -> str:
    """The one line under a working slice's chip: what it is on, and how long ago it last did anything."""
    if not found["last_t"]:
        return ""
    current = found["current"]
    if found["waiting"]:
        head = f"waiting on {found['waiting']}"
    elif current:
        head = " ".join(part for part in (current["task"], current["what"]) if part) or current["role"]
    else:
        head = found["said"] or found["last"]
    return f"{head} · {minutes(now_stamp() - found['last_t'])} ago" if head else ""


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
