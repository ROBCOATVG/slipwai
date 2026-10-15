#!/usr/bin/env python3
"""What was started, where, and by what — written at the moment of dispatch and committed.

    python3 scripts/agents/dispatch.py --feature <feature>   # write the ledger for what starts now
    python3 scripts/agents/dispatch.py --feature <feature> --json

**The decision to run one slice at a time was free and left no trace.** `commands/sail.md` says to fan out
over the ready set, and 859 lines in it says what to do where the harness cannot delegate — run one at a
time, and *say so in the line that says which model ran*. Nothing read that line. A run that took the
ready set one slice at a time and a run that fanned out over it were indistinguishable afterwards except
by reading a transcript by hand, which is how this came to be written.

So the first act of a run is a command rather than a paragraph, and it writes one line per slice:
dispatched into which worktree with which delegate, or **not dispatched and why**. Both are recorded —
a run that could not delegate is not a failure, but a run that could not delegate and left no line is
indistinguishable from one that simply did not try.

**Committed, unlike the deck logs.** The logs are a machine's running record and travel as refs; this is
evidence about a commit, and the gate that reads it runs on a checkout that has only what git carries.
`specs/<feature>/dispatch-ledger.jsonl`, append-only, one JSON object per line.

**It will not write a line on an answer it does not have.** `preflight.py --record` leaves this checkout's
own answer under `.slipwai/`, and without a current one there is nothing here saying whether this session
can delegate at all — so the ledger would be recording a guess. That is the chain: skipping preflight is
not refused, it just leaves nothing to dispatch with, and `check-dispatch.py` refuses the push.

Standalone and dependency-free beyond the modules beside it: this ships inside a generated project, which
has no slipwai to import.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402
import logs  # noqa: E402

ROOT = harness.ROOT
SPECS = ROOT / "specs"
#: This checkout's own preflight answer. Absent means nothing here has asked whether the method can run.
RECORD = ROOT / ".slipwai/preflight.json"
#: How old a preflight answer may be and still be about this checkout. A checkout changes under a run —
#: a branch moves, `make agents` is run, a worktree is made — and an answer from this morning is about a
#: different tree. One hour is long enough not to be ceremony and short enough to still be evidence.
STALE_AFTER = 3600.0
#: The one file this writes, per feature. Append-only: a ledger that was ever rewritten would be a ledger
#: whose earlier lines nobody can trust, and the earlier lines are the whole evidence.
LEDGER = "dispatch-ledger.jsonl"
#: Which delegate type takes a band. One type for all three, because *Running ready slices concurrently*
#: hands a band to one fresh `sail-slice-watch` and that delegate chooses stage by stage inside itself.
DELEGATE = "sail-slice-watch"
#: What a line may say about a slice. A closed set: a word nobody wrote down is one nobody reviewed.
OUTCOMES = ("dispatched", "taken-here", "left-named")


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def preflight() -> tuple[dict, str]:
    """This checkout's preflight answer, or the sentence saying why there is none to stand on."""
    if not RECORD.is_file():
        return {}, ("nothing in this checkout has run `make preflight`, so nothing here says whether the "
                    "method can run at all — whether the delegate types are projected, whether this "
                    "harness has any. Run `make preflight` and dispatch again")
    try:
        found = json.loads(RECORD.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}, f"{RECORD.name} is not readable as JSON. Run `make preflight` and dispatch again"
    if not isinstance(found, dict) or not found.get("at"):
        return {}, f"{RECORD.name} carries no timestamp, so nothing says which checkout it is about"
    try:
        when = datetime.fromisoformat(str(found["at"]).replace("Z", "+00:00"))
    except ValueError:
        return {}, f"{RECORD.name} carries an unreadable timestamp ({found['at']!r})"
    age = (datetime.now(UTC) - when).total_seconds()
    if age > STALE_AFTER:
        return {}, (f"the preflight answer here is {int(age // 60)} minutes old and a checkout changes "
                    f"under a run. Run `make preflight` and dispatch again")
    return found, ""


