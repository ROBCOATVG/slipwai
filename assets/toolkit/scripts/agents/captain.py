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

**An open question is a park with the question in it, and the answer becomes the decision.** A stage that
meets a product question it may not guess past writes a `question` line and ends; the gate used to read
that as *wrote no `mark-set`*, which sent a person to look for a slice that was never built. Now the park
names the question, `/cruise-tell` with the answer clears it, and the captain writes the `decision` line
carrying the question's `id` before it re-dispatches — so the resumed `/sail` finds the question answered
in the log rather than in somebody's memory, and clearance stops saying *awaiting decision*.

**A stop is a line, and the slice it interrupted is carried on.** `fleet.py stop` is a SIGTERM, and a captain
with no handler for it died where it stood: the `/sail` it had dispatched ran on with nothing watching it,
the claim stayed taken, and the log said nothing — so the next captain lit on the same machine took its own
claim back, found no park to resume from, stepped past the claimed slice and said *nothing to start* for
ever. Now the signal ends the running stage, `stopped` names the slice, the claim is given back once that
line has travelled, and a slice claimed and not merged is resumed whatever interrupted it.

**Every ready slice runs, each in a berth of its own, up to what the harbour gives this fairway.** The
captain used to dispatch `/sail <slice>` once a turn — the single-slice form, "that slice, and nothing
else" — so a fairway of twenty-two independent slices ran them one after another while a person typing
`/sail` had all twenty-two fanned out. Now a turn starts every slice `clearance.py` admits and the slice
graph lets run together, up to the `slots` the harbourmaster has given this fairway (`abreast.py` is the
rule; a fairway it has said nothing about runs one), and refills from the ready set as each one merges or
parks while any is still running. Each slice is a thread here with its own session, berth (`moorings.py`),
stage bound, retries, `.working` marker, gate and merge request; this process stays the one writer of the
fairway's log, under one lock, because the slices' threads are the only other hands on the file and a lock
in one process is the whole of what serialising them takes. Threads rather than a poll loop because the
slice's own path — dispatch, watch, retry, ask, wait — was already a sequence written for one slice, and
the wait in each step is a process or a file, never this interpreter. A park on one slice holds that slice
and not its siblings; a stop ends every one and writes a `stopped` line for each.

**A hook never costs the rung.** The extension hook points fire around each rung, at each boundary and before
a merge; `hooks.py` always exits 0 for them, and the captain does not read their output. A hook is a second
belt, and a second belt that can stop the run is the thing it was meant to be instead of.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import abreast  # noqa: E402
import claims  # noqa: E402
import clearance  # noqa: E402
import fleet  # noqa: E402
import harness  # noqa: E402
import inbox  # noqa: E402
import logs  # noqa: E402
import moorings  # noqa: E402
import travel  # noqa: E402


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
#: How often a turn with room to spare asks clearance again when nothing has woken it. A sibling's
#: `mark-set` clears a slice without ending anything, so it wakes nobody; asking at every poll would be
#: the chart parsed and trunk's history read every two seconds for an answer that changes by the minute.
LOOK = 15.0
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
STOPS = (" is parked — ", "nothing to start", " is held by ", " yields its berth to ")
#: Minutes a harbour may be *silent* for before a wait on it is a park, where `harbour.json` does not say.
#: `half-ahead`'s number. Silence and not elapsed time: see `await_answer`.
DEFAULT_WAIT_MINUTES = 60
#: What a slice's branch is called, which `check-slice-scope` holds every branch to and the harbourmaster
#: rebases. A taken-over stream's branch arrives under this name, because that is the name `/sail` expects
#: to find its own work on.
BRANCH = "slice/{slice}"
#: The fairway and feature this captain is on, and whether a stop is being honoured.
ON: dict[str, str] = {}
#: Every slice in flight, each with the session running it, its berth, and whether it is waiting on a merge
#: answer — what a stop ends and names, and what back-pressure reads. Empty between slices: a captain that
#: has written no `claimed` has nothing to name and, until its claim is taken, no right to write at all.
FLIGHT: dict[str, dict[str, object]] = {}
#: Held around every read and append of the deck log. Several slices' threads write into one file, and the
#: rule that makes every reader safe is one writer per file — one process, and inside it one lock.
LOCK = threading.RLock()
#: Set by a stop, and read by every slice's thread at each poll, so each one ends its own session and
#: leaves without writing anything after the stop: the `stopped` lines are the main thread's to write.
STOP = threading.Event()
#: What wakes the turn between polls: a slice's thread finishing, or one leaving its merge wait, which is
#: when a fairway held back by its pending merge may start its next slice.
BOUNDARY: queue.Queue[str] = queue.Queue()


class Stopped(Exception):
    """The captain was asked to stop. Raised by the SIGTERM handler wherever the captain is, so that every
    `finally` between there and `main` runs — the one in `dispatch` that ends the stage, and the one in
    `main` that gives the claim back."""


def on_term(signum: int, _frame: object) -> None:
    """The first SIGTERM is a stop; a second, while the first is being honoured, is *now*.

    The second matters because honouring the first waits for the final line to travel, up to the wait
    bound, and a person who asks twice has said they will not wait for it. The claim is then kept, which is
    what the lease is for.
    """
    if ON.get("stopping"):
        raise SystemExit(128 + signum)
    ON["stopping"] = "yes"
    STOP.set()
    raise Stopped()


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
    """Every machine's harbour log as one history, or nothing where it cannot be read.

    Read rather than refused, unlike this fairway's own deck log: a harbour log is somebody else's file and
    a captain that stopped dead because of a line in one would be stopped by another machine's fault.
    """
    try:
        return logs.harbour_fold(ROOT)
    except (logs.Unreadable, OSError, UnicodeDecodeError):
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
        # Every poll, because the answer can only come from a harbourmaster that is running, and one that
        # died while this waited would otherwise cost the slice its gate at the end of the bound.
        if STOP.is_set():
            raise Stopped()
        keep_harbourmaster()
        found = answered(request)
        if found is not None:
            return found
        count = len(harbour_entries())
        if count > seen:
            seen, until = count, time.monotonic() + bound
        if time.monotonic() >= until:
            return None
        time.sleep(ANSWER_POLL)


