"""One read of a project for the board, kept for about two seconds and shared by every poll.

Every poll read the run from the start, and nothing was kept between them: the project's clearance script
twice — once for the columns and once for the berths — and its gates once, each a Python child behind a
login shell of its own. A Voyage window asked for that five times every few seconds, a second window on the
same project asked again, and half a second of children a poll was the board's whole cost.

So a project is read once here and the read is kept for `KEEP` seconds behind a lock: polls that arrive in
that time — from this window's bands or another window's — are answered from it, and one that arrives while
it is being made waits for it rather than starting a second. Inside the read the clearance script is asked
once per feature (`fleet.ASKED`) and the login shell once per board process (`shell_environment.KEEP_LOGIN`).

**A person's own action drops it.** Every POST the board handles calls `forget`, so what somebody just did is
never shown undone for two seconds; a read that was being made while they did it is not kept either. What
is per window — the board's own child, the seat a frame is addressed by — is never in here: it is read per
request, by whoever asked.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .activity import live
from .checkout_level import level
from .fleet import ASKED, board, harbour_log
from .harbour import config
from .logs import Entry
from .park_verdict import mark
from .shell_environment import ANSWERED, KEEP_LOGIN
from .trunk_story import story
from .voyage import feedback_points, fleet_running, folded

#: Seconds a read is kept. Under the page's poll, so each poll of a window on its own still reads the run
#: fresh; long enough that every band, window and route asking at once is answered by one read.
KEEP = 2.0
#: How old a kept read may be and still answer at once while it is made again behind the request.
STALE = 60.0
#: Projects held at once. A board kept up by a login service is pointed at a lot of trees in a month.
HELD = 16


@dataclass(frozen=True)
class Read:
    """Everything the Voyage's bands are drawn from that is the project's rather than the window's."""

    rows: list[dict[str, str]]
    fault: str
    fleet: dict
    config: dict
    folds: dict[str, dict]
    points: list[dict]
    trunk: dict[str, Any]


GUARD = threading.Lock()
LOCKS: dict[str, threading.Lock] = {}
KEPT: dict[str, tuple[float, Read]] = {}
#: Bumped by `forget`, so a read begun before a person's action is not kept after it.
EPOCH: dict[str, int] = {}
#: The projects whose read is being made again behind a request already answered.
REMAKING: set[str] = set()


def trunk_of(harbour: list[Entry]) -> dict[str, str]:
    """Trunk's own CI, as the harbour last wrote it: `red` or `green` with when and why, or nothing yet."""
    said = [e for e in harbour if e.kind in ("trunk-red", "trunk-green")]
    if not said:
        return {"state": "", "t": "", "why": "", "job": ""}
    last = said[-1]
    return {"state": "red" if last.kind == "trunk-red" else "green", "t": last.t,
            "why": str(last.fields.get("why") or ""), "job": str(last.fields.get("job") or "")}


def fold(root: Path) -> Read:
    """The read itself, made fresh: the columns, the berths, the activity, and trunk with what the trunk mender
    did about it (`trunk_story`)."""
    asked, login = ASKED.set({}), KEEP_LOGIN.set(True)
    try:
        rows, fault = folded(root)
        held = config(root)
        # Whether each mock-up verdict's card may offer Approve and Reject: a reading of the drawings, so here.
        fleet = mark(root, {**board(root, held), "running": fleet_running(root)})
        unreadable = fleet.get("unreadable")
        if fault or (isinstance(unreadable, dict) and unreadable.get("clearance")):
            ANSWERED.clear()  # the shell's answer may be why: the next read asks it again
        harbour = harbour_log(root)
        # And whether this folder is level with the forge's trunk, which is how old a project it is drawing.
        return Read(rows, fault, fleet, held, live(root, rows), feedback_points(root),
                    {**trunk_of(harbour), **story(root, harbour, held),
                     "checkout": level(root, held.get("trunk"))})
    finally:
        ASKED.reset(asked)
        KEEP_LOGIN.reset(login)


def read(root: Path) -> Read:
    """The project's read: the one kept, while it is fresh, else a new one, made once however many ask.

    A read past its `KEEP` but younger than `STALE` is answered at once and made again behind it, by one thread:
    on a project as large as manda's a read takes seconds, and every request that found the kept one two seconds
    old waited all of them, so the window drew in one second and then in seven. A person's own action drops the
    kept read (`forget`), so what they did is never answered from before it; nothing older than `STALE` is."""
    key = str(root)
    with GUARD:
        lock = LOCKS.setdefault(key, threading.Lock())
        kept = KEPT.get(key)
        age = time.monotonic() - kept[0] if kept is not None else None
        behind = age is not None and KEEP <= age < STALE and key not in REMAKING
        if behind:
            REMAKING.add(key)
    if behind and kept is not None:
        threading.Thread(target=remake, args=(root, lock), daemon=True).start()
        return kept[1]
    return made_now(root, lock)


def remake(root: Path, lock: threading.Lock) -> None:
    """Make the read again behind the request that was answered from the kept one."""
    try:
        made_now(root, lock, force=True)
    except Exception:  # noqa: BLE001 — a read that fails here is made again, in the open, by the next request
        pass
    finally:
        with GUARD:
            REMAKING.discard(str(root))


def made_now(root: Path, lock: threading.Lock, force: bool = False) -> Read:
    """The read made under the project's lock, or the one kept where it is fresh and this is not a remake."""
    key = str(root)
    with lock:
        with GUARD:
            kept, epoch = KEPT.get(key), EPOCH.get(key, 0)
        if kept is not None and KEEP > 0 and time.monotonic() - kept[0] < KEEP and not force:
            return kept[1]
        made = fold(root)
        with GUARD:
            if EPOCH.get(key, 0) == epoch and KEEP > 0:
                KEPT[key] = (time.monotonic(), made)
                for old in sorted(KEPT, key=lambda name: KEPT[name][0])[:-HELD]:
                    KEPT.pop(old, None)
        return made


def forget(root: Path | None = None) -> None:
    """Drop what is kept for `root`, or for every project: a person has just done something to it."""
    with GUARD:
        for key in [str(root)] if root is not None else list(set(KEPT) | set(LOCKS)):
            KEPT.pop(key, None)
            EPOCH[key] = EPOCH.get(key, 0) + 1
