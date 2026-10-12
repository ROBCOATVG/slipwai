#!/usr/bin/env python3
"""The captain: the outer loop for one fairway, and the thing that believes the log rather than the agent.

`cruise.py` ran one iteration per checkout and trusted what the iteration said about itself. It died at
iteration two, and the seventeen iterations that followed ran from interactive sessions and wrote nothing —
so the checkpoint still said "iteration 2" while twenty slices merged. The inversion this file is built on
falls straight out of that: **a stage that wrote no line made no progress**, and every control here reads
lines rather than asking the thing being controlled how it is getting on.

Each turn it: fetches trunk and both logs; derives the fairway's state from its own `claimed` and `merged`
lines; takes a `fix-trunk` ahead of anything new where the harbourmaster has sent one, because a trunk this
fairway reddened is worth more than any slice it could start; otherwise picks the next slice in split order
that `clearance.py` allows; writes `claimed`; dispatches `/sail`
for that slice in its berth — a headless session of the installed harness, asked for `/sail <slice>
fairway=<name>`; watches the deck log while it runs; reads the inbox at every boundary and
enforces the receipt; asks the harbourmaster for the merge, because a captain holds no credential; and
writes `merged` against the commit the answer names.

**Nothing it relies on is in the agent's answer.** Progress is a new line in the deck log. A stage that has
written nothing for its wall budget is ended and `parked` with the reason — not because the agent said it was
stuck, which a stuck agent cannot say, but because the log stopped.

**And a slice is through its gate only when the log says so, in lines written during this turn.** That rule
was applied to the wall budget and nowhere else, so the first real run had `/sail` print a help message,
exit 0, and this file write `claimed`, then `request: merge`, and report the slice through its gate — with
no `mark-set` and no `demo` anywhere. What closes a slice now is every mark the chart says it `sets`, plus a
`demo`, all after the index this turn started at. *During this turn* is the whole of it: without it a retry
passes on the previous turn's lines, which is the same fault as a cursor that outlives its log.

A demo that came back `behaviour` or `implementation` is not a park, it is a retry. The person who sent it
back is present and has just written notes, and parking would ask them to come back and restart a fairway
before anything acts on them. `/sail` re-enters at the first incomplete stage, so a retry resumes at the
demo rung with the notes in the slice. `attempts` in `harbour.json` bounds it; when it is spent the fairway
parks naming the verdict and the count.

**A hook never costs the rung.** The extension hook points fire around each rung, at each boundary and before
a merge; `hooks.py` always exits 0 for them, and the captain does not read their output. A hook is a second
belt, and a second belt that can stop the run is the thing it was meant to be instead of.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import claims  # noqa: E402
import clearance  # noqa: E402
import harness  # noqa: E402
import inbox  # noqa: E402
import logs  # noqa: E402


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
HARBOUR = ROOT / "harbour.json"
HOOKS = ROOT / "scripts/extensions/hooks.py"
#: The ladder itself. A harness whose print mode resolves this project's slash commands is asked `/sail`;
#: every other is asked to read this file and follow it.
DRIVE_COMMAND = ROOT / "commands/sail.md"
#: How often a heartbeat is written while a slice is being worked. Short enough that a fleet board can tell a
#: wedged berth from a slow one, long enough that it is not most of the log.
HEARTBEAT = 60.0
#: How often the deck log is re-read while `/sail` runs. The log is the only progress signal there is.
POLL = 2.0
#: Used where `harbour.json` is absent or unreadable — the file is the answer, and these keep the loop
#: bounded while somebody fixes it rather than letting an unbounded stage be the cost of a typo.
DEFAULT_STAGE_MINUTES = 30
#: Re-dispatches of `/sail` for one slice, where `harbour.json` does not say. `half-ahead`'s number, which
#: is what a fresh harbour is at.
DEFAULT_ATTEMPTS = 2
#: The verdict that closes a slice, and the two that send it back. `logs.VERDICTS` is the whole set.
ACCEPTED = "accepted"
#: How often the harbour log is re-read while waiting for an answer to a request.
ANSWER_POLL = 2.0
#: What a turn can say that ends the run rather than inviting another: a park is a person's to clear, there
#: is nothing to start, or another machine holds this fairway and nothing here changes that by waiting.
STOPS = (" is parked — ", "nothing to start", " is held by ")
#: Minutes a harbour may be *silent* for before a wait on it is a park, where `harbour.json` does not say.
#: `half-ahead`'s number. Silence and not elapsed time: see `await_answer`.
DEFAULT_WAIT_MINUTES = 60


def harbour() -> dict:
    try:
        held = json.loads(HARBOUR.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def stage_bound() -> float:
    """Seconds a stage may write nothing before it is ended. The longest stage's budget, because the captain
    cannot tell from outside which stage is running — only that the log has stopped."""
    stages = harbour().get("stages")
    minutes = [row.get("minutes") for row in stages.values()
               if isinstance(row, dict)] if isinstance(stages, dict) else []
    found = [one for one in minutes if isinstance(one, int | float) and one > 0]
    return (max(found) if found else DEFAULT_STAGE_MINUTES) * 60.0


def attempts() -> int:
    """Re-dispatches of `/sail` one slice may have. `0` means one run and no retry."""
    held = harbour().get("attempts")
    return held if isinstance(held, int) and held >= 0 else DEFAULT_ATTEMPTS


def wait_bound() -> float:
    """Seconds a wait may go with the harbour log silent before it is a parked line with a reason."""
    held = harbour().get("wait_bound")
    return (held if isinstance(held, int | float) and held > 0 else DEFAULT_WAIT_MINUTES) * 60.0


def harbour_entries() -> list[logs.Entry]:
    """The harbour log, or nothing where it cannot be read.

    Read rather than refused, unlike this fairway's own deck log: the harbour log is somebody else's file
    and a captain that stopped dead because of a line in it would be stopped by another fairway's fault.
    """
    path = ROOT / logs.HARBOUR
    if not path.is_file():
        return []
    try:
        return logs.fold(path.read_text(encoding="utf-8").splitlines(), harbour=True)
    except logs.Unreadable:
        return []


def fix_owed(fairway: str, found: list[logs.Entry]) -> logs.Entry | None:
    """A `fix-trunk` for this fairway that it has not answered, or None.

    Answered means a `merged` line of this fairway's, no older than the order, naming a commit that is not
    the one that went red. By commit and not by the clock alone: a timestamp is to the second, so the merge
    that answers an order can carry the same instant as the order itself, and the merge that *broke* trunk
    is the one line that carries the broken commit. The fix reaches trunk the way everything else does, so
    the line that says any slice is done is the line that says this one is.

    The harbourmaster sends the order because it wrote the `merged` line for the commit that went red, so it
    knows whose it was. A captain takes it at its next turn, ahead of any new slice, because a trunk this
    fairway reddened is worth more than anything else it could start.
    """
    orders = [e for e in harbour_entries()
              if e.kind == "fix-trunk" and str(e.fields.get("fairway", "")) == fairway]
    if not orders:
        return None
    last = orders[-1]
    broke = str(last.fields.get("commit", ""))
    answered_by = [e for e in found if e.kind == "merged" and e.t >= last.t
                   and not str(e.fields.get("commit", "")).startswith(broke[:8])]
    return None if answered_by else last


def answered(request: str) -> logs.Entry | None:
    """The harbourmaster's answer to this request, or None while there is not one yet."""
    return next((e for e in reversed(harbour_entries())
                 if e.kind in ("granted", "refused") and str(e.fields.get("request", "")) == request), None)