def keep_harbourmaster() -> None:
    """Start the harbourmaster again where it has died, and say so.

    Every captain checks, because nothing else would: `fleet.py relight` never starts one, and the
    harbourmaster is the only thing that fills free berths and answers a merge. `fleet.relight_harbourmaster`
    holds the one-harbourmaster rule — it restarts only what a pid file says was started and is now gone,
    and only one of two captains that both noticed does it.
    """
    pid = fleet.relight_harbourmaster()
    if pid is not None:
        print(f"captain: the harbourmaster had stopped, so it was started again, pid {pid}. Its output is "
              f"in .slipwai/running/harbourmaster.out", flush=True)


def deck(feature: str, fairway: str) -> Path:
    return ROOT / logs.deck_path(feature, fairway)


def entries(feature: str, fairway: str) -> list[logs.Entry]:
    path = deck(feature, fairway)
    if not path.is_file():
        return []
    try:
        with LOCK:
            text = path.read_text(encoding="utf-8")
        return logs.fold(text.splitlines())
    except logs.Unreadable as fault:
        raise SystemExit(f"captain: {path} cannot be read ({fault}). The log is the state, so this is not "
                         f"something to carry on past: fix the line and start the captain again")


def write(feature: str, fairway: str, entry: logs.Entry) -> None:
    """Append one line to this fairway's own log. One writer per file — this process — and inside it one lock,
    because several slices' threads append at once and an interleaved half-line is a log nobody can fold."""
    path = deck(feature, fairway)
    path.parent.mkdir(parents=True, exist_ok=True)
    with LOCK, path.open("a", encoding="utf-8") as handle:
        handle.write(entry.line())


def state(found: list[logs.Entry], fairway: str = "") -> tuple[str, dict[str, str]]:
    """(why the whole fairway is parked, each slice parked on its own) — as its own lines say.

    A park naming a `slice` holds that slice alone: its siblings were never waiting on its question, and a
    fairway that stopped for it would be one person's answer costing every other slice its afternoon.
    """
    name = fairway or next((str(e.fields.get("fairway", "")) for e in found), "")
    parks = logs.open_parks(found, harbour_entries(), name)
    whole = logs.fairway_parks(parks)
    return (str(whole[-1].fields["why"]) if whole else ""), logs.held_slices(parks)


def displaced_by(fairway: str) -> str:
    """The fairway holding the berth this one would have had, or `""` while it still has one — slice 18.2.

    `boilers` is how many berths are lit at once and the harbour's fairway priority is which streams get
    them, so a person who moves a stream up while a run is going pushes another one below the line. This is
    what that captain reads to find out, and it reads it at a slice boundary rather than at once: a stage
    ended half-way to free a berth has freed nothing and lost the work.

    **Only where another fairway is actually holding a berth.** An unbounded harbour lights everything and
    displaces nobody; `boilers: 0` lights nothing, which is the telegraph at `stop` and is a different
    question from priority — a captain stopping because the whole harbour stopped is not a captain yielding
    to a stream, and writing a `yielded` line naming nobody would say it was.
    """
    given = abreast.granted(harbour_entries(), fairway)
    if given is not None:
        # The harbourmaster has shared the boilers out, and its line is the answer: a fairway it gave
        # nothing, with work, names the fairway the slot went to. Read before the older rule below, which
        # assumed one session per captain and would yield a berth the allocation had just given it.
        return str(given.fields.get("to", "")) if not given.fields.get("slots") else ""
    held = harbour().get("boilers")
    if not isinstance(held, int) or isinstance(held, bool) or held <= 0:
        return ""
    charted, _ = clearance.chart()
    order = clearance.fairway_order(charted, clearance.preferred_fairways(HARBOUR))
    lit = order[:held]
    return "" if not lit or fairway in lit or fairway not in order else lit[-1]


def next_slices(fairway: str, beside: list[str]) -> tuple[list[str], str]:
    """Every slice this fairway may start now beside the ones in flight, in split order, and why there is
    none where there is none.

    Split order, not sorted order: wiring is the one place two slices can depend on each other's having run,
    and the chart's own order is the order the split agreed. **Which slices may start is clearance's
    answer** — every `depends_on` merged, every mark steered by set, no question open, no park — and which of
    them may run *together* is the slice graph's `parallel_ok_with`, read by `abreast.ready`. Nothing here is
    a second definition of either.
    """
    charted, feature = clearance.chart()
    mine = [str(slice_id) for slice_id, body in (charted.get("slices") or {}).items()
            if str((body or {}).get("fairway", "")) == fairway]
    if not mine:
        return [], f"the chart gives {fairway} no slices"
    folded_logs = clearance.with_evidence(charted, clearance.folded(clearance.lines(feature)))
    done = clearance.done_marked(feature)
    found = abreast.ready(charted, folded_logs, done, fairway, beside)
    if found:
        return found, ""
    left = [one for one in mine if one not in folded_logs.merged and one not in folded_logs.claimed
            and one not in beside]
    if not left:
        return [], f"every slice of {fairway} is claimed or merged"
    state, why = clearance.position(charted, folded_logs, left[0], done)
    return [], (f"{left[0]} may run, and not beside {', '.join(beside)}, which the slice graph's "
                f"parallel_ok_with leaves out" if state in abreast.READY else f"{left[0]} waits on {why}")


def fire(point: str, **given: str) -> None:
    """One hook point, which never costs the rung. `hooks.py` exits 0 whatever a hook did; this does not
    even read its output, so an extension cannot change what the captain does next."""
    if not HOOKS.is_file():
        return
    argv = [sys.executable, str(HOOKS), point]
    for name, value in given.items():
        argv += [f"--{name}", value]
    subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


