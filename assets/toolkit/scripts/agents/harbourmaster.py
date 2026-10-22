#!/usr/bin/env python3
"""The harbourmaster: the one writer of the harbour log, and the only thing in a harbour that holds a credential.

One process per harbour. Its job is two things that both come from the same rule — **one writer per file** —
and a third that comes from a different one.

**It carries between fairways.** A captain writes its own deck log and reads everybody's, but a fairway that
had to read every other fairway's log to find the one line it needed would be reading a hundred files to find
three. So the handful of lines that matter across fairways — a mark set, a park, a berth allocated, a flag
changed — are copied into the harbour log, which has exactly one writer and therefore never conflicts.

**It allocates berths.** A captain asks by writing `berth-request`; the answer is `berth-allocated` in the
harbour log. The numbers are arithmetic (`berths.py`), so nobody chooses one and nobody chooses the same one
twice — but somebody has to decide the order, and one writer deciding it is the whole of the mechanism.

**It holds the credentials, and that is the different rule.** A berth is a sandbox; a berth with a token in
it is a sandbox with a way out. So a captain asks for a push, a merge, a deploy, a flag change or a publish
by writing a `request` line, and this process does it or refuses with the reason. What it will never do is a
closed list, and it is checked against the request's own text rather than trusted to the asker:

    destroy data or history · release what nobody asked for · spend money · expose a secret ·
    weaken security · discard a person's commits · change a gate to make it pass

**Both outcomes are written.** A refusal that left no line is one the captain waits on for ever and nobody
can explain afterwards. That is the same rule as every other log line here: a thing that wrote no line did
not happen.

**And a merge is performed, not just permitted.** For a long while `granted` was written and read by nothing,
no `merged` line was written by anything, and the board said `merged: 0` for ever while slices were being
accepted at their demos. A granted merge now rebases the slice branch onto trunk in a scratch worktree of
this process's own, runs the project's own gate there, and advances trunk — then `granted` carries the
commit, and the captain writes `merged` into its own log against it.

Four things about how, each of which was a choice:

- **One at a time, in the order they were asked.** Each gate then runs on a trunk that already holds every
  merge before it, so a green result is evidence about the trunk the commit will actually land on. Gating
  two in parallel wins nothing, because `make verify` is a whole-repo gate and a result measured against a
  trunk that has since moved has to be measured again.
- **A scratch worktree, never the berth.** The berth belongs to a captain that may still be writing in it,
  and the person's own checkout belongs to the person. `make verify` needs no ports and no Docker — the
  in-memory adapter is what the port's contract runs against — so the scratch worktree needs no berth
  resources and is removed either way.
- **The gate is the project's own `make verify`.** Exactly what the two-gate rule already names, so a
  project that adds a check gets it at the merge for nothing. `make ci` was rejected because it wants
  Docker or the network and a laptop without them could then never merge; a gate narrowed to the changed
  paths was rejected because a narrow gate that passes where `verify` would fail is the worst outcome
  available.
- **A conflict is aborted and refused, naming the paths.** `git rebase --abort`, so nothing is left
  half-done, and the captain resolves in its own berth — where the context is — and asks again. This
  process stays credentials-and-gate only, which matters because it is the one thing here with push rights.

**And trunk's own CI is read before any merge is granted, so the fleet stops adding to a red build.** The
gate above is `make verify`; CI runs `make ci`, which adds `audit` and `test-integration` — so trunk can go
red from a check `verify` never ran, and without this nothing would notice while every fairway kept merging
onto it. A red trunk is harbour-wide rather than one fairway's fault, which is why it is a harbour line and
not just a refusal.

Red refuses every merge and writes `trunk-red` naming the commit and the job; the queue drains the moment
trunk is green again, which is written once as `trunk-green`. Drains, and not just reopens: each fairway
that parked on that refusal gets a `cleared` receipt from this process, because a captain that was told
*no* parks, and a park nobody here clears is a stop no person caused and none should have to undo. A forge
this cannot reach reads *could not verify*, never *green*: the merge still goes ahead — a harbour with no
forge has to keep working — and the `granted` line says the CI was unverified, so nobody reads it later as
a run that was checked.

**The fix goes to the captain that broke it, not to a person.** This process wrote the `merged` line for the
commit that went red, so it knows the fairway and the slice: `fix-trunk` names them, and that captain takes
the fix at its next turn ahead of any new slice. A red trunk no `merged` line accounts for — a direct push,
or a red older than any merge — parks for a person at once, because guessing who broke it would send a
captain to rewrite somebody else's work.

Standalone and dependency-free, like everything under `scripts/`: this runs inside a generated project, which
has no slipwai to import. `logs.py` and `berths.py` beside it are the keel's own modules, carried here by
`make shared` and byte-identical to their source.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import berths  # noqa: E402
import claims  # noqa: E402
import inbox  # noqa: E402
import logs  # noqa: E402
import telegraph  # noqa: E402
import travel  # noqa: E402


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
#: Where this process keeps how far it has read each deck log. A cursor, not a copy: the logs are the truth
#: and this is only a bookmark, so losing it costs a re-read and never a line.
CURSORS = ROOT / ".slipwai/harbourmaster.json"
#: The numbers this harbour is held to, and the lever over them. Watched rather than read once: a person
#: rings the telegraph while the run is going, which is the only time ringing it is any use.
HARBOUR_CONFIG = ROOT / "harbour.json"
#: Which deck-log kind becomes which harbour-log kind. Everything not here stays in the fairway's own log,
#: because the harbour log is what every captain reads on every turn and a line nobody needs is a line
#: everybody pays for.
CARRIED = {"mark-set": "mark-set", "parked": "park"}
#: Who wrote a `told`, where it says. Only a person's answers a park: the board and `/cruise-tell` write it.
PERSON = "person"
#: What a captain's park at the decision ceiling waits on. Cleared by reading, never by a message.
REVIEW = "decision-review"
#: What a request may ask for at all. A closed set: an action nobody wrote down is one nobody reviewed.
ACTIONS = ("push", "merge", "deploy", "flag", "publish")
#: What is never done, whoever asks and whatever the reason. Matched against the request's own text, because
#: the asker is the thing being checked and its own summary of what it is asking is not evidence.
NEVER: tuple[tuple[str, str], ...] = (
    (r"\bpush\b[^\n]*--force(?!-with-lease)", "a plain force-push discards somebody's commits"),
    (r"\bgit\s+reset\s+--hard\b", "a hard reset discards work that is not yours to discard"),
    (r"\bgit\s+clean\b", "a clean deletes files nobody has read"),
    (r"\bbranch\s+-D\b|\bpush\b[^\n]*--delete\b", "deleting a branch destroys history"),
    (r"\bdrop\s+(table|database|schema)\b|\btruncate\s+table\b", "that destroys data"),
    (r"\brm\s+-rf\b", "that destroys data"),
    (r"\bfilter-branch\b|\bfilter-repo\b|\brebase\b[^\n]*\b--root\b", "that rewrites history"),
    (r"(?i)\b(aws_secret|api[_-]?key|password|token)\s*=", "that puts a secret in a log line"),
    (r"(?i)\bdisable\b[^\n]*\b(tls|ssl|verification|signature|auth)", "that weakens security"),
    (r"(?i)--no-verify\b|--skip-checks?\b", "that skips the gate rather than passing it"),
)
HEARTBEAT = 15.0
#: How many of trunk's runs to read. Enough to see every workflow of the newest commit that has any, few
#: enough that the forge is asked one small question.
RUNS_READ = 20
#: What a completed run's conclusion means. Anything else — `cancelled`, `action_required`, a word a forge
#: adds next year — is *not a verdict*, and a verdict is the one thing this must not invent.
GREEN = ("success", "skipped", "neutral")
RED = ("failure", "timed_out", "startup_failure")
#: Where a merge is rebased and gated. Under `.slipwai/` so it is ignored by git and swept with the rest.
SCRATCH = ROOT / ".slipwai/merge"
#: What the branch for a slice is called, which `check-slice-scope` holds every branch to as well. Read
#: from `travel`, which is where it has to be one name: two spellings travel as two pieces of work.
BRANCH = travel.BRANCH
#: Used where nothing says otherwise. `origin/HEAD` answers it on a repository with a remote.
DEFAULT_TRUNK = "main"
#: How a push refused because trunk moved on the forge reads in git's own words: `[rejected] ...
#: (non-fast-forward)` where the local copy is behind, `(fetch first)` where the forge has commits it has
#: never seen. Read off stderr because the exit code is `1` for every refusal alike.
MOVED_UNDER = re.compile(r"\[rejected\][^\n]*\((non-fast-forward|fetch first)\)")
#: How many times a merge whose push lost the race to trunk is fetched, rebased and gated again before it
#: is refused. Each time is a whole `make verify`, and the slice already passed one, so this is not a
#: question about the slice: it is whether trunk is quiet long enough to land on. Three covers the busy
#: case — a few people pushing by hand while a fleet merges — and a trunk that moves under four gates in a
#: row is one that something pushes to faster than this can gate, which the refusal then says.
PUSH_RACES = 3
#: What a merge refused only because trunk was red carries, so that the park it causes can be told apart
#: from every other park when trunk comes back: a field and not the refusal's prose, which gets reworded.
GREEN_TRUNK = "green-trunk"


def read_cursors() -> dict[str, int]:
    try:
        held = json.loads(CURSORS.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return {str(key): int(value) for key, value in held.items()} if isinstance(held, dict) else {}


def write_cursors(held: dict[str, int]) -> None:
    CURSORS.parent.mkdir(parents=True, exist_ok=True)
    CURSORS.write_text(json.dumps(held, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def deck_logs() -> list[Path]:
    """Every fairway's log, in a stable order. No harbour log is one of them: they are the output."""
    return logs.deck_logs(ROOT)


