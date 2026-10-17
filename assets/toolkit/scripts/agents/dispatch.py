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
`.slipwai/dispatch/<feature>.jsonl`, append-only, one JSON object per line: with the run's other committed
records rather than in `specs/`, which is the feature's specification and not evidence about how it was
worked. A ledger at the old `specs/<feature>/dispatch-ledger.jsonl` is still read until `slipwai migrate`
moves it, and never written.

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
#: Where this writes, one file per feature. Append-only: a ledger that was ever rewritten would be a ledger
#: whose earlier lines nobody can trust, and the earlier lines are the whole evidence.
LEDGERS = ROOT / ".slipwai/dispatch"
#: Where the ledger was until 2.0.0, under each feature. Read, never written; `slipwai migrate` moves it.
OLD_LEDGER = "dispatch-ledger.jsonl"
#: Which delegate type takes a band. One type for all three, because *Running ready slices concurrently*
#: hands a band to one fresh `sail-slice-watch` and that delegate chooses stage by stage inside itself.
DELEGATE = "sail-slice-watch"
#: What a line may say about a slice. A closed set: a word nobody wrote down is one nobody reviewed.
#: `baselined` is the one that names no slice — it is about the run, not about a piece of work.
OUTCOMES = ("dispatched", "taken-here", "left-named", "baselined")
#: The clearance state that says a slice waits on a mark whose setter already shipped. Not `blocked`: the
#: work is done and the wait is an artefact of crossing into a version that has a mark log.
NEEDS_BASELINE = "migration-evidence-required"


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


def clearance(feature: str, *flags: str) -> tuple[dict, str]:
    """What may start now, asked of the one thing that knows. Never guessed from a status field."""
    command = [sys.executable, str(HERE / "clearance.py"), "--json", *flags]
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


def owed_a_baseline(found: dict) -> list[str]:
    """The slices waiting on a mark that shipped before there was a log to write it in.

    `clearance.py` calls this state `migration-evidence-required` rather than `blocked` for exactly this
    reason: the setter is *done*, so the wait is an artefact of the crossing and not of the work.
    """
    return sorted(slice_id for slice_id, row in (found.get("states") or {}).items()
                  if isinstance(row, dict) and row.get("state") == NEEDS_BASELINE)


def baseline(feature: str) -> tuple[bool, str]:
    """Record the marks a crossing owes, once. (it was taken, what it said).

    **Run here rather than asked of a person.** It derives rather than invents — one `mark-set` per mark a
    *done* slice sets, stamped `provenance: baseline` with the evidence it read — and `clearance.py`
    refuses a second one outright, so automating it cannot turn it into a way past the gate. Left to a
    person it is a command nobody runs, and every slice steering by a shipped mark stays blocked for ever
    in a loop nobody is watching.
    """
    command = [sys.executable, str(HERE / "clearance.py"), "--baseline-marks"]
    if feature:
        command += ["--feature", feature]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=120, cwd=ROOT, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"the baseline could not be taken: {type(error).__name__}: {error}"
    said = (done.stdout or done.stderr).strip().splitlines()
    return done.returncode == 0, (said[-1] if said else "nothing was said").removeprefix("clearance: ")


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
    return LEDGERS / f"{feature}.jsonl"


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
    """Every slice this feature's ledger accounts for, however it accounts for it — the old home included."""
    rows = read(ledger_of(feature)) + read(SPECS / feature / OLD_LEDGER)
    return {str(row.get("slice", "")) for row in rows if row.get("slice")}


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
    # Before anything is scheduled, because a slice waiting on a shipped mark is not a slice that may not
    # start — it is one nothing has written the evidence for yet, and the schedule below would leave it out.
    owed, taken = owed_a_baseline(found), ""
    if owed:
        recorded, said = baseline(feature)
        if recorded:
            taken = said
            found, why_not = clearance(feature)
            if why_not:
                print(f"dispatch: {why_not}", file=sys.stderr)
                return 1
        else:
            # A baseline already spent, or one that could not run. Said once and never written to the
            # ledger: a line per dispatch saying the same thing is a line nobody reads by the third one.
            print(f"dispatch: {len(owed)} slice(s) wait on a shipped mark and no baseline was taken — "
                  f"{said}", file=sys.stderr)
    able = bool(flown.get("delegates") is True)
    why = str(flown.get("why") or "no reason was recorded")
    written = lines(found, able, why, logs.machine(), harness.current_key())
    if taken:
        # Named in the ledger as well as in the harbour log, so a reader of *this run* can see that what it
        # dispatched on stood partly on derived evidence rather than on marks any stage here earned.
        written.insert(0, {"v": 1, "t": now(), "feature": str(found.get("feature", "")), "slice": "",
                           "band": "", "slot": 0, "outcome": "baselined", "why": taken, "delegate": "",
                           "harness": harness.current_key(), "machine": logs.machine(), "worktree": ""})
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
        tail = f" -> {row['worktree']}" if row["worktree"] else ""
        print(f"  {row['outcome']:<11} {row['slice']:<8} {row['band']:<9} {row['why']}{tail}")
    if not able:
        print("dispatch: this session cannot delegate, and the ledger says so. That is a recorded reason "
              "for running one slice at a time, not a judgement about it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
