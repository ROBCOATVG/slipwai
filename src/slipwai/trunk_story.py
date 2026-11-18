"""Trunk's story as the board tells it: red or green, since when, and what the trunk mender did about it.

A red trunk holds every merge, and the harbourmaster sends the trunk mender (`mender.py` in the toolkit) to
clear it. Each attempt is a harbour line — `mend`, then `mended` or `mend-failed` — and once every attempt is
spent a `park` with no fairway says a person decides. The board read only `trunk-red` and `trunk-green`, so
a fleet whose mender had given up said nothing at all: no attempt, none of the mender's words, nothing waiting
on anybody, while no merge could be granted. This folds the rest of it, from the files the run already
writes and nothing new:

- the harbour log's lines since trunk last went red (or, once green, the red stretch that just ended), each
  `mend` joined to its outcome in the order the log has them;
- `running/mender.json`, there only while an attempt runs: its attempt, branch, start and the CI run's link;
- `running/mender.out`, the attempt's own event stream, read from its tail only — it is tens of megabytes on
  a long attempt — through `talk.read_bytes`, and kept by size and modification time, so a poll that finds
  it unchanged reads nothing. Its last `result` is the mender's own explanation; the lines after it are what
  the attempt in flight is doing, folded as a session's are (`session_log`).

**A harbour park is cleared by trunk going green, and by nothing else.** The harbourmaster answers a
person's `told` per fairway (`told_after_parks`), and a park with no fairway has no deck a `told` lands in;
the mender looks only at what came after the newest `trunk-red`. So the park is open while trunk is red and
retired when it turns green, and the board offers no button that would do nothing.
"""
from __future__ import annotations

import json
import os
import stat
import threading
from pathlib import Path
from typing import Any

from .logs import Entry, run_dir
from .process_alive import alive
from .session_log import Folder
from .talk import read_bytes

#: How much of the end of `mender.out` is read: enough for the mender's closing explanation and the lines
#: before it, never the whole file.
TAIL = 512 * 1024
#: The longest explanation kept, in characters: what a person reads, not a transcript.
LONGEST = 20_000
#: Lines of what an attempt in flight is doing.
DOING = 8
#: `harbour.json`'s `attempts` where it says none, as the mender counts them.
ATTEMPTS = 3
#: How long a green trunk that the mender cleared still says so, in seconds.
BRIEFLY = 15 * 60

GUARD = threading.Lock()
#: Each `mender.out` read, by path: (size, modification time, what it said).
KEPT: dict[str, tuple[int, int, dict[str, Any]]] = {}


def number(value: object) -> int:
    """An attempt's number as a log or a record wrote it; 1 where it is not a whole number."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 1


def stretch(harbour: list[Entry]) -> tuple[list[Entry], str, str]:
    """The harbour lines since trunk last went red, the state, and when it turned green where it has.
    A green trunk keeps the red stretch that ended with it, which is what the Fleet tab's history reads."""
    words = [index for index, e in enumerate(harbour) if e.kind in ("trunk-red", "trunk-green")]
    if not words:
        return [], "", ""
    last = harbour[words[-1]]
    reds = [index for index in words if harbour[index].kind == "trunk-red"]
    if last.kind == "trunk-red":
        return harbour[reds[-1]:], "red", ""
    if not reds:
        return [], "green", last.t
    return harbour[reds[-1]:words[-1] + 1], "green", last.t


def attempts_of(lines: list[Entry], held: dict[str, Any]) -> list[dict[str, Any]]:
    """Each trunk attempt in the stretch with its outcome: `mended`, `failed`, `running`, or `no word`."""
    found: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if line.kind != "mend" or line.fields.get("job") != "trunk":
            continue
        attempt = number(line.fields.get("attempt"))
        later = [e for e in lines[index + 1:] if e.fields.get("job") == "trunk"
                 and e.kind in ("mend", "mended", "mend-failed")]
        outcome = later[0] if later and later[0].kind != "mend" else None
        one = {"attempt": attempt, "t": line.t, "commit": str(line.fields.get("commit") or ""),
               "branch": str(line.fields.get("branch") or ""), "url": str(line.fields.get("url") or ""),
               "outcome": "no word", "why": "", "landed": "", "ended": ""}
        if outcome is not None:
            one.update(outcome="mended" if outcome.kind == "mended" else "failed", ended=outcome.t,
                       why=str(outcome.fields.get("why") or ""),
                       landed=str(outcome.fields.get("commit") or "") if outcome.kind == "mended" else "")
        elif held and held.get("attempt") == attempt:
            one["outcome"] = "running" if held.get("alive") else "ending"
        found.append(one)
    return found