def new_lines(path: Path, cursors: dict[str, int]) -> tuple[list[str], int]:
    """The lines of this log the harbourmaster has not read, and where it has now read to.

    A cursor past the end of its log is a cursor that is about a file that no longer exists — a fresh
    clone, a reset, a log somebody rotated — and keeping it would have this carry nothing from that stream
    for ever while reporting that it ran. So it is dropped and the log is read whole: the harbour log is
    append-only and `carried` writes what the lines mean, so re-reading costs a duplicate line and
    believing a stale cursor costs every line after it.

    A log replaced by one of exactly the same length is not caught, and would need a fingerprint per log
    to catch. The case this is for is a reset or a fresh clone, where the log is much shorter — and a
    guard that cost a hash of every log on every pass to close a case nobody has had is the wrong trade.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return [], cursors.get(key_of(path), 0)
    seen = cursors.get(key_of(path), 0)
    if seen > len(lines):
        print(f"harbourmaster: {key_of(path)} is shorter than it was; reading it from the start",
              file=sys.stderr)
        seen = 0
    return lines[seen:], len(lines)


def key_of(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def config() -> dict:
    try:
        held = json.loads(HARBOUR_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def at() -> str:
    """Where the telegraph is, as the file says."""
    return str(config().get("position", telegraph.POSITIONS[0]))


def last_telegraph() -> str:
    """The position the harbour log last said, so a change is written once and not on every pass."""
    for entry in reversed(harbour_entries()):
        if entry.kind in ("telegraph", "fires-banked"):
            return str(entry.fields.get("position") or entry.fields.get("step") or "")
    return ""


def rung() -> list[logs.Entry]:
    """A `telegraph` line where the file has moved since the last one. Captains read it and adjust at their
    next boundary — not immediately, because a stage ended half-way to save a few tokens has saved nothing."""
    # No `harbour.json` is no telegraph, not `full-ahead`: writing a position into the log for a harbour
    # that never declared one would have the captains adjust to a lever nobody rang.
    if not HARBOUR_CONFIG.is_file():
        return []
    here = at()
    if here == last_telegraph() or here not in telegraph.SETTINGS:
        return []
    return [logs.entry("telegraph", harbour=True, position=here)]


def spent_today() -> int:
    """Thousands of input tokens the harbour has spent since midnight, from the lines that record it.

    From the logs rather than from a counter: a counter is state kept somewhere other than where the work
    happened, which is the mistake this whole method is built around not making.
    """
    today = logs.now()[:10]
    total = 0
    for path in deck_logs():
        try:
            found = logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError, logs.Unreadable):
            continue
        for entry in found:
            tokens = entry.fields.get("tokens")
            if entry.t[:10] == today and isinstance(tokens, int | float):
                total += int(tokens)
    return total


def bank() -> list[logs.Entry]:
    """Step the position down one notch where the day's bunker is spent, or nothing.

    One notch at a time, and never straight to `stop`: a run that stops dead at the end of the day loses
    whatever was in flight, and a run that slows keeps finishing what it started.
    """
    here = at()
    allowed = config().get("bunker_per_day")
    if here not in telegraph.SETTINGS or not isinstance(allowed, int | float) or allowed <= 0:
        return []
    spent = spent_today()
    if spent < allowed:
        return []
    down = telegraph.slower(here)
    if down is None:
        return []
    write_position(down)
    return [logs.entry("fires-banked", harbour=True, step=down,
                       why=f"the day's bunker of {int(allowed)}k is spent ({spent}k), so the fires are "
                           f"banked one notch from {here}")]


def write_position(name: str) -> None:
    """Ring the telegraph down, in the file, so the next pass and every reader sees the same thing."""
    held = config()
    whole = telegraph.applied(name, held)
    if isinstance(held.get("stages"), dict):
        whole["stages"] = telegraph.scaled(held["stages"], float(whole["stage_scale"]))
    HARBOUR_CONFIG.write_text(json.dumps(whole, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git(*argv: str, where: Path | None = None) -> subprocess.CompletedProcess[str]:
    """One git command, never raising: every caller here reads the code and says what it means."""
    return subprocess.run(["git", *argv], cwd=where or ROOT, capture_output=True, text=True, check=False)


def trunk() -> str:
    """The branch a merge lands on: what `harbour.json` says, else what the remote calls its head, else main."""
    named = config().get("trunk")
    if isinstance(named, str) and named:
        return named
    found = git("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    head = found.stdout.strip().removeprefix("origin/") if found.returncode == 0 else ""
    return head or DEFAULT_TRUNK


def gate() -> list[str]:
    """The project's own full gate, where its Makefile is.

    `layout.delivery` is `.` in a generated project and a subdirectory in an adopted one, which is the same
    answer `./init` writes into the agent's own instructions — read from the manifest rather than assumed,
    because a repository that keeps its Makefile elsewhere would otherwise be ungateable here.
    """
    try:
        manifest = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
        delivery = str((manifest.get("layout") or {}).get("delivery") or ".")
    except (OSError, ValueError, UnicodeDecodeError):
        delivery = "."
    return ["make", "verify"] if delivery == "." else ["make", "-f", f"{delivery}/Makefile", "verify"]


def base() -> str:
    """What to rebase onto: the remote's trunk where there is one, else the local branch."""
    name = trunk()
    return f"origin/{name}" if git("rev-parse", "--verify", "--quiet", f"origin/{name}").returncode == 0 else name


def conflicting() -> list[str]:
    """The paths a rebase stopped on, read before it is aborted — afterwards there is nothing to read."""
    found = git("diff", "--name-only", "--diff-filter=U", where=SCRATCH)
    return sorted({line.strip() for line in found.stdout.splitlines() if line.strip()})


def advance(name: str, commit: str) -> tuple[str, str, bool]:
    """Move trunk to this commit. (what went wrong, what was done to the person's checkout, trunk moved).

    The third says the forge refused the push because trunk is no longer where the fetch found it — some
    other machine or person pushed in between. That is not a fault in the slice or in anything a person
    must decide, so `merge` reads it as *gate it again on the new trunk* rather than as a refusal.

    Pushed where there is a remote, because then nobody's working tree is touched and every checkout catches
    up on its own next fetch. With no remote there is only the local ref — and if the person's own checkout
    is sitting on trunk, moving the ref under it would leave their working tree looking like a mass
    deletion, so that case is a fast-forward in their checkout.

    **A person's uncommitted changes never stop the run.** For a long while they did: any edit on trunk
    refused the merge, the refusal was not one a berth could fix, and the fairway parked behind a slice that
    had already passed its gate — a whole voyage stopped by an `AGENTS.md` nobody had committed. Git's own
    fast-forward already refuses only where the merge would overwrite a changed file, so it is asked first.
    Where it does refuse, the checkout is detached exactly where it stands — working tree and index
    untouched — and the ref moves on without it: the person's work is all still there, and switching back
    to trunk is theirs to do when they have committed or stashed it.
    """
    if git("rev-parse", "--verify", "--quiet", "origin/" + name).returncode == 0:
        pushed = git("push", "origin", f"{commit}:refs/heads/{name}")
        if pushed.returncode == 0:
            return "", "", False
        return last_line(pushed), "", bool(MOVED_UNDER.search(pushed.stderr or ""))
    head = git("symbolic-ref", "--quiet", "--short", "HEAD")
    if head.returncode == 0 and head.stdout.strip() == name:
        moved = git("merge", "--ff-only", commit)
        if moved.returncode == 0:
            return "", "", False
        if not git("status", "--porcelain", "--untracked-files=no").stdout.strip():
            return last_line(moved), "", False  # clean, so the refusal is about the history and is git's
        detached = git("checkout", "--quiet", "--detach")
        if detached.returncode != 0:
            return last_line(detached), "", False
        note = (f"this checkout was on {name} with uncommitted changes the merge would overwrite, so it was "
                f"detached where it stood with those changes untouched, and {name} moved on without it. "
                f"Commit or stash them, then `git switch {name}`")
    else:
        note = ""
    moved = git("update-ref", f"refs/heads/{name}", commit)
    return ("" if moved.returncode == 0 else last_line(moved)), note, False