def sail_command(slice_id: str, fairway: str, retry: str = "",
                 berth: Path | None = None) -> tuple[list[str], dict[str, str], str]:
    """What runs the ladder for one slice: (argv, the environment it runs under, what was chosen).

    A headless session of the installed harness, asked for `/sail <slice> fairway=<name>`. The one slice is
    deliberate: the gate below is per slice — every mark *that slice's* `sets` names, plus *its* demo — and a
    dispatch handed a whole fairway would make the completion lines unattributable, which is the check that
    caught `/sail` printing a help message and exiting 0.

    `SLIPWAI_SAIL` replaces the whole thing and takes `<slice> <fairway>` after it, which is how the suite
    drives a fake and how a harness the registry does not know is pointed at. It used to fall back to
    `scripts/agents/sail.py` — the *settings reader* for `/sail`, which prints its table and exits 0 — and
    that stood in for the ladder in the first real run this loop ever did.

    `retry` is why the run before this one did not close the gate, where there was one. It is said to the
    session in its prompt and in `SLIPWAI_RETRY`, as a demo sent back says its notes in the slice: a retry
    told nothing re-runs the ladder blind and meets the same wall the same way.

    `berth` is the slice's own worktree, where the session is started. It is told so, because the ladder
    otherwise makes a worktree for the slice it is given, and `slice/<id>` is already checked out here.
    """
    named = os.environ.get("SLIPWAI_SAIL")
    if named:
        return [*named.split(), slice_id, fairway], {**os.environ, **naming(slice_id, fairway, retry, berth)}, \
            f"SLIPWAI_SAIL: {named}"
    chosen, said = harness.choose()
    template, _ = harness.template(chosen)
    prompt = harness.prompt_for(chosen, "drive", DRIVE_COMMAND, f"{slice_id} fairway={fairway}")
    if berth is not None:
        prompt += (f"\n\nYou are already in this slice's berth: the worktree at {berth}, on branch "
                   f"{BRANCH.format(slice=slice_id)}. Work there, and make no other worktree for it; its "
                   f"`.slipwai/logs` is the project's own.")
    if retry:
        prompt += (f"\n\nThe last run of this slice did not close its gate: {retry}. Re-enter at the first "
                   f"incomplete stage and close what it left.")
    line = template.replace("{prompt}", shlex.quote(prompt)) + harness.model_flags(chosen, sail_model())
    return shlex.split(line), {**harness.child_environment(chosen), **naming(slice_id, fairway, retry, berth)}, \
        said


def naming(slice_id: str, fairway: str, retry: str = "", berth: Path | None = None) -> dict[str, str]:
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
    told = {"SLIPWAI_RETRY": retry} if retry else {}
    if berth is not None:
        told["SLIPWAI_BERTH"] = str(berth)
    return {"SLIPWAI_FAIRWAY": fairway, "SLIPWAI_SLICE": slice_id, "SLIPWAI_STAGE": "drive",
            "SLIPWAI_SINCE": logs.now(), **told}


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


def head(branch: str) -> str:
    """The commit that branch is at, or `""` where it does not exist yet."""
    found = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
                           cwd=ROOT, capture_output=True, text=True)
    return found.stdout.strip() if found.returncode == 0 else ""