def clearance(feature: str) -> tuple[dict, str]:
    """What may start now, asked of the one thing that knows. Never guessed from a status field."""
    command = [sys.executable, str(HERE / "clearance.py"), "--json"]
    if feature:
        command += ["--feature", feature]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=120, cwd=ROOT, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {}, f"clearance could not be asked: {type(error).__name__}: {error}"
    try:
        found = json.loads(done.stdout or "{}")
    except ValueError:
        return {}, f"clearance answered nothing a reader can parse: {(done.stderr or done.stdout).strip()[:200]}"
    if found.get("error"):
        return {}, str(found["error"])
    return found, ""


def lines(found: dict, able: bool, why: str, machine: str, key: str) -> list[dict]:
    """One line per slice that may start, in the order clearance put them.

    Where the harness can delegate, every one of them is dispatched. Where it cannot, the rule the command
    page states in prose is applied here instead: the earliest in the ordered split is taken in this
    session and the rest are *named*, so another session can claim a sibling. The difference between the
    two runs is now a word in a file rather than a thing you would have to read a transcript to see.
    """
    starting = (found.get("schedule") or {}).get("start") or []
    written = []
    for slot, row in enumerate(starting, start=1):
        slice_id = str(row.get("slice", ""))
        band = str(row.get("band", ""))
        if able:
            outcome, because = "dispatched", f"slot {slot} of {found.get('slots') or len(starting)}"
        elif slot == 1:
            outcome, because = "taken-here", why
        else:
            outcome, because = "left-named", f"{why}; another session may claim this one"
        written.append({"v": 1, "t": now(), "feature": str(found.get("feature", "")), "slice": slice_id,
                        "band": band, "slot": slot, "outcome": outcome, "why": because,
                        "delegate": DELEGATE if able else "", "harness": key, "machine": machine,
                        "worktree": f"../{ROOT.name}-{slice_id}" if able else ""})
    return written


def ledger_of(feature: str) -> Path:
    return SPECS / feature / LEDGER


def append(path: Path, written: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for row in written:
            file.write(json.dumps(row, sort_keys=True) + "\n")


def read(path: Path) -> list[dict]:
    """Every line of one ledger, skipping what cannot be read rather than failing the gate that reads it."""
    if not path.is_file():
        return []
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            found.append(row)
    return found


def dispatched_slices(feature: str) -> set[str]:
    """Every slice this feature's ledger accounts for, however it accounts for it."""
    return {str(row.get("slice", "")) for row in read(ledger_of(feature)) if row.get("slice")}


def main(argv: list[str]) -> int:
    feature = ""
    if "--feature" in argv:
        index = argv.index("--feature") + 1
        feature = argv[index] if index < len(argv) and not argv[index].startswith("--") else ""
    flown, refused = preflight()
    if refused:
        print(f"dispatch: {refused}", file=sys.stderr)
        return 1
    found, why_not = clearance(feature)
    if why_not:
        print(f"dispatch: {why_not}", file=sys.stderr)
        return 1
    able = bool(flown.get("delegates") is True)
    why = str(flown.get("why") or "no reason was recorded")
    written = lines(found, able, why, logs.machine(), harness.current_key())
    if not written:
        print("dispatch: clearance names nothing that may start now, so there is nothing to dispatch")
        return 0
    path = ledger_of(str(found.get("feature", "")))
    append(path, written)
    if "--json" in argv:
        print(json.dumps({"v": 1, "ledger": path.relative_to(ROOT).as_posix(), "lines": written}))
        return 0
    print(f"dispatch: {len(written)} line(s) written to {path.relative_to(ROOT).as_posix()}")
    for row in written:
        tail = f" → {row['worktree']}" if row["worktree"] else ""
        print(f"  {row['outcome']:<11} {row['slice']:<8} {row['band']:<9} {row['why']}{tail}")
    if not able:
        print("dispatch: this session cannot delegate, and the ledger says so. That is a recorded reason "
              "for running one slice at a time, not a judgement about it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