def last_line(done: subprocess.CompletedProcess[str]) -> str:
    """The sentence git ended on, which is the one that says what it refused."""
    said = (done.stderr or done.stdout).strip().splitlines()
    return said[-1] if said else f"git exited {done.returncode}"


HOOKS = ROOT / "scripts/extensions/hooks.py"


def fire(point: str, **given: str) -> None:
    """One hook point, which never costs the merge. The twin of `captain.fire`, and deliberately a second
    small copy rather than a shared import: these two processes are started separately, run on different
    machines in the general case, and a module one of them imported from the other would be a dependency
    between two things whose whole design is that neither waits on the other.

    `hooks.py` exits 0 whatever a hook did and this does not read its output, so an extension cannot change
    what the harbourmaster does next — which matters more here than anywhere, because what it does next is
    move trunk.
    """
    if not HOOKS.is_file():
        return
    argv = [sys.executable, str(HOOKS), point]
    for name, value in given.items():
        argv += [f"--{name}", value]
    subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


#: How often `refs/slipwai/merge` is tried again while another machine holds it. A merge is a rebase and a
#: whole `make verify`, so there is nothing to gain by asking faster than this.
MERGE_POLL = 5.0
#: Minutes to wait for the merge ref where `harbour.json` says nothing. `wait_bound`'s own default, because
#: it is the same question — how long a wait may last before it is a line somebody has to read.
DEFAULT_MERGE_WAIT = 60


def merge_wait() -> float:
    """Seconds this machine will wait for another machine's merge before saying so."""
    held = config().get("wait_bound")
    return (held if isinstance(held, int | float) and held > 0 else DEFAULT_MERGE_WAIT) * 60.0


def merge_lease() -> float:
    """Seconds the merge ref's holder may go without renewing it before another machine takes it over.

    **Half the wait, and derived rather than chosen**, for two reasons that pull opposite ways. Under the
    wait, because a waiting machine has to be able to take a dead holder's ref *before* its own wait runs
    out — a dead holder last renewed no later than the moment the waiter started, so a lease shorter than
    the wait always lapses inside it, and the waiter merges instead of refusing and parking a fairway for a
    person. And not much under it, because the holder's `since` is the holder's clock read by another
    machine's, and half an hour of slack makes any skew two machines plausibly have irrelevant.

    The length of a merge does not enter into it: `make verify` can outlast any lease worth having, so the
    holder renews while the gate runs (`gated`) and a live merge never lapses however long it takes.
    """
    return merge_wait() / 2


def renew_every() -> float:
    """How often the holder renews the merge ref while its gate runs: four times a lease, so one renewal
    lost to a forge that did not answer still leaves three before anybody could call it gone."""
    return merge_lease() / 4


def taken_over(found: claims.Claim) -> None:
    """Write that the merge ref was taken off another machine, straight into this machine's harbour log.

    Written now rather than with the pass's other lines, because what follows is a rebase and a whole gate,
    and a harbourmaster killed during it would otherwise have taken the ref and left nothing saying from
    whom. The line is this process's own — the one writer of this file is still the one writing it.
    """
    print(f"harbourmaster: took {claims.MERGE} over from {found.machine}, which last renewed it at "
          f"{found.since} and is past its lease", flush=True)
    append([logs.entry("merge-taken-over", harbour=True, **{"from": found.machine, "since": found.since})])


def take_the_merge() -> tuple[bool, str]:
    """Take `refs/slipwai/merge`, waiting while another machine has it. (taken, why not).

    Waiting *is* queueing: the loser of the race sits on the ref rather than refusing at once, because a
    merge is a rebase and a whole gate and the machine ahead will be some minutes.

    **A holder that has not renewed within `merge_lease` is taken over**, exactly as a fairway's claim is,
    and the harbour log says from whom. Until it was, a machine that took the ref and was killed before it
    could give it back stopped every other machine's merges for the wait bound and then parked the fairway
    that asked — a stop that needed a person on the dead machine to run `--release`, for a lock whose
    holder was provably gone. The bound is still there for the one case a lease cannot settle: a holder
    that keeps renewing and never finishes, which is a line a person has to read.
    """
    until = time.monotonic() + merge_wait()
    while True:
        taken = claims.take(ROOT, claims.MERGE, logs.machine(), lease=merge_lease())
        if taken.ours:
            if taken.took_over and taken.holder is not None:
                taken_over(taken.holder)
            return True, ""
        if time.monotonic() >= until:
            holder = taken.holder
            who = holder.machine if holder is not None else "another machine"
            since = f" since {holder.since}" if holder is not None else ""
            return False, (f"{who} has been merging{since} and still holds {claims.MERGE}, which is taken "
                           f"for one merge at a time so that two machines never rebase onto one trunk at "
                           f"once. It is still renewing the ref, so it is alive; if it is stuck, free it "
                           f"there with `python3 scripts/agents/claims.py --release {claims.MERGE}`")
        time.sleep(MERGE_POLL)


def gated(where: Path) -> subprocess.CompletedProcess[str]:
    """The project's gate in the scratch worktree, renewing the merge ref while it runs.

    The gate is the one part of a merge that can be long — a whole `make verify` — and while it runs this
    process writes nothing anywhere, so without a renewal a slow suite would look exactly like a dead
    machine and another harbourmaster would take the ref over mid-gate. `communicate` with a timeout is
    asked again after each renewal, which is what the standard library says to do with one that expired.
    """
    argv = gate()
    with subprocess.Popen(argv, cwd=where, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True) as running:
        while True:
            try:
                out, err = running.communicate(timeout=renew_every())
                break
            except subprocess.TimeoutExpired:
                claims.renew(ROOT, claims.MERGE, logs.machine())
    return subprocess.CompletedProcess(argv, running.returncode, out, err)


def still_ours() -> bool:
    """Whether this machine still holds the merge ref, asked once the gate is over and before trunk moves.

    A renewal the forge never took, or a machine with a clock far enough out to think this one gone, can
    leave another harbourmaster holding the ref while this one finishes its gate. Moving trunk then would
    be the two-rebases-onto-one-trunk the ref exists to prevent, so this is asked rather than assumed.
    """
    found = claims.held_by(ROOT, claims.MERGE)
    return found is not None and found.machine == logs.machine()


def land(branch: str, spent: dict[str, int]) -> tuple[str, str, bool, str, bool]:
    """One fetch, rebase, gate and advance of this branch. `merge`'s answer, plus whether trunk moved.

    The last says the push lost a race to trunk and nothing else went wrong, which is the one outcome
    `merge` answers by doing this again. Its own scratch worktree each time, removed whichever way it ends.
    """
    git("fetch", "--quiet", "origin", trunk())
    onto = base()
    git("worktree", "remove", "--force", str(SCRATCH))  # a worktree left by a run that was killed
    SCRATCH.parent.mkdir(parents=True, exist_ok=True)
    made = git("worktree", "add", "--quiet", "--detach", str(SCRATCH), branch)
    if made.returncode != 0:
        return "", f"a worktree for {branch} could not be made ({(made.stderr or made.stdout).strip()})", \
            False, "", False
    try:
        rebased = git("rebase", onto, where=SCRATCH)
        if rebased.returncode != 0:
            paths = conflicting()
            git("rebase", "--abort", where=SCRATCH)
            return "", (f"{branch} conflicts with {onto} in {', '.join(paths) or 'files git did not name'}. "
                        f"The rebase was aborted, so nothing is half-done; resolve it in your own berth and "
                        f"ask again"), True, "", False
        started = time.monotonic()
        done = gated(SCRATCH)
        spent["gate_s"] = spent.get("gate_s", 0) + round(time.monotonic() - started)
        if done.returncode != 0:
            said = [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]
            return "", (f"the full gate failed on {branch} rebased onto {onto}: "
                        f"{said[-1] if said else 'no output'}"), True, "", False
        if not still_ours():
            # `resolve` true, because nothing is wrong with the slice and nothing needs a person: the next
            # ask queues behind whoever has the ref now and gates again on the trunk they leave.
            return "", (f"{branch} passed the gate and {claims.MERGE} was taken over by another machine "
                        f"before trunk was moved, so trunk was left alone; ask again"), True, "", False
        commit = git("rev-parse", "HEAD", where=SCRATCH).stdout.strip()
        fault, note, raced = advance(trunk(), commit)
        if fault:
            return "", f"{branch} passed the gate and trunk could not be moved: {fault}", False, "", raced
        return commit, "", False, note, False
    finally:
        git("worktree", "remove", "--force", str(SCRATCH))