def await_answer(request: str, bound: float) -> logs.Entry | None:
    """Wait for the answer to one request. None where the harbour went silent for the bound.

    A captain holds no credential, so this is the one place its own progress depends on another process —
    and a wait with no bound is indistinguishable from a run that has stopped, which is why there is one.

    **What the bound is on is silence, not elapsed time**, which is the same inversion as everything else
    here: a process that wrote a line made progress. A harbourmaster's answer to a merge is on the far side
    of a fetch, a rebase and the project's whole `make verify`, and every one of those is a different length
    on a different machine — so a clock started at the request is a clock measuring the gate rather than the
    harbourmaster's health, and the number that works on a laptop parks a merge that is being gated at that
    moment on a loaded runner. Any new line in the harbour log is the harbour saying it is still there, and
    it starts the bound again. What still parks is a harbour that has stopped writing altogether, which is
    the failure the bound exists for and the only one it can honestly detect.
    """
    seen = len(harbour_entries())
    until = time.monotonic() + bound
    while True:
        found = answered(request)
        if found is not None:
            return found
        count = len(harbour_entries())
        if count > seen:
            seen, until = count, time.monotonic() + bound
        if time.monotonic() >= until:
            return None
        time.sleep(ANSWER_POLL)


def deck(feature: str, fairway: str) -> Path:
    return ROOT / logs.deck_path(feature, fairway)


