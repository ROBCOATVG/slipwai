#!/usr/bin/env python3
"""What keeps a stream's captain agent in its place beyond what its orders are checked against.

**The project as it was.** A captain run as a process is started in a folder of its own with the most
restrictive mode its harness offers, and is still a session with a shell that can reach the project. So the
project's checkout is read before and after each decision it is woken for — `git status --porcelain`, `HEAD`,
and every local branch head but the slices' own — and a difference is a captain that changed something.
Where a slice of the stream is being worked in the checkout itself (a stream held to one slice at a time),
that slice changes it too and the checkout is not read; and the deck and harbour logs are not read, because
slices and the harbourmaster write them while the captain decides, and a check that fired on them would
turn every captain off. What is read is what nothing else in the fleet changes during a decision.

**Off until a person says.** A captain caught changing the project is turned off for its stream — a record
beside its events that the board's reader shows and nothing but a person removes — and the stream runs on
its rules.

**A ceiling an hour.** Past `captain.per_hour` events in the last hour, the stream runs on its rules alone
until the hour has passed: a captain woken without end is paid for without end.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

OFF = "agent-off.json"
HOUR = 3600.0


def git(root: Path, *argv: str) -> str:
    try:
        done = subprocess.run(["git", *argv], cwd=root, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


def snapshot(root: Path, busy: bool, run: Path | None = None) -> dict[str, str]:
    """The checkout as it stands, as far as nothing else in the fleet changes it during a decision: never the
    run folder, which the captain program itself writes while the agent decides."""
    heads = "\n".join(line for line in git(root, "for-each-ref", "--format=%(refname) %(objectname)",
                                           "refs/heads").splitlines() if not line.startswith("refs/heads/slice/"))
    held = {"heads": heads}
    if not busy:
        outside = [f":(exclude){run.resolve().relative_to(root.resolve()).as_posix()}"] if run is not None and \
            run.resolve().is_relative_to(root.resolve()) else []
        held.update(status=git(root, "status", "--porcelain", "--untracked-files=all", "--", ".", *outside),
                    head=git(root, "rev-parse", "HEAD"))
    return held


def changed(before: dict[str, str], after: dict[str, str]) -> str:
    """What differs, said shortly, or `''`. A checkout a slice took over meanwhile is not compared."""
    found = []
    if before.get("heads") != after.get("heads"):
        found.append("a branch head moved")
    if "status" in before and "status" in after:
        if before["head"] != after["head"]:
            found.append("the checkout's HEAD moved")
        was, now = set(before["status"].splitlines()), set(after["status"].splitlines())
        if was != now:
            moved = sorted(line[3:] for line in now ^ was)
            found.append("files changed in the checkout: " + ", ".join(moved[:5]) + ("…" if len(moved) > 5 else ""))
    return "; ".join(found)


def turn_off(events: Path, why: str) -> None:
    events.mkdir(parents=True, exist_ok=True)
    said = {"v": 1, "t": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "why": why,
            "lift": f"remove {OFF} beside this stream's events to turn its captain agent on again"}
    (events / OFF).write_text(json.dumps(said, indent=1) + "\n", encoding="utf-8")


def turned_off(events: Path) -> str:
    """Why this stream's captain agent is off, or `''`."""
    try:
        held = json.loads((events / OFF).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return ""
    return str(held.get("why") or "it was turned off") if isinstance(held, dict) else "it was turned off"


def past_ceiling(events: Path, per_hour: int) -> bool:
    """Whether this stream's captain has been woken `per_hour` times in the last hour already."""
    if per_hour <= 0 or not events.is_dir():
        return False
    since = time.time() - HOUR
    return sum(1 for path in events.glob("*.closed.json") if path.stat().st_mtime >= since) >= per_hour