def merge(slice_id: str, spent: dict[str, int] | None = None) -> tuple[str, str, bool, str]:
    """Rebase this slice onto trunk, gate it there, and advance trunk.

    `(commit, "", False, note)` where it landed — the note saying what was done to the person's checkout to
    land it, if anything — or `("", why not, whether a berth can fix it, "")`. That flag is
    what tells a captain whether to go back into its berth and try again or to stop and park: a conflict and
    a failed gate are work on code, and a missing branch or an unmovable trunk are not.

    Everything happens in a scratch worktree made for this merge and removed afterwards either way, so a
    failure leaves no half-rebased branch anywhere a captain or a person is working.

    **A push that lost the race to trunk is done again, not refused.** Between the fetch and the push some
    other machine or person can push to trunk, and the forge then refuses ours as not a fast-forward. For a
    long while that came back as a refusal no berth could fix, and the fairway parked behind a slice that
    had passed its gate. Now it is fetched, rebased and gated again on the trunk that won, `PUSH_RACES`
    times, all under the one hold of the merge ref — and a trunk that outruns every one of them is refused
    as something asking again can fix, because it is.

    `spent` is filled with the whole seconds each part took, as far as this merge got: `lock_s` waiting on
    `refs/slipwai/merge` and `gate_s` running the gate. They are what says whether integration is slow
    because the harbour queues or because the gate is long, which nothing could answer from the logs before.
    """
    spent = {} if spent is None else spent
    branch = BRANCH.format(slice=slice_id)
    if git("rev-parse", "--verify", "--quiet", branch).returncode != 0:
        return "", f"there is no branch {branch} to merge", False, ""
    # A rebase that replays a commit writes one, and writing one needs a committer. Asked before the
    # worktree is made rather than read out of a failed rebase: git's own answer there is nine lines of
    # advice about `--global`, inside a refusal that has already said something else went wrong.
    if git("var", "GIT_COMMITTER_IDENT").returncode != 0:
        return "", ("this repository has no `user.name` and `user.email`, and a rebase writes commits. "
                    "`git config user.email you@example.com` here, or set one globally"), False, ""
    # Taken before the fetch, because `base()` is read after it and the whole point is that trunk does not
    # move between the gate and the advance. Released in the `finally` below, whichever way this ends.
    asked = time.monotonic()
    held, why = take_the_merge()
    spent["lock_s"] = round(time.monotonic() - asked)
    if not held:
        return "", why, False, ""
    try:
        for race in range(PUSH_RACES + 1):
            commit, fault, resolvable, note, raced = land(branch, spent)
            if not raced:
                return commit, fault, resolvable, note
            print(f"harbourmaster: trunk moved on the forge while {branch} was gated "
                  f"({race + 1} of {PUSH_RACES + 1}); gating it again on the new trunk", flush=True)
        return "", (f"{branch} passed the gate {PUSH_RACES + 1} times and each time trunk moved on the forge "
                    f"before it could be pushed. Nothing is wrong with the slice; ask again once trunk is "
                    f"quieter"), True, ""
    finally:
        # Given back the moment this merge is over, or the first merge of a run would be the last one any
        # machine ever did.
        claims.release(ROOT, claims.MERGE, logs.machine())


def ci_command(trunk_name: str) -> tuple[list[str], str]:
    """What is run to ask the forge about trunk, or ([], why nothing can be).

    `gh` by default, which is GitHub's own client and already holds a credential — this process is the one
    thing in a harbour that may hold one, and a second way of authenticating would be a second thing to
    leak. `harbour.json`'s `ci` replaces the argv for a harbour on another forge, with `{trunk}` and
    `{limit}` filled in; `"ci": "off"` says do not ask, which reads *unverified* and never *green*.

    Whatever runs has to print what `gh run list --json status,conclusion,headSha,workflowName,url`
    prints: a JSON list of runs. That is a shape, not a vendor — a dozen lines of any forge's API answer
    it, and a forge that cannot is one this says it could not verify rather than guessing about.
    """
    named = config().get("ci")
    if named == "off":
        return [], "`harbour.json` says `ci: off`, so trunk's CI is not read here"
    if isinstance(named, list) and named:
        return [str(word).replace("{trunk}", trunk_name).replace("{limit}", str(RUNS_READ))
                for word in named], ""
    if not shutil.which("gh"):
        return [], "`gh` is not on PATH, so trunk's CI cannot be read here; `harbour.json`'s `ci` takes a " \
                   "command for another forge, and `ci: off` says not to ask"
    return ["gh", "run", "list", "--branch", trunk_name, "--limit", str(RUNS_READ), "--json",
            "status,conclusion,headSha,workflowName,url"], ""


def forge_runs(trunk_name: str) -> tuple[list[dict], str]:
    """Trunk's recent CI runs as the forge reports them, or ([], why they could not be read)."""
    argv, fault = ci_command(trunk_name)
    if fault:
        return [], fault
    done = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        said = (done.stderr or done.stdout).strip().splitlines()
        return [], f"the forge could not be asked ({said[-1] if said else 'gh failed'})"
    try:
        found = json.loads(done.stdout or "[]")
    except ValueError:
        return [], "the forge's answer was not JSON"
    return (found, "") if isinstance(found, list) else ([], "the forge's answer was not a list of runs")


def trunk_ci(trunk_name: str) -> tuple[str, dict]:
    """What trunk's CI says: ("green"|"red"|"unverified", what it says).

    Every *completed* run of the newest commit that has one, and all of them have to be green for trunk to
    be. One workflow passing while another fails is a red trunk, and reading only the first would call it
    green — which is the whole failure this is here to stop.
    """
    runs, fault = forge_runs(trunk_name)
    if fault:
        return "unverified", {"why": fault}
    done = [one for one in runs if one.get("status") == "completed"]
    if not done:
        return "unverified", {"why": f"no CI run of {trunk_name} has finished yet"}
    commit = str(done[0].get("headSha", ""))
    mine = [one for one in done if str(one.get("headSha", "")) == commit]
    failed = [one for one in mine if str(one.get("conclusion", "")) in RED]
    if failed:
        return "red", {"commit": commit,
                       "job": ", ".join(sorted({str(one.get("workflowName", "?")) for one in failed})),
                       "url": str(failed[0].get("url", "")),
                       "why": f"trunk is red at {commit[:8]}"}
    if all(str(one.get("conclusion", "")) in GREEN for one in mine):
        return "green", {"commit": commit}
    return "unverified", {"why": f"no run of {commit[:8]} reached a verdict this reader knows"}


def broke_it(commit: str) -> tuple[str, str]:
    """The fairway and slice whose `merged` line names that commit, or ("", "").

    This process wrote that line, which is the whole reason the fix can be sent anywhere at all. Nothing
    there is a direct push or a red older than any merge, and the answer to that is a person.
    """
    for path in deck_logs():
        try:
            found = logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError, logs.Unreadable):
            continue
        for entry in found:
            if entry.kind == "merged" and str(entry.fields.get("commit", "")).startswith(commit[:8]):
                return str(entry.fields.get("fairway", "")), str(entry.fields.get("slice", ""))
    return "", ""


def last_trunk_word() -> str:
    """What the harbour log last said about trunk, so a state is written once and not every pass."""
    for entry in reversed(harbour_entries()):
        if entry.kind in ("trunk-red", "trunk-green"):
            return entry.kind
    return ""