def entries(feature: str, fairway: str) -> list[logs.Entry]:
    path = deck(feature, fairway)
    if not path.is_file():
        return []
    try:
        return logs.fold(path.read_text(encoding="utf-8").splitlines())
    except logs.Unreadable as fault:
        raise SystemExit(f"captain: {path} cannot be read ({fault}). The log is the state, so this is not "
                         f"something to carry on past: fix the line and start the captain again")


def write(feature: str, fairway: str, entry: logs.Entry) -> None:
    """Append one line to this fairway's own log. One writer per file, so nothing is locked."""
    path = deck(feature, fairway)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry.line())


def state(found: list[logs.Entry]) -> tuple[set[str], set[str], str]:
    """(claimed, merged, why it is parked) — the fairway, as its own lines say it is."""
    claimed = {str(e.fields["slice"]) for e in found if e.kind == "claimed"}
    merged = {str(e.fields["slice"]) for e in found if e.kind == "merged"}
    parked = next((str(e.fields["why"]) for e in reversed(found) if e.kind == "parked"), "")
    return claimed, merged, parked


def next_slice(fairway: str, claimed: set[str], merged: set[str]) -> tuple[str | None, str]:
    """The next slice this fairway may start, and why there is none where there is none.

    Split order, not sorted order: wiring is the one place two slices can depend on each other's having run,
    and the chart's own order is the order the split agreed.
    """
    charted, feature = clearance.chart()
    settled = clearance.marks_set(feature)
    mine = [slice_id for slice_id, body in (charted.get("slices") or {}).items()
            if str((body or {}).get("fairway", "")) == fairway]
    if not mine:
        return None, f"the chart gives {fairway} no slices"
    left = [slice_id for slice_id in mine if slice_id not in merged and slice_id not in claimed]
    if not left:
        return None, f"every slice of {fairway} is claimed or merged"
    for slice_id in left:
        if clearance.cleared(charted, settled, slice_id) is True:
            return slice_id, ""
    waiting = clearance.cleared(charted, settled, left[0])
    return None, f"{left[0]} waits on {waiting}"


def fire(point: str, **given: str) -> None:
    """One hook point, which never costs the rung. `hooks.py` exits 0 whatever a hook did; this does not
    even read its output, so an extension cannot change what the captain does next."""
    if not HOOKS.is_file():
        return
    argv = [sys.executable, str(HOOKS), point]
    for name, value in given.items():
        argv += [f"--{name}", value]
    subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


def sail_command(slice_id: str, fairway: str) -> tuple[list[str], dict[str, str], str]:
    """What runs the ladder for one slice: (argv, the environment it runs under, what was chosen).

    A headless session of the installed harness, asked for `/sail <slice> fairway=<name>`. The one slice is
    deliberate: the gate below is per slice — every mark *that slice's* `sets` names, plus *its* demo — and a
    dispatch handed a whole fairway would make the completion lines unattributable, which is the check that
    caught `/sail` printing a help message and exiting 0.

    `SLIPWAI_SAIL` replaces the whole thing and takes `<slice> <fairway>` after it, which is how the suite
    drives a fake and how a harness the registry does not know is pointed at. It used to fall back to
    `scripts/agents/sail.py` — the *settings reader* for `/sail`, which prints its table and exits 0 — and
    that stood in for the ladder in the first real run this loop ever did.
    """
    named = os.environ.get("SLIPWAI_SAIL")
    if named:
        return [*named.split(), slice_id, fairway], {**os.environ, **naming(slice_id, fairway)}, \
            f"SLIPWAI_SAIL: {named}"
    chosen, said = harness.choose()
    template, _ = harness.template(chosen)
    prompt = harness.prompt_for(chosen, "drive", DRIVE_COMMAND, f"{slice_id} fairway={fairway}")
    line = template.replace("{prompt}", shlex.quote(prompt)) + harness.model_flags(chosen, sail_model())
    return shlex.split(line), {**harness.child_environment(chosen), **naming(slice_id, fairway)}, said