def end(process: subprocess.Popen) -> None:
    """End a dispatched stage, and everything it started.

    The session is started in a process group of its own so that this can reach its delegates as well: a
    harness that is told to stop and leaves a delegate running leaves an agent writing into a berth nobody
    is watching, which is the untracked work a stop exists to prevent. Windows has no process groups to
    signal, so there it is the session itself.
    """
    if process.poll() is not None:
        return
    group = getattr(os, "killpg", None)
    try:
        if group is not None:
            group(process.pid, signal.SIGTERM)
        else:  # pragma: no cover - the other platform's branch
            process.terminate()
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        if group is not None:
            group(process.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
        else:  # pragma: no cover - the other platform's branch
            process.kill()
        process.wait()
    except ProcessLookupError:
        pass


def mine(found: list[logs.Entry], slice_id: str) -> list[logs.Entry]:
    """The lines that are this slice's: those naming it, and — while it is the only slice in flight — those
    naming none, which is every line a session wrote before a fairway ran several slices at once.

    With siblings in flight a line naming no slice is nobody's in particular, so it counts for none of them:
    a session that stopped writing is not kept alive by a sibling's heartbeat, which is the one mistake a
    shared log invites and the reason every line that matters carries `slice`.
    """
    alone = len(FLIGHT) <= 1
    return [e for e in found if str(e.fields.get("slice", "")) == slice_id
            or (alone and not e.fields.get("slice"))]


def watched(process: subprocess.Popen, feature: str, fairway: str, slice_id: str, bound: float,
            started: int, branch: str = "") -> tuple[bool, str]:
    """Wait for `/sail`, writing a heartbeat and ending it if the log stops. (finished, why it was ended).

    What is watched is the log and not the process: a process that is alive and writing nothing is exactly
    the failure that cost the first attempt seventeen iterations, and it looks identical from the outside to
    one that is working hard. **The log as this slice's lines**, by their `slice` field: several slices now
    write into one fairway's log, and a silent one must not be kept alive by its siblings.

    **A commit on the slice's branch is progress too.** It is evidence in git, not the agent's account of
    itself, and the implement rung writes one per example and no deck line until its mark: an S1 that
    committed fourteen times in ninety minutes was ended fifty-one seconds after the last of them, as a
    stage that "made no progress".
    """
    last_line, last_beat = time.monotonic(), time.monotonic()
    seen = len(mine(entries(feature, fairway)[started:], slice_id))
    at = head(branch) if branch else ""
    while process.poll() is None:
        time.sleep(POLL)
        if STOP.is_set():
            end(process)
            raise Stopped()
        now = time.monotonic()
        count = len(mine(entries(feature, fairway)[started:], slice_id))
        if count > seen:
            seen, last_line = count, now
        moved = head(branch) if branch else ""
        if moved != at:
            at, last_line = moved, now
        if now - last_beat >= HEARTBEAT:
            write(feature, fairway, logs.entry("heartbeat", fairway=fairway, slice=slice_id))
            last_beat, seen = now, len(mine(entries(feature, fairway)[started:], slice_id))
        if now - last_line >= bound:
            end(process)
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


def open_questions(found: list[logs.Entry], slice_id: str) -> list[logs.Entry]:
    """The `question` lines against this slice no `decision` has answered: open until one carries the `id`."""
    answered = {str(e.fields.get("id", "")) for e in found if e.kind == "decision"}
    return [e for e in found if e.kind == "question" and str(e.fields.get("slice", "")) == slice_id
            and str(e.fields.get("id", "")) not in answered]


def park_answer(found: list[logs.Entry], fairway: str, slice_id: str = "") -> str:
    """What a person answered the latest park on this slice with: the `what` of the harbour `cleared`
    receipt that names that park's timestamp. A park of the whole fairway is a park on every slice in it.
    `""` where the park is still open or there never was one."""
    parks = [e for e in found if e.kind == "parked" and str(e.fields.get("fairway", "")) == fairway
             and str(e.fields.get("slice", "") or slice_id) == slice_id]
    if not parks:
        return ""
    for receipt in reversed(harbour_entries()):
        if (receipt.kind == "cleared" and str(receipt.fields.get("fairway", "")) == fairway
                and str(receipt.fields.get("parked", "")) == parks[-1].t):
            return str(receipt.fields.get("what", ""))
    return ""


def answer_questions(feature: str, fairway: str, slice_id: str, found: list[logs.Entry]) -> list[str]:
    """Turn the answer to a park into the `decision` lines the open questions owe, and say which.

    One answer may close several questions: the park listed every one of them, and the person answered the
    park. A question answered this way carries `decided by: human`, which is what it was.
    """
    what = park_answer(found, fairway, slice_id)
    if not what:
        return []
    closed = []
    for asked in open_questions(found, slice_id):
        ident = str(asked.fields.get("id", ""))
        write(feature, fairway, logs.entry("decision", fairway=fairway, id=ident, what=what,
                                           slice=slice_id, decided_by="human"))
        closed.append(ident)
    return closed


class NeverRan(Exception):
    """No session could be started at all. Not a run that failed, so not one a retry is spent on."""


def dispatch(slice_id: str, feature: str, fairway: str,
             retry: str = "") -> tuple[bool, str, list[logs.Entry]]:
    """One run of `/sail`, in the slice's berth, and the lines it wrote. (finished, why not, the lines
    written during it — every slice's, for the caller to read its own out of by `slice`)."""
    flying = FLIGHT.setdefault(slice_id, {})
    held = flying.get("berth")
    berth = held if isinstance(held, Path) and held.resolve() != ROOT.resolve() else None
    try:
        argv, environment, _said = sail_command(slice_id, fairway, retry, berth)
    except harness.NoHarness as refused:
        # Not a park with a mark missing: the ladder never ran, and saying "no `mark-set` was written" about
        # a session nobody could start would send somebody to read a slice that is fine.
        raise NeverRan(f"{refused}. Or set SLIPWAI_SAIL to a command taking <slice> <fairway>") from refused
    fire("before-stage", stage="drive", slice=slice_id, fairway=fairway)
    started = len(entries(feature, fairway))
    if STOP.is_set():
        raise Stopped()
    # A session of its own, so that `end` reaches the delegates it starts as well as the session; and a
    # `Session`, so that one which said it was finished and stayed is ended rather than waited out.
    process = harness.Session(argv, berth or ROOT, environment)
    flying["process"] = process
    try:
        finished, why = watched(process, feature, fairway, slice_id, stage_bound(), started,
                                BRANCH.format(slice=slice_id))
    finally:
        # A stop, a Ctrl-C, anything that leaves mid-stage: the stage ends with the captain, never after it.
        end(process)
        flying.pop("process", None)
    fire("after-stage", stage="drive", slice=slice_id, fairway=fairway)
    return finished, why, entries(feature, fairway)[started:]


def own_parks(fresh: list[logs.Entry], fairway: str, slice_id: str) -> list[logs.Entry]:
    """The parks a run of this slice wrote about itself: naming it, or — written by a session that named no
    slice — naming the whole fairway while this was the only slice in flight or saying its id in the why."""
    return [e for e in fresh if e.kind == "parked" and str(e.fields.get("fairway", "")) == fairway
            and (str(e.fields.get("slice", "")) == slice_id
                 or (not e.fields.get("slice") and (len(FLIGHT) <= 1 or slice_id in str(e.fields.get("why", "")))))]


def through_its_gate(slice_id: str, feature: str, fairway: str, bound: int) -> tuple[bool, str]:
    """Drive the slice until its gate is satisfied, or say why it will not be. (satisfied, why not).

    The gate is every mark the chart says this slice `sets`, plus a `demo`, written during the turn that
    just ran. **Every run that misses it is a retry, up to `attempts`** — a demo sent back, a mark not set,
    no demo, a stage ended for silence, `/sail` exiting non-zero. Only the sent-back demo used to be one,
    and the rest parked on the first run, so a session that fell over once cost a person a visit to a slice
    a second run would have finished. Each retry is told why the last did not close, and the park, when
    `attempts` is spent, carries the last reason and the count.

    Two things are not retried, because a second run cannot change them: an open question, which only a
    person answers, and a session that parked itself, whose reason is already the newest line.
    """
    tried, retry = 0, ""
    promised = sets_of(slice_id)
    while True:
        try:
            finished, why, fresh = dispatch(slice_id, feature, fairway, retry)
        except NeverRan as refused:
            return False, str(refused)
        tried += 1
        own = own_parks(fresh, fairway, slice_id)
        if own:
            return False, str(own[-1].fields.get("why", ""))
        if finished:
            missing, verdict = owed(fresh, slice_id, promised)
            if not missing and verdict == ACCEPTED:
                return True, ""
            asked = open_questions(fresh, slice_id)
            if asked:
                # Before the mark check: a stage that stopped to ask is not a stage that wrote nothing, and
                # the park has to carry the question, because the person reading it answers it.
                said = "; ".join(f"{e.fields.get('id')}: {e.fields.get('what')}" for e in asked)
                return False, (f"{slice_id} is awaiting a decision — {said}. A person answers with "
                               f"`/cruise-tell {fairway} <answer>`; the captain records the decision and "
                               f"resumes {slice_id}")
            why = gate_missed(slice_id, promised, missing, verdict)
        if tried <= bound:
            retry = why
            print(f"captain: {slice_id} run {tried} did not close its gate — {why}. Running it again",
                  flush=True)
            continue
        return False, f"{why}. That was the last of {tried} run(s), which is what `attempts` allows"


def gate_missed(slice_id: str, promised: list[str], missing: list[str], verdict: str) -> str:
    """Why a run that finished did not close the gate, in the words the park and the retry carry."""
    if verdict and verdict != ACCEPTED:
        return f"the demo came back {verdict!r}. The notes are in the slice; a person decides what happens next"
    if missing:
        return (f"the chart says {slice_id} sets {', '.join(promised)}, and this turn wrote no `mark-set` "
                f"for {', '.join(missing)}. A stage that wrote no line made no progress, so nothing here is "
                f"evidence the slice was built")
    return (f"this turn wrote no `demo` line for {slice_id}, so nothing says a person watched it work. "
            f"`/sail` exiting 0 is the agent's account of itself, which is the one thing this loop does not "
            f"read")


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
        # Back into its berth to resolve, which is work on code and no longer a wait on the queue.
        FLIGHT.setdefault(slice_id, {})["merging"] = False
        try:
            finished, fault, _ = dispatch(slice_id, feature, fairway, why)
        except NeverRan as refused:
            return False, str(refused)
        FLIGHT.setdefault(slice_id, {})["merging"] = True
        if not finished:
            return False, fault
    return False, "unreachable"


def working(fairway: str, slice_id: str) -> Path:
    """Where this machine records which captain process is working one of the fairway's slices right now.

    One file per slice, because one per fairway held one pid for one slice and a fairway now has several in
    flight: a second captain reading it would have resumed every slice but the one it named.
    """
    return fleet.RUNNING / f"captain-{fairway}--{slice_id}.working"


def worked_here(fairway: str, slice_id: str) -> int | None:
    """Another live captain process on this machine that is on this slice, or None.

    The claim names a machine, not a process, so a captain a person runs by hand beside one the fleet lit
    takes the same claim and reads the same log. Before every claimed slice was resumed that cost nothing:
    the second skipped what the first had claimed. Now it would resume a slice that is being worked, so a
    claimed slice is carried on only when the process recorded as working it has gone — which is every
    case a resume is for, since a stop, a kill and a reboot all leave a dead pid behind or none at all.
    """
    for path in (working(fairway, slice_id), fleet.RUNNING / f"captain-{fairway}.working"):
        # The second is the one file per fairway a captain from before kept, for its one slice: honoured
        # while such a captain is still alive here, so an upgrade mid-run does not resume what it is on.
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if pid != os.getpid() and fleet.alive(pid):
            return pid
    return None


def moored(slice_id: str) -> tuple[Path | None, str]:
    """The slice's berth, or the project's checkout where it may stand in for one. (where, why not).

    **A fairway held to one slice at a time — `abreast: 1` — is worked in the checkout**, exactly as every
    slice was before a fairway ran several: one session, so nothing to collide with, and the ladder makes
    the slice its worktree as *Running ready slices concurrently* says. Otherwise every slice gets a berth,
    the first as much as the rest, because the first is the one the others are about to join. The
    checkout also stands in while nothing else is in flight where no berth can be made — a harbour with no
    commit yet. With a sibling running, the checkout is the one place two sessions would collide, so a
    slice with no berth of its own does not start.
    """
    if abreast.width(harbour()) == 1:
        return ROOT, ""
    base = clearance.trunk() or "HEAD"
    found, why = moorings.berth(ROOT, slice_id, BRANCH.format(slice=slice_id), base)
    if found is not None:
        if why:
            print(f"captain: {slice_id}: {why}", flush=True)
        return found, ""
    if len(FLIGHT) <= 1:
        return ROOT, ""
    return None, f"it has no berth of its own and a sibling is in flight, so it did not start: {why}"


def work(slice_id: str, feature: str, fairway: str) -> tuple[bool, str]:
    """One slice, start to finish. (did it finish, why it did not). Run in a thread of its own."""
    # Recorded before the `claimed` line, so a captain that reads the line also finds whose it is.
    working(fairway, slice_id).parent.mkdir(parents=True, exist_ok=True)
    working(fairway, slice_id).write_text(f"{os.getpid()}\n", encoding="utf-8")
    try:
        berth, why = moored(slice_id)
        if berth is None:
            return False, why
        FLIGHT.setdefault(slice_id, {})["berth"] = berth
        write(feature, fairway, logs.entry("claimed", fairway=fairway, slice=slice_id))
        bound = attempts()
        ok, why = through_its_gate(slice_id, feature, fairway, bound)
        if not ok:
            return False, why
        # Through its gate is already on its way to the merge queue, and holds the fairway's next slice back
        # from here rather than from the request line: the inbox and the hook in between take a moment, and a
        # sibling started in it would meet the trunk this slice is about to move.
        FLIGHT.setdefault(slice_id, {})["merging"] = True
        held = boundary(feature, fairway)
        if held:
            return False, held
        fire("before-merge", slice=slice_id, fairway=fairway)
        landed, why = merged(slice_id, feature, fairway, bound)
        if landed:
            kept = moorings.leave(ROOT, berth)
            if kept:
                print(f"captain: {slice_id} merged; {kept}", flush=True)
        return landed, why
    finally:
        if worked_here(fairway, slice_id) is None:
            working(fairway, slice_id).unlink(missing_ok=True)


def ask_to_merge(slice_id: str, feature: str, fairway: str,
                 asked: int) -> tuple[bool, str, bool]:
    """Ask the harbourmaster to merge, and wait for its answer. (it landed, why not, worth another turn).

    A captain holds no credential, so it asks; the harbourmaster rebases, gates and advances trunk, and its
    `granted` carries the commit. `merged` is written here, in this fairway's own log, because one writer
    per file is the rule that makes every other reader safe — and because the fairway's own log is where a
    reader looks for what this fairway did.
    """
    request = f"merge-{slice_id}-{asked}" if asked else f"merge-{slice_id}"
    # Waiting on a merge answer is what holds the fairway's next slice back: the harbourmaster gates one
    # merge at a time, and a slice started now would only meet the trunk this one is about to move.
    FLIGHT.setdefault(slice_id, {})["merging"] = True
    write(feature, fairway, logs.entry(
        "request", fairway=fairway, id=request, what="merge", slice=slice_id,
        detail=f"merge slice/{slice_id} into trunk after the full gate"))
    try:
        found = await_answer(request, wait_bound())
    finally:
        BOUNDARY.put(slice_id)
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
    """Trunk, every log and every in-flight branch. Never fatal: a harbour on one machine has no remote."""
    subprocess.run(["git", "fetch", "--quiet", "origin"], cwd=ROOT, capture_output=True, text=True)
    travel.fetch(ROOT)


def lease() -> float:
    """Seconds this fairway's holder may go unheard from before this captain may take it over.

    Derived from `stage_bound` and never chosen, which is the berth rule: a captain that writes nothing for
    `stage_bound` ends that stage itself and says so, so a lease above it cannot take a stream from a
    captain that is working — the guarantee falls out rather than being asserted — and it moves with the
    telegraph for free, because `stage_scale` multiplies every stage budget.
    """
    return travel.lease(stage_bound())


def heard(feature: str, fairway: str) -> str:
    """When this fairway's holder was last heard from: the later of its pushed log and the one here.

    The pushed log is the honest evidence across machines — what one machine can know about another is
    exactly what the other has pushed — and it is the only evidence where the holder is somewhere else.
    But a harbour with no forge pushes nothing, and there two captains under two names share one file: the
    local log is then the only evidence there is, and a lease judged without it would take a stream off a
    captain writing into the very file this one is reading.

    So the later of the two, always. More evidence of life can only make a lease *less* likely to fire,
    which is the safe direction: the one thing a lease may never do is take a stream from somebody working.
    """
    found = entries(feature, fairway)
    return max(travel.last_heard(ROOT, travel.deck_ref(fairway)), found[-1].t if found else "")


def resuming(found: list[logs.Entry]) -> list[str]:
    """The slices this stream was in the middle of: claimed, and not merged — every one of them.

    Whatever stopped them — a lapsed lease, a park since cleared, a `stopped` line, or a machine that went
    down mid-stage and wrote nothing at all. The last is why this asks only the claim: a captain relit on
    the same machine takes its own claim back, so nothing says *taken over*, and with no park either the
    slice used to be stepped past as claimed — *nothing to start* for ever, with four rungs of work on it.
    A slice is let go only by merging; nothing else in a fairway's log hands one back. **Every one**, since a
    fairway runs several at once: the reader this replaced took the last claimed, and a fairway stopped with
    three in flight came back to one of them.
    """
    return logs.unmerged(found)


def take_over(feature: str, fairway: str, from_machine: str) -> tuple[list[str], str]:
    """Bring a lapsed stream's work over before anything is dispatched. (the slices to resume, why not).

    Two things travel and both have to arrive. **The lines**, so that this captain knows what the stream
    was on and so that nothing it appends is written over the top of a log the ref is ahead of — a deck log
    is one chain per fairway, and taking the claim is taking the pen. **The branches**, one per slice in
    flight, because a captain holds no credential and a slice branch lives only on the machine that built
    it: a lapsed claim whose work never travelled leaves four rungs of it unreachable, and carrying on as
    though it had not would discard them in silence. That is why the lease was refused on its own.
    """
    travel.land_ref(ROOT, travel.deck_ref(fairway))
    slices = resuming(entries(feature, fairway))
    for slice_id in slices:
        ref = travel.wip_ref(fairway, slice_id)
        if not travel.tip(ROOT, ref) and len(slices) == 1:
            ref = travel.wip_ref(fairway)  # pushed by a machine from before a branch travelled per slice
        landed, why = travel.land_wip(ROOT, ref, BRANCH.format(slice=slice_id))
        if not landed:
            return [], (f"{fairway} was taken over from {from_machine}, which was working {slice_id}, and its "
                        f"work did not come with it: {why}")
    for slice_id in slices:
        write(feature, fairway, logs.entry("taken-over", fairway=fairway, slice=slice_id,
                                           **{"from": from_machine}))
    return slices, ""


def allowed(fairway: str, flying: int, found: list[logs.Entry]) -> int:
    """How many slices this fairway may have in flight now. One while none is; more only on the
    harbourmaster's word.

    The first slice is the captain's by being lit, which is what `boilers` gave it before it meant
    sessions. A slice beyond that needs a `slots` line, and one written **since the fairway's last slice
    ended**: a merge or a park frees a session the harbourmaster re-offers by its own rules — breadth
    first, so a fairway with nothing running may be owed it — and a captain that refilled from the number
    it held before would take a slot that was never its own to take again. With no `slots` line at all the
    answer is one, which is exactly what every captain did before there was one.
    """
    if flying == 0:
        return 1
    given = abreast.granted(harbour_entries(), fairway)
    if given is None:
        return 1
    ended = max((e.t for e in found if e.kind in ("merged", "stopped", "parked")), default="")
    if given.t < ended:
        return flying
    count = given.fields.get("slots")
    return min(count if isinstance(count, int) else 1, abreast.width(harbour()))


def finished(feature: str, fairway: str, slice_id: str, done: bool, fault: str, since: int, alone: bool) -> str:
    """The line a slice's end prints, and the park it writes where it did not merge.

    The session parked itself, with the reason it met: a second park on top of it would say what the gate
    missed (no `demo`, a mark not set), which is true of every stage that stops early and hides the reason
    it stopped behind the newest line a person reads. **A slice parked while siblings run holds itself
    alone** — the park names its `slice` — and one parked as the fairway's only slice holds the fairway,
    as every park did before several slices ran at once.
    """
    if done:
        return f"captain: {slice_id} is through its gate and merged"
    own = own_parks(entries(feature, fairway)[since:], fairway, slice_id)
    if own:
        return f"captain: {fairway} parked at {slice_id} — {own[-1].fields.get('why', '')}"
    named = {} if alone else {"slice": slice_id}
    write(feature, fairway, logs.entry("parked", fairway=fairway, why=f"{slice_id}: {fault}", **named))
    return f"captain: {fairway} parked at {slice_id} — {fault}"


def sail_out(feature: str, fairway: str, first: list[str], fresh: bool) -> list[str]:
    """Run slices until none is in flight: `first` before anything new, then the ready set, refilled at
    every boundary while any slice is still running. What each one's end said, in the order they ended.

    A turn ends when the last slice in flight ends, so with one slice allowed a turn is one slice — the
    captain as it was. `fresh` says whether new slices may be started at all, which a fix owed to trunk
    and a fairway past the lit line both say they may not.
    """
    threads: dict[str, threading.Thread] = {}
    results: dict[str, tuple[bool, str, bool]] = {}
    said: list[str] = []
    queued = list(first)
    since = len(entries(feature, fairway))
    looked, woken, was = 0.0, True, 0
    while True:
        found = entries(feature, fairway)
        if not ON.get("drained"):
            limit = allowed(fairway, len(threads), found)
            # A new number from the harbourmaster is a boundary too: it is the room a merge elsewhere freed.
            woken, was = woken or limit != was, limit
            merging = any(bool(flying.get("merging")) for flying in list(FLIGHT.values()))
            parked, _ = state(found, fairway)
            if not merging and not parked and len(threads) < limit:
                if fresh and len(queued) < limit - len(threads) and (woken or time.monotonic() - looked >= LOOK):
                    looked, woken = time.monotonic(), False
                    more, _ = next_slices(fairway, [*threads, *queued])
                    queued += more
                starting = queued[:max(0, limit - len(threads))]
                for slice_id in starting:
                    alone = not threads
                    FLIGHT[slice_id] = {}
                    thread = threading.Thread(target=run_one, args=(slice_id, feature, fairway, alone, results),
                                              name=f"slice-{slice_id}", daemon=True)
                    threads[slice_id] = thread
                    thread.start()
                queued = [one for one in queued if one not in threads]
                if starting:
                    # The allowance is read again at once: the first slice was the lit right, the rest are slots.
                    woken = True
                    continue
        if not threads:
            return said
        try:
            BOUNDARY.get(timeout=POLL)
            woken = True
        except queue.Empty:
            pass
        for slice_id in [one for one, thread in threads.items() if not thread.is_alive()]:
            threads.pop(slice_id).join()
            done, fault, alone = results.pop(slice_id, (False, "the slice's thread ended without a word", True))
            FLIGHT.pop(slice_id, None)
            line = finished(feature, fairway, slice_id, done, fault, since, alone and not threads)
            print(line, flush=True)
            said.append(line)
        if not threads:
            # The last one has ended: the turn is over, as a single slice's turn always was. Nothing more
            # is started from here — the next turn reads the log afresh, and with one slice allowed that is
            # exactly the captain this was.
            ON["drained"] = "yes"


def run_one(slice_id: str, feature: str, fairway: str, alone: bool,
            results: dict[str, tuple[bool, str, bool]]) -> None:
    """One slice's thread: its whole path, and its answer left where the turn reads it. A stop ends it
    with nothing written — the `stopped` line is the main thread's, once every session is ended."""
    try:
        done, fault = work(slice_id, feature, fairway)
        results[slice_id] = (done, fault, alone)
    except NeverRan as refused:
        results[slice_id] = (False, str(refused), alone)
    except Stopped:
        results[slice_id] = (False, "stopped", alone)
    except Exception as fault:  # noqa: BLE001 - a slice's fault is its own park, never its siblings' end
        results[slice_id] = (False, f"the captain met {type(fault).__name__}: {fault}", alone)
    finally:
        BOUNDARY.put(slice_id)


def turn(fairway: str) -> str:
    """One turn: what happened, as the lines the command prints.

    **The claim comes before anything is written.** A fairway's deck log has one writer by rule, and
    nothing enforced it across machines: two captains for `ordering` were two processes appending to one
    file through two worktrees, which is a conflict in the file the design promised would never have one.
    So the claim ref is taken here, before the first line of the turn, and a captain that cannot take it
    writes nothing at all — not even its reason, which would be the damage done while explaining it.
    """
    keep_harbourmaster()
    fetch()
    ON.pop("drained", None)
    # The chart before the claim, because working out whether the holder is still alive means reading this
    # fairway's log, and reading it means knowing which feature it is under. Nothing is written by either.
    _, feature = clearance.chart()
    taken = claims.take(ROOT, fairway, logs.machine(), lease=lease(), heard=heard(feature, fairway))
    if not taken.ours:
        return f"captain: {taken.why}"
    ON.update(feature=feature, fairway=fairway)
    if taken.why:
        # Taken, with something to say about it — a harbour that is not a git repository, where nothing can
        # hold a fairway and a second captain cannot be refused; or a stream taken over past its lease.
        # Said and carried on from, because a project without git has no berths and no merges either, and
        # this is not where that is refused.
        print(f"captain: {taken.why}", flush=True)
    resume: list[str] = []
    stranded = ""
    if taken.took_over:
        resume, stranded = take_over(feature, fairway,
                                     taken.holder.machine if taken.holder else "another machine")
    found = entries(feature, fairway)
    parked, held = state(found, fairway)
    if parked:
        return f"captain: {fairway} is parked — {parked}"
    if stranded:
        write(feature, fairway, logs.entry("parked", fairway=fairway, why=stranded))
        return f"captain: {fairway} parked — {stranded}"
    # Claimed and not merged is this stream's own work, whatever left it there: a cleared park, a stop, a
    # reboot. A slice still parked on its own is left until it is cleared, and one another captain on this
    # machine is working is left to it.
    resume = [one for one in (resume or resuming(found))
              if one not in held and worked_here(fairway, one) is None]
    fix = fix_owed(fairway, found)
    if fix is not None:
        slice_id = str(fix.fields["slice"])
        print(f"captain: trunk is red at {str(fix.fields['commit'])[:8]} ({fix.fields['job']}) and "
              f"{fairway} merged it; fixing {slice_id} before anything new", flush=True)
        said = sail_out(feature, fairway, [slice_id], fresh=False)
    elif resume:
        # The stream was mid-slice when it stopped, and the ready set steps past a slice that is claimed —
        # which is exactly the four rungs of work each of these exists to carry over.
        for slice_id in resume:
            for ident in answer_questions(feature, fairway, slice_id, found):
                print(f"captain: {ident} on {slice_id} is decided by the answer to the park", flush=True)
        said = sail_out(feature, fairway, resume, fresh=True)
    else:
        # The boundary a yield is taken at — slice 18.2. Here and nowhere else: a fix owed to trunk is
        # still owed, and a slice carried over from a park is claimed work this stream is holding, so
        # both are above it. What is below it is starting something *new* in a berth the run wants for
        # another stream, which is the one thing giving the berth up actually saves.
        giving_up = displaced_by(fairway)
        if giving_up:
            write(feature, fairway, logs.entry("yielded", fairway=fairway, to=giving_up))
            return f"captain: {fairway} yields its berth to {giving_up}"
        first, why = next_slices(fairway, [])
        if not first:
            return f"captain: nothing to start in {fairway} — {why}"
        said = sail_out(feature, fairway, first[:1], fresh=True)
    # Nothing started at all is a turn with nothing to start, said in the words that end the loop: a turn
    # that printed nothing would go round again for ever, saying nothing each time.
    return "\n".join(said) or f"captain: nothing to start in {fairway} — nothing could be started this turn"


def release_after_publication(fairway: str) -> None:
    """Give the pen back only after the final local suffix is durable on the forge.

    Publication stays the harbourmaster's job. Releasing first lets a new captain take the free claim
    and read a log missing the final merged or parked line. A timeout retains the claim and names the
    publisher to restart, so the next pass can publish before another captain is handed the pen.
    """
    machine = logs.machine()
    found = claims.holder(ROOT, fairway)
    if found is None or found.machine != machine or not found.held():
        return
    if travel.forge(ROOT):
        _, feature = clearance.chart()
        path = deck(feature, fairway)
        local = path.read_text(encoding="utf-8") if path.is_file() else ""
        until = time.monotonic() + wait_bound()
        while local:
            travel.fetch(ROOT)
            published = travel.held(ROOT, travel.deck_ref(fairway)) or ""
            if travel.appends(local, published):
                break
            if time.monotonic() >= until:
                print(f"captain: {fairway}'s final deck lines have not travelled, so its claim is "
                      f"retained. Run `python3 scripts/agents/harbourmaster.py --once` on {machine}, "
                      f"then `python3 scripts/agents/captain.py {fairway} --once` to publish and release",
                      flush=True)
                return
            time.sleep(min(ANSWER_POLL, max(0.0, until - time.monotonic())))
    claims.release(ROOT, fairway, machine)


def stopped(fairway: str) -> None:
    """End every slice in flight and say so in the log, one `stopped` line each, before the claim is given
    back.

    Every session is ended here as well as by its own thread's `finally`, because a thread that is waiting
    on a merge answer or a hook has no session to end and would otherwise be what the stop waits for. Only
    slices that were in flight are named: between slices this captain has written nothing this turn and may
    not hold the claim at all, and a line written without it is the second writer the claim exists to refuse.
    """
    STOP.set()
    flying = list(FLIGHT)
    for slice_id in flying:
        process = FLIGHT.get(slice_id, {}).get("process")
        if isinstance(process, subprocess.Popen):
            end(process)
    for thread in [one for one in threading.enumerate() if one.name.startswith("slice-")]:
        thread.join(timeout=60)
    feature = ON.get("feature", "")
    if flying and ON.get("fairway") == fairway:
        for slice_id in flying:
            write(feature, fairway, logs.entry("stopped", fairway=fairway, slice=slice_id))
        print(f"captain: {fairway} stopped mid-way through {', '.join(flying)}; "
              f"{'it is' if len(flying) == 1 else 'they are'} carried on when the fairway is lit again", flush=True)
    else:
        print(f"captain: {fairway} stopped between slices", flush=True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="captain", description="Run one fairway: claim, dispatch, watch the log, ask for the merge")
    parser.add_argument("fairway", help="the fairway this captain is for, as the chart names it")
    parser.add_argument("--once", action="store_true", help="one slice, rather than the loop")
    parser.add_argument("--interval", type=float, default=30.0, help="seconds between turns")
    parsed = parser.parse_args(argv)
    signal.signal(signal.SIGTERM, on_term)
    try:
        while True:
            said = turn(parsed.fairway)
            # The turn's slices are merged or parked by now, so a stop while sleeping interrupts nothing.
            FLIGHT.clear()
            print(said, flush=True)
            if parsed.once or any(mark in said for mark in STOPS):
                return 0
            time.sleep(parsed.interval)
    except Stopped:
        stopped(parsed.fairway)
        return 0
    finally:
        # The final line must travel while this captain still holds the pen. A captain killed outright
        # still leaves its claim behind, which is what 11.2's lease is for.
        release_after_publication(parsed.fairway)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
