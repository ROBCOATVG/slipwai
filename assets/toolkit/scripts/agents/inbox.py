#!/usr/bin/env python3
"""What a fairway owes a person at this boundary: messages unread, decisions unreviewed, waits overrun.

Three rules, and all three exist because the first attempt failed the same way three times: something was
true and nothing said so.

**Messages were documented and not read.** "Read the inbox between stages" was written in command prose, and
under load it did not happen — one of four instructions in MANDA that were documented and all failed. So a
message is answered with a `read` line carrying the `told` line's own timestamp. That is a receipt rather
than an assertion that somebody looked, and a `told` older than its bound with no receipt forces a boundary
rather than waiting for the next one to come round.

**Decisions outran review.** 125 decisions, 105 never read by a person, 8 ADRs still at Proposed. That is
not a record of judgement, it is a backlog of it, and nobody saw it accumulate because nothing counted. So
the count of unreviewed decisions is capped, and over the cap the fairway parks instead of deciding a
126th thing nobody has looked at.

**Waits had no bound.** A run waiting on a mark, a person or a lock looked exactly like a run that had
stopped, which is how seventeen iterations produced no log line and nobody noticed for a fortnight. So
every wait carries a bound and ends as a `parked` line with a reason.

    python3 scripts/agents/inbox.py ORD            # what this fairway owes at this boundary
    python3 scripts/agents/inbox.py ORD --forced   # exit 1 where a boundary is owed now
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
LOGS = ROOT / ".slipwai/logs"
#: Where each machine's harbourmaster writes its own log. One per machine since 11.3, so this is a
#: directory of files rather than one file, and it is not a feature's.
HARBOUR_LOGS = LOGS / "harbour"
HARBOUR = ROOT / "harbour.json"
V = 1
#: Used where `harbour.json` is absent or unreadable. The file is the answer; these keep the rules working
#: in a project that has not got one yet rather than making them conditional on it.
DEFAULT_CEILING = 10
DEFAULT_WAIT = 60


def settings() -> tuple[int, int]:
    try:
        document = json.loads(HARBOUR.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT_CEILING, DEFAULT_WAIT
    return (int(document.get("decision_ceiling", DEFAULT_CEILING)),
            int(document.get("wait_bound", DEFAULT_WAIT)))


def lines(fairway: str) -> list[dict]:
    """This fairway's deck log and every harbour log, which is where a person's messages arrive.

    Every machine's, since the harbour log became one file per machine: a message that reached the harbour
    on one of them is still a message to this fairway, and reading only this machine's would make whether a
    person is waiting depend on which machine happened to be running when they wrote.
    """
    paths = [path for path in LOGS.glob(f"*/{fairway}.jsonl")
             if path.parent.name != HARBOUR_LOGS.name] if LOGS.is_dir() else []
    paths += sorted(HARBOUR_LOGS.glob("*.jsonl")) if HARBOUR_LOGS.is_dir() else []
    older = LOGS / "harbour.jsonl"
    if older.is_file():
        paths.append(older)
    found: list[dict] = []
    for path in sorted(paths):
        for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not text.strip():
                continue
            try:
                line = json.loads(text)
            except ValueError:
                raise SystemExit(f"inbox: {path.name}:{number} is not JSON. Reading past it would report an "
                                 f"empty inbox that is not empty.") from None
            if isinstance(line, dict) and line.get("v") != V:
                raise SystemExit(f"inbox: {path.name}:{number} says v{line.get('v')} and this reader knows "
                                 f"v{V}. Run `slipwai upgrade`.")
            if isinstance(line, dict):
                found.append(line)
    return found


def minutes_since(instant: str, now: datetime | None = None) -> float:
    """How long ago, in minutes. An unparseable instant reads as *now*, which never forces a boundary on
    the strength of a timestamp nobody can read."""
    try:
        when = datetime.strptime(instant, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return 0.0
    return (( now or datetime.now(UTC)) - when).total_seconds() / 60


def unread(written: list[dict]) -> list[dict]:
    """Every `told` with no `read` carrying its timestamp. The receipt is the timestamp, not the count."""
    receipts = {str(line.get("told")) for line in written if line.get("kind") == "read"}
    return [line for line in written if line.get("kind") == "told" and str(line.get("t")) not in receipts]


def unreviewed(written: list[dict]) -> list[dict]:
    """Every `decision` a person has not read. The same receipt rule, for the same reason."""
    receipts = {str(line.get("told")) for line in written if line.get("kind") == "read"}
    return [line for line in written if line.get("kind") == "decision" and str(line.get("t")) not in receipts]


def overrun(written: list[dict], bound: int, now: datetime | None = None) -> list[dict]:
    """Every wait past its bound: a `told` nobody answered, which is the wait a person can end."""
    return [line for line in unread(written) if minutes_since(str(line.get("t", "")), now) > bound]


def owed(fairway: str, now: datetime | None = None) -> dict:
    """What this fairway owes at this boundary, and whether one is forced before the next stage starts."""
    ceiling, bound = settings()
    written = lines(fairway)
    waiting, backlog = unread(written), unreviewed(written)
    late = overrun(written, bound, now)
    return {
        "unread": waiting,
        "unreviewed": backlog,
        "overrun": late,
        "ceiling": ceiling,
        "over_ceiling": len(backlog) > ceiling,
        # A boundary is forced by a message nobody answered in time, or by a backlog of judgement nobody
        # has looked at. Either way the next thing to happen is a person, not another stage.
        "forced": bool(late) or len(backlog) > ceiling,
    }


def main(argv: list[str]) -> int:
    if not argv:
        print("inbox: give a fairway, as `inbox.py ORD`", file=sys.stderr)
        return 1
    state = owed(argv[0])
    if "--forced" in argv:
        print("inbox: a boundary is owed now" if state["forced"] else "inbox: nothing forces a boundary")
        return 1 if state["forced"] else 0
    print(f"inbox: {len(state['unread'])} unread, {len(state['unreviewed'])} decisions unreviewed "
          f"(ceiling {state['ceiling']}), {len(state['overrun'])} past their bound")
    for line in state["unread"]:
        print(f"  told {line.get('t')}: {line.get('message')}")
    if state["over_ceiling"]:
        print(f"  over the decision ceiling — this fairway parks until a person reads them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