def naming(slice_id: str, fairway: str) -> dict[str, str]:
    """What the session is told about itself, for `scripts/agents/session.py` to read at the harness's own
    moments — the guards it may be refused at and the hooks it fires.

    A session carries no argument into a hook: a hook is a command the harness runs, and the only thing it
    and the session have in common is the environment. So the four facts `session.py` needs are put there,
    and the *absence* of `SLIPWAI_FAIRWAY` is what tells a person's own `/sail` from one the captain
    dispatched — which is the difference between a control-file edit being refused and being allowed.

    `SLIPWAI_SINCE` is the instant the session opened. `before-stop` holds a turn that has written no deck
    log line, and "no line" has to mean *none since this session began*: a fairway with a hundred lines
    behind it would otherwise satisfy the test for ever.
    """
    return {"SLIPWAI_FAIRWAY": fairway, "SLIPWAI_SLICE": slice_id, "SLIPWAI_STAGE": "drive",
            "SLIPWAI_SINCE": logs.now()}


def sail_model() -> str | None:
    """The model the ladder's own session runs on, or None for the harness's default.

    `.specify/cruise.json`'s `model`, and deliberately not `models.json`'s: that file maps a *role* to a
    model per harness for the stages `/sail` delegates, and the session running `/sail` itself is the
    `host` it is all relative to. Under `/sail` typed by a person the host is whatever they opened; nobody
    opens this one, so the same value `/cruise` uses for the same question answers it. Unset means the
    harness's own default, which is a fact about the run and is said in the turn's line rather than left to
    be inferred from a transcript.
    """
    try:
        table = json.loads((ROOT / ".specify/cruise.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    named = table.get("model") if isinstance(table, dict) else None
    return named if isinstance(named, str) and named else None


def watched(process: subprocess.Popen, feature: str, fairway: str, bound: float,
            started: int) -> tuple[bool, str]:
    """Wait for `/sail`, writing a heartbeat and ending it if the log stops. (finished, why it was ended).

    What is watched is the log and not the process: a process that is alive and writing nothing is exactly
    the failure that cost the first attempt seventeen iterations, and it looks identical from the outside to
    one that is working hard.
    """
    last_line, last_beat = time.monotonic(), time.monotonic()
    seen = started
    while process.poll() is None:
        time.sleep(POLL)
        now = time.monotonic()
        count = len(entries(feature, fairway))
        if count > seen:
            seen, last_line = count, now
        if now - last_beat >= HEARTBEAT:
            write(feature, fairway, logs.entry("heartbeat", fairway=fairway))
            last_beat, seen = now, len(entries(feature, fairway))
        if now - last_line >= bound:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
            return False, (f"nothing was written to the deck log for {bound / 60:.0f} minutes, so the stage "
                           f"was ended. A stage that wrote no line made no progress")
    return process.returncode == 0, ("" if process.returncode == 0
                                     else f"`/sail` exited {process.returncode}")


def boundary(feature: str, fairway: str) -> str:
    """The inbox at a boundary, and why the fairway stops where it does.

    `inbox.owed` says a boundary is forced; this says what the next thing to happen is. Either way it is a
    person — a message nobody answered inside its bound, or a backlog of decisions nobody has read. The
    experiment reached 125 decisions with 105 of them never reviewed, which is not a record of judgement.
    """
    fire("boundary", slice="", fairway=fairway)
    owed = inbox.owed(fairway)
    if not owed.get("forced"):
        return ""
    late = owed.get("overrun") or []
    if late:
        said = str(late[0].get("message", ""))[:120]
        return (f"{len(late)} message(s) from a person have gone past the wait bound unanswered, the "
                f"oldest being {said!r}. `/told` reads them, and a read line is the receipt")
    return (f"{len(owed.get('unreviewed') or [])} decisions stand unread, over the ceiling of "
            f"{owed.get('ceiling')}. A backlog of judgement nobody has looked at is not judgement")


def sets_of(slice_id: str) -> list[str]:
    """The marks the chart says this slice publishes, which is what its gate is.

    An absent `sets` reads as none here and is refused by `make check-chart` once the split has run, where
    it can say which slice and what to write. This is the reader, not the gate.
    """
    charted, _ = clearance.chart()
    body = (charted.get("slices") or {}).get(slice_id) or {}
    return [str(mark) for mark in (body.get("sets") or [])]


def owed(fresh: list[logs.Entry], slice_id: str, promised: list[str]) -> tuple[list[str], str]:
    """What this slice still owes from the lines written this turn: (marks not set, the demo's verdict).

    The verdict is `""` where no demo was written at all, which is a different fault from one that was
    written and sent back — the first says the rung never ran, the second says a person watched it and
    wanted something changed, and they get different answers.
    """
    mine = [e for e in fresh if str(e.fields.get("slice", "")) == slice_id]
    done = {str(e.fields["mark"]) for e in mine if e.kind == "mark-set"}
    verdicts = [str(e.fields["verdict"]) for e in mine if e.kind == "demo"]
    return [mark for mark in promised if mark not in done], (verdicts[-1] if verdicts else "")


def dispatch(slice_id: str, feature: str, fairway: str) -> tuple[bool, str, list[logs.Entry]]:
    """One run of `/sail`, and the lines it wrote. (finished, why not, the lines written during it)."""
    try:
        argv, environment, _said = sail_command(slice_id, fairway)
    except harness.NoHarness as refused:
        # Not a park with a mark missing: the ladder never ran, and saying "no `mark-set` was written" about
        # a session nobody could start would send somebody to read a slice that is fine.
        return False, f"{refused}. Or set SLIPWAI_SAIL to a command taking <slice> <fairway>", []
    fire("before-stage", stage="drive", slice=slice_id, fairway=fairway)
    started = len(entries(feature, fairway))
    process = subprocess.Popen(argv, cwd=ROOT, env=environment)
    finished, why = watched(process, feature, fairway, stage_bound(), started)
    fire("after-stage", stage="drive", slice=slice_id, fairway=fairway)
    return finished, why, entries(feature, fairway)[started:]


def through_its_gate(slice_id: str, feature: str, fairway: str, bound: int) -> tuple[bool, str]:
    """Drive the slice until its gate is satisfied, or say why it will not be. (satisfied, why not).

    The gate is every mark the chart says this slice `sets`, plus a `demo`, written during the turn that
    just ran. A demo that came back is driven again, up to `attempts`; anything else stops here, because a
    turn that wrote none of what closes a slice has given no evidence that anything was built.
    """
    sent_back = 0
    promised = sets_of(slice_id)
    while True:
        finished, why, fresh = dispatch(slice_id, feature, fairway)
        if not finished:
            return False, why
        missing, verdict = owed(fresh, slice_id, promised)
        if not missing and verdict == ACCEPTED:
            return True, ""
        if verdict and verdict != ACCEPTED:
            sent_back += 1
            if sent_back <= bound:
                continue
            return False, (f"the demo came back {verdict!r} {sent_back} time(s), which is what `attempts` "
                           f"allows. The notes are in the slice; a person decides what happens next")
        if missing:
            return False, (f"the chart says {slice_id} sets {', '.join(promised)}, and this turn wrote no "
                           f"`mark-set` for {', '.join(missing)}. A stage that wrote no line made no "
                           f"progress, so nothing here is evidence the slice was built")
        return False, (f"this turn wrote no `demo` line for {slice_id}, so nothing says a person watched it "
                       f"work. `/sail` exiting 0 is the agent's account of itself, which is the one thing "
                       f"this loop does not read")


def merged(slice_id: str, feature: str, fairway: str, bound: int) -> tuple[bool, str]:
    """Ask for the merge until it lands or until asking again cannot change the answer.

    A refusal says whether a berth could fix it. A conflict and a failed gate are work on code, so `/sail`
    is dispatched again — in this fairway's own berth, where the context is — and the merge asked for
    afresh, because trunk may have moved again in the meantime. A refusal nothing here can act on stops at
    once rather than driving a slice four more times to be told the same thing.
    """
    for asked in range(bound + 1):
        landed, why, resolvable = ask_to_merge(slice_id, feature, fairway, asked)
        if landed:
            return True, ""
        if not resolvable:
            return False, why
        if asked == bound:
            return False, f"{why}. That is {asked + 1} attempt(s), which is what `attempts` allows"
        finished, fault, _ = dispatch(slice_id, feature, fairway)
        if not finished:
            return False, fault
    return False, "unreachable"


def work(slice_id: str, feature: str, fairway: str) -> tuple[bool, str]:
    """One slice, start to finish. (did it finish, why it did not)."""
    write(feature, fairway, logs.entry("claimed", fairway=fairway, slice=slice_id))
    bound = attempts()
    ok, why = through_its_gate(slice_id, feature, fairway, bound)
    if not ok:
        return False, why
    held = boundary(feature, fairway)
    if held:
        return False, held
    fire("before-merge", slice=slice_id, fairway=fairway)
    return merged(slice_id, feature, fairway, bound)


def ask_to_merge(slice_id: str, feature: str, fairway: str,
                 asked: int) -> tuple[bool, str, bool]:
    """Ask the harbourmaster to merge, and wait for its answer. (it landed, why not, worth another turn).

    A captain holds no credential, so it asks; the harbourmaster rebases, gates and advances trunk, and its
    `granted` carries the commit. `merged` is written here, in this fairway's own log, because one writer
    per file is the rule that makes every other reader safe — and because the fairway's own log is where a
    reader looks for what this fairway did.
    """
    request = f"merge-{slice_id}-{asked}" if asked else f"merge-{slice_id}"
    write(feature, fairway, logs.entry(
        "request", fairway=fairway, id=request, what="merge", slice=slice_id,
        detail=f"merge slice/{slice_id} into trunk after the full gate"))
    found = await_answer(request, wait_bound())
    if found is None:
        return False, (f"the harbourmaster did not answer {request}, and the harbour log has been silent for "
                       f"the wait bound. Nothing merges without it, and a wait with no end is "
                       f"indistinguishable from a run that stopped"), False
    if found.kind == "refused":
        why = str(found.fields.get("why", "no reason given"))
        return False, f"the merge was refused: {why}", bool(found.fields.get("resolve"))
    commit = str(found.fields.get("commit", ""))
    if not commit:
        return False, (f"the merge of {slice_id} was granted and the answer names no commit, so nothing here "
                       f"can say what trunk is at"), False
    write(feature, fairway, logs.entry("merged", fairway=fairway, slice=slice_id, commit=commit))
    return True, "", False


def fetch() -> None:
    """Trunk and both logs. Never fatal: a harbour on one machine has no remote to fetch from."""
    for argv in (["git", "fetch", "--quiet", "origin"],
                 ["git", "fetch", "--quiet", "origin", "refs/slipwai/logs/*:refs/slipwai/logs/*"]):
        subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


def turn(fairway: str) -> str:
    """One turn: what happened, as the line the command prints.

    **The claim comes before anything is written.** A fairway's deck log has one writer by rule, and
    nothing enforced it across machines: two captains for `ordering` were two processes appending to one
    file through two worktrees, which is a conflict in the file the design promised would never have one.
    So the claim ref is taken here, before the first line of the turn, and a captain that cannot take it
    writes nothing at all — not even its reason, which would be the damage done while explaining it.
    """
    fetch()
    taken = claims.take(ROOT, fairway, logs.machine())
    if not taken.ours:
        return f"captain: {taken.why}"
    if taken.why:
        # Taken, with something to say about it — a harbour that is not a git repository, where nothing can
        # hold a fairway and a second captain cannot be refused. Said and carried on from, because a project
        # without git has no berths and no merges either, and this is not where that is refused.
        print(f"captain: {taken.why}", flush=True)
    _, feature = clearance.chart()
    found = entries(feature, fairway)
    claimed, merged, parked = state(found)
    if parked:
        return f"captain: {fairway} is parked — {parked}"
    fix = fix_owed(fairway, found)
    if fix is not None:
        slice_id, why = str(fix.fields["slice"]), ""
        print(f"captain: trunk is red at {str(fix.fields['commit'])[:8]} ({fix.fields['job']}) and "
              f"{fairway} merged it; fixing {slice_id} before anything new", flush=True)
    else:
        slice_id, why = next_slice(fairway, claimed, merged)
    if slice_id is None:
        return f"captain: nothing to start in {fairway} — {why}"
    done, fault = work(slice_id, feature, fairway)
    if done:
        return f"captain: {slice_id} is through its gate and merged"
    write(feature, fairway, logs.entry("parked", fairway=fairway, why=f"{slice_id}: {fault}"))
    return f"captain: {fairway} parked at {slice_id} — {fault}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="captain", description="Run one fairway: claim, dispatch, watch the log, ask for the merge")
    parser.add_argument("fairway", help="the fairway this captain is for, as the chart names it")
    parser.add_argument("--once", action="store_true", help="one slice, rather than the loop")
    parser.add_argument("--interval", type=float, default=30.0, help="seconds between turns")
    parsed = parser.parse_args(argv)
    try:
        while True:
            said = turn(parsed.fairway)
            print(said, flush=True)
            if parsed.once or any(mark in said for mark in STOPS):
                return 0
            time.sleep(parsed.interval)
    finally:
        # The claim is given back whichever way the loop ended, including the park. A captain that kept it
        # would hold the fairway against every other machine until somebody went looking for a ref — and a
        # captain killed outright still does, which is what 11.2's lease is for.
        claims.release(ROOT, parsed.fairway, logs.machine())


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
