"""Whether a slice is stuck, read off its activity log: taking long on one task, going in circles, gone quiet.

The board says so on a slice's card, and a stream's captain is woken by it, so both read one fold: this module,
which the keel's `activity.py` builds its strip from and which `scripts/shared-modules.py` carries into every
project for the captain. Two copies of "how long is quiet" would stop agreeing the first time one was tuned.

Pure, and the standard library only: a generated project has no slipwai to import.
"""
from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path

#: How much of a slice's log a poll reads: the newest lines are all a strip, a window or a captain needs.
TAIL = 256 * 1024
#: How long a slice may go without a line before it is said to be quiet.
QUIET = 8 * 60
#: A sub-agent on one task this long, and past twice its slice's usual, is said to be taking long.
LONG_FLOOR = 10 * 60
#: The same command failing this many times running is an agent going round in circles.
CIRCLE = 3
#: `plan` is a session's plan as its driver last heard it, over the Agent Client Protocol: one line a change.
KINDS = ("start", "done", "ran", "failed", "edit", "said", "wait", "link", "stage", "plan")
#: A `done` this soon after its `start`, before the harness has named the sub-agent, is the harness answering
#: the delegating call at once because it runs sub-agents in the background: a launch receipt, not an end.
LAUNCH = 5


def stamp(text: str) -> float:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def now_stamp() -> float:
    return datetime.now(UTC).timestamp()


def tail_lines(path: Path) -> list[dict]:
    """The newest lines of one activity log, oldest first. A line that is not a JSON object is skipped."""
    if not path.is_file():
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


def agents_of(lines: list[dict], slice_id: str, now: float | None = None) -> list[dict]:
    """Every sub-agent the log saw start, with what it was given, when it ran and what it handed back.

    A sub-agent is started under the call that briefed it and works under the name the harness gave it, so
    a `link` line — the harness saying it started one of a type — ties the oldest unlinked start of that type
    to the name its own commands will carry. A harness that never says leaves the commands with the session.

    A harness that runs sub-agents in the background answers the delegating call the second it is made, so
    its `done` under the call's name is the launch, and the one that counts is the `done` the harness writes
    under the sub-agent's own name when it stops. On a log with no such line — a harness that never says, or
    one written before the hook existed — a launched sub-agent that has gone quiet ended at its last line,
    and one still writing is still running."""
    now = now_stamp() if now is None else now
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
                            "ended": 0.0, "commit": "", "last": "", "last_t": stamp(one["t"]), "linked": False,
                            "launched": False}
        elif one["kind"] == "done" and name in agents:
            # The launch receipt: seconds after the start, before the sub-agent has done a thing. Whether the
            # harness named the sub-agent first or after is the order of two hooks in one second, not a fact.
            held = agents[name]
            ended = stamp(one["t"])
            quick = ended - held["started"] <= LAUNCH and held["last_t"] <= held["started"]
            held.update(ended=0.0 if quick else ended, launched=quick,
                        commit=str(one.get("commit", "")) or held["commit"])
        elif name in agents and one["kind"] in ("ran", "failed", "edit", "wait"):
            agents[name].update(last=str(one.get("what", "")), last_t=stamp(one["t"]))
    for held in agents.values():
        if held["launched"] and not held["ended"] and now - held["last_t"] > QUIET:
            held["ended"] = held["last_t"]
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


def minutes(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h {seconds % 3600 // 60}m"


def warnings(lines: list[dict], agents: list[dict], now: float) -> list[dict]:
    """The three a person — or a captain — would step in for: `long`, `circles`, `quiet`. `lines` without
    the `link` lines, `agents` as `agents_of` gave them."""
    found = []
    running = [one for one in agents if not one["ended"]]
    finished = [one["ended"] - one["started"] for one in agents if one["ended"]]
    usual = statistics.median(finished) if finished else 0.0
    for one in running:
        took = now - one["started"]
        if took > LONG_FLOOR and usual and took > 2 * usual:
            found.append({"kind": "long", "level": "amber",
                          "said": f"{minutes(took)} on {one['task'] or 'one task'} · its others took {minutes(usual)}"})
    loop = circling(lines)
    if loop:
        found.append({"kind": "circles", "level": "red", "said": f"failed {CIRCLE} times running: {loop}"})
    last = lines[-1] if lines else None
    quiet = now - stamp(last["t"]) if last else 0.0
    if last and quiet > QUIET:
        found.append({"kind": "quiet", "level": "red", "said": f"nothing for {minutes(quiet)}"})
    return found


def stuck(lines: list[dict], slice_id: str, now: float | None = None) -> list[dict]:
    """The warnings on one slice's log now: what wakes its captain."""
    now = now_stamp() if now is None else now
    return warnings([one for one in lines if one["kind"] != "link"], agents_of(lines, slice_id, now), now)