def watch_trunk() -> tuple[str, list[logs.Entry]]:
    """Read trunk's CI and say what the harbour log owes. (the verdict, the lines to write).

    Written once per change of state rather than every pass: a board that said `trunk-red` fifteen times a
    minute is one nobody reads, and the fifteenth says nothing the first did not.
    """
    verdict, said = trunk_ci(trunk())
    was = last_trunk_word()
    if verdict == "red" and was != "trunk-red":
        fairway, slice_id = broke_it(str(said.get("commit", "")))
        lines = [logs.entry("trunk-red", harbour=True, commit=str(said.get("commit", "")),
                            job=str(said.get("job", "")), why=str(said.get("why", "")))]
        if fairway and slice_id:
            lines.append(logs.entry("fix-trunk", harbour=True, fairway=fairway, slice=slice_id,
                                    commit=str(said.get("commit", "")), job=str(said.get("job", ""))))
        else:
            lines.append(logs.entry("park", harbour=True, fairway="",
                                    why=f"trunk is red at {str(said.get('commit', ''))[:8]} "
                                        f"({said.get('job', 'a job')}) and no `merged` line accounts for "
                                        f"that commit, so nobody here broke it. A person decides what "
                                        f"happens; no merge is granted until trunk is green"))
        return verdict, lines
    if verdict == "green" and was == "trunk-red":
        return verdict, [logs.entry("trunk-green", harbour=True, commit=str(said.get("commit", "")))]
    return verdict, []


def never(detail: str) -> str | None:
    """Why this request is one the harbourmaster will never do, or None."""
    for pattern, why in NEVER:
        if re.search(pattern, detail):
            return why
    return None


def slice_asked(entry: logs.Entry) -> str:
    """Which slice a merge request is about: the field where there is one, else the id it was given.

    The id is `merge-<slice>` and has been since the captain first wrote one, so an older log still answers.
    The field is what a reader should use, because an id is a name and names get reformatted.
    """
    named = entry.fields.get("slice")
    if isinstance(named, str) and named:
        return named
    given = str(entry.fields.get("id", ""))
    # Only where the id really is one of ours. An id of some other shape names nothing, and treating it as
    # a slice would have this merge a branch whose name came from a string that was never about a branch.
    return given.removeprefix("merge-") if given.startswith("merge-") else ""


def attempts(fairway: str, slice_id: str) -> int:
    """Which attempt at merging this slice this one is: one more than the answers it has had already.

    Counted from the harbour log rather than from the request id, because a captain asks again under a new
    id — `merge-<slice>-<n>` — and an older harbour wrote no `slice` on a refusal.
    """
    def about(line: logs.Entry) -> bool:
        named = line.fields.get("slice")
        if named:
            return named == slice_id
        request = str(line.fields.get("request", ""))
        return request == f"merge-{slice_id}" or request.startswith(f"merge-{slice_id}-")
    return 1 + sum(1 for line in harbour_entries()
                   if line.kind in ("granted", "refused") and line.fields.get("fairway") == fairway and about(line))