def record(root: Path) -> dict[str, Any]:
    """The trunk attempt in flight, as `running/mender.json` says it, or {}: a need's attempt is not trunk's."""
    got = read_bytes(run_dir(root) / "running/mender.json", 64 * 1024)
    try:
        held = json.loads(got[0].decode("utf-8")) if got else None
    except (UnicodeDecodeError, ValueError, RecursionError):
        return {}
    if not isinstance(held, dict) or held.get("job", "trunk") != "trunk":
        return {}
    pid, started, attempt = held.get("pid"), held.get("started"), held.get("attempt")
    return {"attempt": number(attempt),
            "branch": str(held.get("branch") or ""), "url": str(held.get("url") or ""),
            "commit": str(held.get("commit") or ""),
            "started": float(started) if isinstance(started, int | float) else 0.0,
            "alive": isinstance(pid, int) and not isinstance(pid, bool) and alive(pid)}


def said(root: Path) -> dict[str, Any]:
    """The mender's last explanation and what the attempt after it is doing, from the tail of `mender.out`.
    Read again only when its size or modification time has moved."""
    path = run_dir(root) / "running/mender.out"
    try:
        seen = os.lstat(path)
    except OSError:
        return {"result": "", "doing": []}
    if not stat.S_ISREG(seen.st_mode):
        return {"result": "", "doing": []}
    key = str(path)
    with GUARD:
        kept = KEPT.get(key)
    if kept is not None and kept[:2] == (seen.st_size, seen.st_mtime_ns):
        return kept[2]
    got = read_bytes(path, TAIL, -TAIL)
    found = told(got[0], got[1] > TAIL, root) if got else {"result": "", "doing": []}
    with GUARD:
        KEPT[key] = (seen.st_size, seen.st_mtime_ns, found)
    return found


def told(raw: bytes, cut: bool, root: Path | None = None) -> dict[str, Any]:
    """The last `result` in `raw` and the folded lines after it. `cut` where `raw` starts mid-file, so its
    first line is a piece of one and is dropped."""
    lines = raw.decode("utf-8", errors="replace").split("\n")
    if cut:
        lines = lines[1:]
    result, after = "", 0
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index].strip()
        if not line.startswith("{") or '"result"' not in line:
            continue
        try:
            event = json.loads(line)
        except (ValueError, RecursionError):
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            result, after = str(event.get("result") or event.get("subtype") or "").strip(), index + 1
            break
    folder, doing = Folder(root), []
    for line in lines[after:]:
        if line.strip():
            doing += folder.fold(line.strip()) if line.lstrip().startswith("{") else []
    return {"result": result[:LONGEST], "doing": [one[:240] for one in doing[-DOING:]]}


def story(root: Path, harbour: list[Entry], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Trunk's state with what the mender did about it: the board's `trunk`, read by the Voyage's band, the
    Fleet tab's card, the Needs a look strip and the one list of what waits on a person."""
    held = config or {}
    lines, state, green = stretch(harbour)
    if not state:
        return {"state": "", "t": "", "why": "", "job": "", "commit": ""}
    red = lines[0] if lines and lines[0].kind == "trunk-red" else None
    last = next(e for e in reversed(harbour) if e.kind in ("trunk-red", "trunk-green"))
    running = record(root) if state == "red" else {}
    tried = attempts_of(lines, running)
    parks = [e for e in lines if e.kind == "park" and not str(e.fields.get("fairway") or "")]
    limit = held.get("attempts")
    urls = [one["url"] for one in tried if one["url"]] + ([running["url"]] if running.get("url") else [])
    if red is not None and red.fields.get("url"):
        urls.insert(0, str(red.fields["url"]))
    return {"state": state, "t": last.t, "why": str(red.fields.get("why") or "") if red else "",
            "job": str(red.fields.get("job") or "") if red else "",
            "commit": str((red or last).fields.get("commit") or ""), "red_t": red.t if red else "",
            "green_t": green, "green_commit": str(last.fields.get("commit") or "") if green else "",
            "attempts": tried, "of": limit if isinstance(limit, int) and limit > 0 else ATTEMPTS,
            "off": held.get("mender") == "off", "running": running,
            "parked": ({"t": parks[-1].t, "why": str(parks[-1].fields.get("why") or ""),
                        "mend": bool(parks[-1].fields.get("mend"))} if parks and state == "red" else {}),
            "urls": [url for url in dict.fromkeys(urls) if url.startswith(("https://", "http://"))],
            "said": said(root) if tried or running else {"result": "", "doing": []}}