def waited(entry: logs.Entry) -> dict[str, int]:
    """`waited_s`: whole seconds from the request being written to this harbourmaster taking it up.

    Nothing where the request carries no readable time, because a wait of nought would read as no queue.
    """
    try:
        asked = datetime.strptime(entry.t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return {}
    return {"waited_s": max(0, round((datetime.now(UTC) - asked).total_seconds()))}


def answer(entry: logs.Entry, trunk_state: str = "unverified") -> list[logs.Entry]:
    """The harbour-log line(s) one `request` gets: `granted` or `refused`, and always one of them.

    A granted merge is *performed* here before the line is written, so `granted` carries the commit trunk is
    now at and a captain has something to write `merged` against. A merge that could not be done is a
    refusal with the reason, which is the same outcome shape as a refusal of policy — the captain reads one
    thing either way.
    """
    fairway = str(entry.fields.get("fairway", ""))
    request = str(entry.fields.get("id", ""))
    what = str(entry.fields.get("what", ""))
    detail = str(entry.fields.get("detail", ""))
    if what not in ACTIONS:
        return [logs.entry("refused", harbour=True, fairway=fairway, request=request,
                           why=f"{what!r} is not something a captain may ask for. It may ask for: "
                               f"{', '.join(ACTIONS)}")]
    refusal = never(detail)
    if refusal is not None:
        return [logs.entry("refused", harbour=True, fairway=fairway, request=request,
                           why=f"{refusal}. Asked: {detail}")]
    if what != "merge":
        return [logs.entry("granted", harbour=True, fairway=fairway, request=request, what=what)]
    # Where a merge's time went, on both outcomes: queued for this harbourmaster, waiting on the merge ref,
    # running the gate, and which attempt this was. A refusal is time spent too, and the attempts are what
    # says a slice went round the berth three times before it landed.
    spent = waited(entry)
    if trunk_state == "red":
        # `resolve` false, because no berth can turn trunk green, so the captain parks rather than driving
        # the slice again to be told the same thing. `waiting` is what clears that park when trunk is no
        # longer red (`cleared_for_green`), which is the queue draining rather than a person undoing it.
        return [logs.entry("refused", harbour=True, fairway=fairway, request=request,
                           why="trunk is red, and nothing merges onto a red trunk. The harbour log says "
                               "which commit and which job; no fairway is granted a merge until it is "
                               "green, and the queue drains the moment it is",
                           resolve=False, waiting=GREEN_TRUNK, **spent)]
    slice_id = slice_asked(entry)
    if not slice_id:
        return [logs.entry("refused", harbour=True, fairway=fairway, request=request,
                           why="a merge request says which slice, in `slice` or in an id of `merge-<slice>`; "
                               "this one says neither, and guessing which branch to merge is not a thing to "
                               "guess at")]
    spent["attempt"] = attempts(fairway, slice_id)
    commit, fault, resolvable, note = merge(slice_id, spent)
    if fault:
        # `resolve` says whether going back into the berth could change the answer. A captain reads it to
        # decide between another turn and a park, which is the difference between a conflict it can fix and
        # a trunk nobody here can move.
        return [logs.entry("refused", harbour=True, fairway=fairway, request=request, why=fault,
                           resolve=resolvable, slice=slice_id, **spent)]
    # `after-merge`, and only here: the slice is on trunk and pushed, which is a different event from the
    # gate passing on the rebased branch — `before-merge` is that one, and the merge can still be refused
    # after it. An extension with something to do once the commit exists had no point to say so at, and
    # `before-merge` was the nearest wrong answer.
    fire("after-merge", slice=slice_id, fairway=fairway, commit=commit)
    # `ci` says what was known about trunk when this was granted. `unverified` is not `green`: a harbour
    # with no forge keeps working, and nobody reads the line later as a run that was checked.
    # `note` only where the person's checkout was touched to land it, so a reader who finds their branch
    # detached has the line that says why, and where their changes are.
    said = {"note": note} if note else {}
    if note:
        print(f"harbourmaster: {note}", flush=True)
    return [logs.entry("granted", harbour=True, fairway=fairway, request=request, what=what,
                       slice=slice_id, commit=commit, ci=trunk_state, **said, **spent)]


def allocation(fairway: str, taken: list[str]) -> logs.Entry:
    """The berth this fairway gets. Its index is its place in the order they were asked for, so two
    fairways never get one block and nobody chose a number."""
    name = berths.named(fairway.lower().replace("_", "-"))
    index = taken.index(name) if name in taken else len(taken)
    return logs.entry("berth-allocated", harbour=True, fairway=fairway,
                      berth=berths.berth(name, index, logs.machine()).name)


def carried(entries: list[logs.Entry], taken: list[str], trunk_state: str = "unverified") -> list[logs.Entry]:
    """Every harbour-log line this batch of deck-log lines produces, in the order they were written."""
    written: list[logs.Entry] = []
    for entry in entries:
        if entry.kind in CARRIED:
            fields = dict(entry.fields)
            if entry.kind == "parked":
                written.append(logs.entry("park", harbour=True, fairway=fields["fairway"], why=fields["why"]))
            else:
                written.append(logs.entry(CARRIED[entry.kind], harbour=True, **fields))
        elif entry.kind == "berth-request":
            fairway = str(entry.fields["fairway"])
            written.append(allocation(fairway, taken))
            name = berths.named(fairway.lower().replace("_", "-"))
            if name not in taken:
                taken.append(name)
        elif entry.kind == "request":
            written += answer(entry, trunk_state)
    return written


def allocated_already() -> list[str]:
    """Every berth *this machine* has already allocated, in the order it did, so a restart repeats none.

    This machine's own log and not the harbour's, which is the one place that distinction matters. A berth
    is ports and a database on one machine: the ports are local, so two machines allocating the same index
    cannot collide, and the database carries the machine's name for the case where they share a server.
    Reading every machine's allocations would make the second machine skip indices the first took — berths
    nobody has, ports nobody is using — for a collision that cannot happen.
    """
    taken: list[str] = []
    for entry in mine():
        if entry.kind == "berth-allocated":
            berth = str(entry.fields.get("berth", ""))
            if berth not in taken:
                taken.append(berth)
    return taken


def written_to() -> Path:
    """This machine's own harbour log — the only file this process ever appends to."""
    return ROOT / logs.harbour_path(logs.machine())


def harbour_entries() -> list[logs.Entry]:
    """Every machine's harbour log, folded into one by the instant each line records.

    Trunk's state, the telegraph and the bunker are the harbour's and not one machine's, so what this
    process reads is all of them. What it *writes* is its own file alone, which is how the single writer
    was removed rather than elected.
    """
    try:
        return logs.harbour_fold(ROOT)
    except (logs.Unreadable, OSError, UnicodeDecodeError):
        return []


def mine() -> list[logs.Entry]:
    """This machine's own harbour lines."""
    path = written_to()
    if not path.is_file():
        return []
    try:
        return logs.fold(path.read_text(encoding="utf-8").splitlines(), harbour=True)
    except logs.Unreadable:
        return []


def append(entries: list[logs.Entry]) -> None:
    path = written_to()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(entry.line())


def unreadable(path: Path, fault: str) -> None:
    """A deck log that cannot be read stops this pass over *that* log and says so. The others carry on: one
    fairway writing a bad line is not a reason the rest of the harbour stops hearing from each other."""
    print(f"harbourmaster: {key_of(path)} cannot be read ({fault}); its lines are not being carried",
          file=sys.stderr)


def once() -> int:
    """One pass: read what is new in every deck log, write what the harbour log needs. Returns lines written."""
    cursors = read_cursors()
    taken = allocated_already()
    fresh: list[logs.Entry] = []
    for path in deck_logs():
        lines, reached = new_lines(path, cursors)
        try:
            fresh += logs.fold(lines)
        except logs.Unreadable as fault:
            unreadable(path, str(fault))
            continue
        cursors[key_of(path)] = reached
    # Trunk first, because what it says decides whether any merge in this batch is granted at all. Asked
    # once a pass rather than once a request: it is a question for the forge, and the answer cannot change
    # between two requests answered a millisecond apart.
    trunk_state, trunk_said = watch_trunk()
    # By the clock rather than by file, so requests are answered in the order they were asked across every
    # fairway and not in the order the directory happens to list. It is the merge that makes this matter:
    # one at a time, each gated on a trunk that already holds the one before it.
    written: list[logs.Entry] = trunk_said + carried(sorted(fresh, key=lambda one: one.t), taken, trunk_state)
    written += bank() or rung()
    written += told_after_parks()
    written += cleared_for_review()
    written += cleared_by_decisions(written)
    written += cleared_for_green(trunk_state, written)
    written += cleared_by_time(written)
    written += needs_met(written)
    if written:
        append(written)
    write_cursors(cursors)
    fill_free_berths()
    return len(written)


def over_ceiling(fairway: str) -> bool | None:
    """Whether more decisions stand unread than `decision_ceiling` allows. None where it cannot be said."""
    try:
        return bool(inbox.owed(fairway).get("over_ceiling"))
    except (SystemExit, OSError, ValueError):
        return None


def told_after_parks() -> list[logs.Entry]:
    """A `cleared` receipt for every open park that a person has since told the stream something.

    A park is a person's to clear, and the board's answer box and `/cruise-tell` both write a `told` line,
    which is how a person answers one. Nothing turned that line into the receipt a park is cleared by, so
    the captain read the park, exited, and the `told` waited for a session the park stopped from ever
    starting: a stream told `go` stayed parked. Told after the park is the answer to it, and the message is
    what the receipt keeps, which `answer_questions` then records as the decision.

    **A person's, and only a person's.** A session writes `told` lines too — *for the host: L03 is green
    but for two gates* — and every one of them used to clear whatever park was open: hr-test-2's fairway
    parked at the decision ceiling on nineteen unread decisions, and the next slice's note to the host
    cleared it eleven minutes later with nobody having read one. Parks cleared each other the same way. So
    a `told` counts only where it says `by: person`, which the board and `fleet.py tell` outside a dispatched
    session write; an older line saying nothing of who wrote it answers nothing.

    **Never past the decision ceiling.** While more decisions stand unread than `decision_ceiling` allows,
    no message clears a park: the captain would park again at its next boundary, and *go* is not a reading.
    The answer waits and clears the park once the backlog is read. A park the captain wrote at the ceiling
    itself is `cleared_for_review`'s, whatever anybody says.

    **Aimed, where it says a slice.** A `told` naming a `slice` clears only that slice's park; one naming
    none is for the stream, and clears every park open in it, as before.

    Every deck log whole, not the lines new this pass: a park can be older than the cursor, and a receipt
    already written drops that park from `open_parks`, so a second pass writes nothing.
    """
    harbour = harbour_entries()
    found: list[logs.Entry] = []
    for path in deck_logs():
        fairway = path.stem
        try:
            deck = logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (logs.Unreadable, OSError, UnicodeDecodeError):
            continue
        told = [e for e in deck if e.kind == "told" and str(e.fields.get("fairway", "")) == fairway
                and e.fields.get("by") == PERSON]
        parks = [park for park in logs.open_parks(deck, harbour, fairway) if park.fields.get("waiting") != REVIEW]
        if not told or not parks or over_ceiling(fairway) is not False:
            continue
        for park in parks:
            # A message aimed at one slice — the box on its red card — answers that slice's park and no
            # other: three slices parked on three different questions are three answers, not one.
            after = [e for e in told if e.t > park.t
                     and (not e.fields.get("slice") or e.fields.get("slice") == park.fields.get("slice"))]
            if after:
                found.append(logs.entry("cleared", harbour=True, fairway=fairway, parked=park.t,
                                        what=str(after[-1].fields.get("message", "")).strip() or "told"))
    return found


def cleared_for_review() -> list[logs.Entry]:
    """A `cleared` receipt for every park a captain wrote at the decision ceiling, once it is no longer over.

    The ceiling is a person reading what was decided on their behalf, so what lifts it is the reading — a
    `read` line for each decision — or a person raising `decision_ceiling` in `harbour.json`. Not a message:
    a message is how the guardrail was walked past. Asked of the same count the captain parked on.
    """
    harbour = harbour_entries()
    found: list[logs.Entry] = []
    for path in deck_logs():
        fairway = path.stem
        try:
            deck = logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (logs.Unreadable, OSError, UnicodeDecodeError):
            continue
        parks = [park for park in logs.open_parks(deck, harbour, fairway) if park.fields.get("waiting") == REVIEW]
        if not parks or over_ceiling(fairway) is not False:
            continue
        found += [logs.entry("cleared", harbour=True, fairway=fairway, parked=park.t,
                             what="the decisions it waited on have been read, or the ceiling was raised")
                  for park in parks]
    return found


def cleared_by_decisions(already: list[logs.Entry]) -> list[logs.Entry]:
    """A `cleared` receipt for every park of one slice that stopped on questions, once each is decided.

    Under `/cruise` the skipper answers a slice's open questions — at the captain's turn, for a slice that
    parked on them before the session was told it was cruising — and a `decision` line carrying each
    question's `id` is the answer, in the same log the park is in. The park asked for exactly those answers,
    so nothing is left for a person to say. **Only a slice's own park**, only where at least one of the slice's
    questions was still open when the park was written, and only once no question of that slice is open: a park on anything else
    is still a person's, and so is one whose skipper left a question `unavailable`. Not a message — a
    person's `told` still clears a park in `told_after_parks`, unchanged; this reads decisions alone.
    """
    harbour = harbour_entries()
    done = {(str(e.fields.get("fairway", "")), str(e.fields.get("parked", "")))
            for e in already if e.kind == "cleared"}
    found: list[logs.Entry] = []
    for path in deck_logs():
        fairway = path.stem
        try:
            deck = logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (logs.Unreadable, OSError, UnicodeDecodeError):
            continue
        decided = {str(e.fields.get("id", "")) for e in deck if e.kind == "decision"}
        for park in logs.open_parks(deck, harbour, fairway):
            slice_id = str(park.fields.get("slice") or "")
            if not slice_id or park.fields.get("waiting") == REVIEW or (fairway, park.t) in done:
                continue
            asked = [str(e.fields.get("id", "")) for e in deck
                     if e.kind == "question" and str(e.fields.get("slice", "")) == slice_id]
            # The questions the park was waiting on: asked by then and not yet decided by then. A park written
            # after every question was already answered is about something else — hr-test-2's L21 parked
            # "implementation held by D50 until L09 is on main" with D45-D50 all written, and was cleared two
            # seconds later as though its questions were what held it, to be run again before L09 landed.
            settled = {str(e.fields.get("id", "")) for e in deck if e.kind == "decision" and e.t <= park.t}
            waited = [str(e.fields.get("id", "")) for e in deck if e.kind == "question" and e.t <= park.t
                      and str(e.fields.get("slice", "")) == slice_id and str(e.fields.get("id", "")) not in settled]
            if not waited or any(one not in decided for one in asked):
                continue
            found.append(logs.entry("cleared", harbour=True, fairway=fairway, parked=park.t,
                                    what=f"answered by decisions {', '.join(dict.fromkeys(waited))}"))
    return found


def cleared_for_green(trunk_state: str, already: list[logs.Entry]) -> list[logs.Entry]:
    """A `cleared` receipt for every open park caused by a merge refused only because trunk was red.

    That refusal said the queue drains the moment trunk is green, and nothing drained it: the captain read
    `resolve: false`, parked, and `fleet.relight` skips a parked fairway — so a red trunk anybody had since
    fixed left every fairway that asked during it parked for a person, behind slices that had passed their
    gates. Nothing about such a park needs a person. Trunk was the only reason, and trunk is the one thing
    this process watches.

    **Which parks.** The ones whose fairway's last answer at or before the park was a refusal carrying
    `waiting: green-trunk`. Read off this process's own answer rather than the captain's wording, because
    the captain writes its park as `<slice>: the merge was refused: <why>` and a reason matched as prose is
    one a later rewording silently stops matching. At-or-before, because the two lines are written in the
    same second as often as not.

    **When.** Every pass on which trunk is not red — green, or *unverified*, on which a merge goes ahead
    anyway — rather than only on the pass that wrote `trunk-green`: a captain can read the refusal and park
    after trunk has already turned, and a receipt only on the turn would miss it. A receipt already written
    drops the park from `open_parks`, so a second pass writes nothing, as in `told_after_parks`; `already`
    is this pass's lines, so a park that a `told` has just cleared is not cleared twice.
    """
    if trunk_state == "red":
        return []
    harbour = harbour_entries()
    answers: dict[str, list[logs.Entry]] = {}
    for entry in harbour:
        if entry.kind in ("granted", "refused"):
            answers.setdefault(str(entry.fields.get("fairway", "")), []).append(entry)
    done = {(str(e.fields.get("fairway", "")), str(e.fields.get("parked", "")))
            for e in already if e.kind == "cleared"}
    found: list[logs.Entry] = []
    for path in deck_logs():
        fairway = path.stem
        if fairway not in answers:
            continue
        try:
            deck = logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (logs.Unreadable, OSError, UnicodeDecodeError):
            continue
        for park in logs.open_parks(deck, harbour, fairway):
            before = [e for e in answers[fairway] if e.t <= park.t]
            if (not before or before[-1].kind != "refused" or before[-1].fields.get("waiting") != GREEN_TRUNK
                    or (fairway, park.t) in done or park.fields.get("waiting") == REVIEW):
                continue
            found.append(logs.entry("cleared", harbour=True, fairway=fairway, parked=park.t,
                                    what="trunk is no longer red, so the merge it refused is asked for again"))
    return found


def cleared_by_time(already: list[logs.Entry]) -> list[logs.Entry]:
    """A `cleared` receipt for every open park whose `until` has come.

    A park with an `until` is a pause: the harness said when it would run the session again, and nobody
    was asked anything. On the recap voyage the limit reset at 21:40 and eight parks stood until a person
    came back at 09:00, because nothing in the fleet knew that time existed. This is the thing that knows.
    The pass after the receipt lights the captain (`fill_free_berths`), so a resume lands within one
    pass of the time. `already` is this pass's lines, so a pause a person cleared early is not cleared twice.
    """
    harbour = harbour_entries()
    now = logs.now()
    done = {(str(e.fields.get("fairway", "")), str(e.fields.get("parked", "")))
            for e in already if e.kind == "cleared"}
    found: list[logs.Entry] = []
    for path in deck_logs():
        fairway = path.stem
        try:
            deck = logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (logs.Unreadable, OSError, UnicodeDecodeError):
            continue
        for park in logs.open_parks(deck, harbour, fairway):
            until = str(park.fields.get("until") or "")
            if not until or until > now or (fairway, park.t) in done:
                continue
            found.append(logs.entry("cleared", harbour=True, fairway=fairway, parked=park.t,
                                    what=f"the time it waited for came: {until}"))
    return found


#: A `make` check may name a target that reads and never writes. `check-*` is that convention in a
#: generated project (`check-model`, `check-chart`, `check-decisions`, `check-slice-scope`); anything else a
#: project wants ticked by `make` is listed in `harbour.json` under `checks`.
CHECK_TARGET = re.compile(r"^check-[a-z0-9-]+$")
#: Where a `make` check runs: a worktree at trunk, made for the check and removed after it.
NEEDS = ROOT / ".slipwai/needs"
#: The checks this process has already run, per trunk commit: a failing `make` is not run again until trunk
#: moves. In memory, because a restart running each once more costs one bounded `make` per need and
#: nothing written.
TRIED: set[tuple[str, str, int, str]] = set()


def trunk_commit() -> str:
    """The commit trunk is at, as this machine sees it — the remote's where there is one."""
    return git("rev-parse", "--verify", "--quiet", base()).stdout.strip()


def text_check(check: dict, commit: str) -> bool:
    """Whether the file at `path` on trunk holds `has`. Read with `git show`, never from a checkout, so a
    berth's uncommitted edit of the same file never ticks a need on trunk's behalf."""
    shown = git("show", f"{commit}:{check.get('path', '')}")
    return shown.returncode == 0 and str(check.get("has", "")) in shown.stdout


def make_check(check: dict, commit: str) -> bool:
    """Whether `make <target>` passes on trunk, in a worktree of its own, within `wait_bound`.

    Only a `check-*` target or one `harbour.json` lists under `checks`: a need is written by a session, and
    a session must not be able to have this process run `make deploy` on trunk by asking.
    """
    target = str(check.get("target", ""))
    allowed = config().get("checks")
    if not (CHECK_TARGET.match(target) or (isinstance(allowed, list) and target in allowed)):
        return False
    git("worktree", "remove", "--force", str(NEEDS))
    NEEDS.parent.mkdir(parents=True, exist_ok=True)
    made = git("worktree", "add", "--quiet", "--detach", str(NEEDS), commit)
    if made.returncode != 0:
        return False
    try:
        done = subprocess.run(["make", target], cwd=NEEDS, capture_output=True, text=True, check=False,
                              timeout=merge_wait())
        return done.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        git("worktree", "remove", "--force", str(NEEDS))


def needs_met(already: list[logs.Entry]) -> list[logs.Entry]:
    """A `need-met` receipt for every need of an open park that trunk now satisfies or a person has ticked,
    and a `cleared` receipt for every park whose needs are all met.

    A park that waits on a change to trunk is a list of needs, each with a check this process can run
    against trunk — a file holding a string, a `check-*` target passing — or a person's word. recap's LB6,
    LB7 and LB8 each waited on the same five things, written as three paragraphs a person had to read to
    find out they were the same five things. The receipts are what lets the board draw them as one
    checklist with the ticks on it, and what clears the park without anybody being asked once the last one
    lands.
    """
    harbour = harbour_entries()
    met = {(str(e.fields.get("fairway", "")), str(e.fields.get("parked", "")), int(e.fields.get("need", -1)))
           for e in [*harbour, *already] if e.kind == "need-met"}
    done = {(str(e.fields.get("fairway", "")), str(e.fields.get("parked", "")))
            for e in already if e.kind == "cleared"}
    commit = trunk_commit()
    found: list[logs.Entry] = []
    for path in deck_logs():
        fairway = path.stem
        try:
            deck = logs.fold(path.read_text(encoding="utf-8").splitlines())
        except (logs.Unreadable, OSError, UnicodeDecodeError):
            continue
        ticked = {(str(e.fields.get("parked", "")), int(e.fields.get("need", -1)))
                  for e in deck if e.kind == "need-done" and str(e.fields.get("fairway", "")) == fairway}
        for park in logs.open_parks(deck, harbour, fairway):
            needs = park.fields.get("needs")
            if not isinstance(needs, list) or not needs or (fairway, park.t) in done:
                continue
            for index, need in enumerate(needs):
                if (fairway, park.t, index) in met:
                    continue
                how = ""
                if (park.t, index) in ticked:
                    how = "a person ticked it on the board"
                elif commit and isinstance(need, dict) and isinstance(need.get("check"), dict):
                    key = (fairway, park.t, index, commit)
                    if key not in TRIED:
                        TRIED.add(key)
                        check = need["check"]
                        passed = (text_check(check, commit) if check.get("kind") == "text"
                                  else make_check(check, commit))
                        how = f"trunk at {commit[:8]}" if passed else ""
                if how:
                    met.add((fairway, park.t, index))
                    found.append(logs.entry("need-met", harbour=True, fairway=fairway, parked=park.t,
                                            need=index, how=how))
            if all((fairway, park.t, index) in met for index in range(len(needs))):
                found.append(logs.entry("cleared", harbour=True, fairway=fairway, parked=park.t,
                                        what=f"every need of this park is met: {len(needs)} of {len(needs)}"))
    return found


def fill_free_berths() -> None:
    """Share the boilers out between the fairways, and light a captain for each one given a session.

    A berth is a machine-local resource and allocating them is already this process's job; this is the same
    job from the other end. `boilers` bounds how many slice sessions run in this harbour at once and the
    harbour's fairway priority is which streams get them, so a person moving a stream up pushes another
    below the line, and that captain writes `yielded` at its next slice boundary and exits. Something then
    has to fill the berth it gave up, or reordering the streams would *stop* a run rather than reorder it —
    and `fleet.py` cannot, by design: it starts processes and gets out of the way.

    **One decider for every fairway's number**, because the number is a share of one budget: `abreast.py`
    says the rule — breadth first, depth by priority, `abreast` the cap, a pending merge holding its fairway,
    nothing preempted — and this writes each fairway's `slots` line when its number, or what it is running,
    has changed. A captain reads that line before it starts any slice beyond its first. Where the plan cannot
    be made — no chart yet, or a module this harbour does not carry — captains are lit as they were, one per
    fairway in priority order, and none is given more than one slice.

    `relight` and never `cast_off`: it lights captains only. A harbourmaster started by hand has no pid
    file, so `cast_off` would read it as not running and start a second one, which is the one-writer rule
    broken in the file this whole design promises cannot conflict.

    Nothing here costs the pass. A fleet that cannot be read or a captain that will not start is a fact
    about this machine, said by `fleet list` and by the captain's own absence from the logs; a
    harbourmaster that stopped carrying lines between fairways because it could not spawn a process would
    take the run down with it.
    """
    try:
        import fleet
        held = json.loads(HARBOUR_CONFIG.read_text(encoding="utf-8")) if HARBOUR_CONFIG.is_file() else {}
        limit = held.get("boilers") if isinstance(held, dict) else None
        if isinstance(limit, int) and not isinstance(limit, bool) and limit <= 0:
            return  # The telegraph is at `stop`, which lights nothing by its own rule.
        bounded = limit if isinstance(limit, int) and not isinstance(limit, bool) else None
        planned = plan_slots(fleet)
        if planned is None:
            fleet.relight(bounded)
            return
        fleet.relight(bounded, wanted=[fairway for fairway, (count, _, _) in planned.items() if count > 0])
        written = slots_lines(planned, harbour_entries())
        if written:
            append(written)
    except Exception as fault:  # pragma: no cover - never at the cost of the pass
        print(f"harbourmaster: the fleet could not be relit ({fault})", flush=True)


def plan_slots(fleet: object) -> dict[str, tuple[int, int, str]] | None:
    """Every fairway's (sessions, running, the fairway a slot went to), or None where no plan can be made."""
    try:
        import abreast
    except ImportError:
        return None
    standing = {name for name, pid in fleet.recorded().items() if fleet.alive(pid)}  # type: ignore[attr-defined]
    lit = {name.removeprefix("captain-") for name in standing if name.startswith("captain-")}
    planned = abreast.harbour_plan(lit, HARBOUR_CONFIG)
    return planned or None


def slots_lines(planned: dict[str, tuple[int, int, str]], harbour: list[logs.Entry]) -> list[logs.Entry]:
    """A `slots` line for each fairway whose number, running count or yield target has changed since its
    last one — and none for a fairway that has never had a number and is given none now, so a chart's idle
    streams do not fill the log with zeros."""
    found: list[logs.Entry] = []
    for fairway, (count, running, to) in planned.items():
        last = next((e for e in reversed(harbour) if e.kind == "slots"
                     and str(e.fields.get("fairway", "")) == fairway), None)
        said = {"running": running, **({"to": to} if to else {})}
        if last is None and count == 0 and not to:
            continue
        if last is not None and (last.fields.get("slots"), last.fields.get("running"),
                                 last.fields.get("to", "")) == (count, running, to):
            continue
        found.append(logs.entry("slots", harbour=True, fairway=fairway, slots=count, **said))
    return found


def ours() -> list[str]:
    """The fairways this machine holds the claim for, which are the only deck logs it may push.

    `travel` owns the rule, because the rule is about what may travel: one ref per writer, and a fairway's
    writer is whichever captain holds it. This process and a plain `/sail` therefore ask the same question
    and get the same answer, which is the whole of why it moved there.
    """
    return travel.ours(ROOT)


def in_flight(path: Path) -> str:
    """The slice this fairway is still working on, or `""`. `travel`'s, for the reason `ours` gives."""
    return travel.in_flight(path)


def arrive() -> None:
    """Bring in what other machines have written, and put it where this harbour's readers already look.

    Never fatal: a harbour on one machine has no remote, and one that cannot reach its forge still has
    every local fairway to carry between.
    """
    travel.land(ROOT, logs.machine(), ours())


def depart() -> None:
    """Put this machine's logs and in-flight branches where the other machines can read them.

    `travel` does it, and does it the same way for a plain `/sail`: this process holds the credential but
    not the rule, and a harbourmaster that pushed by one rule while a session pushed by another would be
    two answers to what travels. Every refusal is said here — a push that is not an append is a log about
    to lose lines, and hearing about it is the whole design.
    """
    _, refused = travel.depart(ROOT)
    for why in refused:
        print(f"harbourmaster: {why}", file=sys.stderr)


def clear_park(fairway: str, parked: str, what: str) -> tuple[bool, str]:
    """Record the harbourmaster's answer to one original park, with the answer itself retained."""
    if not parked or not what.strip():
        return False, ("a clearance needs the original park timestamp and the answer. Run "
                       "`python3 scripts/agents/harbourmaster.py --clear <fairway> "
                       "--parked <timestamp> --what '<answer>' --once`")
    history = [entry for path in deck_logs() if path.stem == fairway
               for entry in logs.fold(path.read_text(encoding="utf-8").splitlines())]
    matching = [entry for entry in history if entry.kind == "parked" and entry.t == parked
                and str(entry.fields["fairway"]) == fairway]
    if not matching:
        return False, (f"{fairway} has no park at {parked}. Run `slipwai fleet {fairway}` and use "
                       "the original park's timestamp")
    if not any(entry.t == parked for entry in logs.open_parks(history, harbour_entries(), fairway)):
        return True, f"{fairway}'s park at {parked} is already cleared"
    append([logs.entry("cleared", harbour=True, fairway=fairway, parked=parked, what=what.strip())])
    return True, f"cleared {fairway}'s park at {parked}: {what.strip()}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="harbourmaster",
        description="Carry between fairways, allocate berths, and answer a captain's requests")
    parser.add_argument("--once", action="store_true", help="one pass, rather than the loop")
    parser.add_argument("--interval", type=float, default=HEARTBEAT, help="seconds between passes")
    parser.add_argument("--no-fetch", action="store_true",
                        help="carry between this machine's own fairways only: reach the forge neither for "
                             "what other machines have written nor to push what this one has")
    parser.add_argument("--clear", metavar="FAIRWAY", help="answer one park, retaining its timestamp and answer")
    parser.add_argument("--parked", default="", help="the original parked line's timestamp")
    parser.add_argument("--what", default="", help="the decision or repair that lets work resume")
    parsed = parser.parse_args(argv)
    if parsed.clear:
        if not parsed.no_fetch:
            arrive()
        try:
            ok, said = clear_park(parsed.clear, parsed.parked, parsed.what)
        except (logs.Unreadable, OSError, UnicodeDecodeError) as fault:
            print(f"harbourmaster: cannot read the parked history ({fault}). Run `slipwai fleet {parsed.clear}`")
            return 1
        print(f"harbourmaster: {said}")
        if ok and not parsed.no_fetch:
            depart()
        return 0 if ok else 1
    while True:
        if not parsed.no_fetch:
            arrive()
        count = once()
        if count:
            print(f"harbourmaster: {count} line(s) carried to {logs.harbour_path(logs.machine())}")
        if not parsed.no_fetch:
            # After the pass and not before it: what this machine has to say about this pass is written by
            # `once()`, and pushing first would carry every line but the ones just made.
            depart()
        if parsed.once:
            return 0
        time.sleep(parsed.interval)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
