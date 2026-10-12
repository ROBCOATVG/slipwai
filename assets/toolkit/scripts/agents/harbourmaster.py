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
trunk is green again, which is written once as `trunk-green`. A forge this cannot reach reads *could not
verify*, never *green*: the merge still goes ahead — a harbour with no forge has to keep working — and the
`granted` line says the CI was unverified, so nobody reads it later as a run that was checked.

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
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import berths  # noqa: E402
import logs  # noqa: E402
import telegraph  # noqa: E402


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
#: What the branch for a slice is called, which `check-slice-scope` holds every branch to as well.
BRANCH = "slice/{slice}"
#: Used where nothing says otherwise. `origin/HEAD` answers it on a repository with a remote.
DEFAULT_TRUNK = "main"


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
    """Every fairway's log, in a stable order. The harbour log is not one of them: it is the output."""
    place = ROOT / logs.LOGS
    harbour = ROOT / logs.HARBOUR
    return sorted(path for path in place.rglob("*.jsonl") if path.resolve() != harbour.resolve())


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


def advance(name: str, commit: str) -> str:
    """Move trunk to this commit, and say what went wrong, or nothing.

    Pushed where there is a remote, because then nobody's working tree is touched and every checkout catches
    up on its own next fetch. With no remote there is only the local ref — and if the person's own checkout
    is sitting on trunk, moving the ref under it would leave their working tree looking like a mass
    deletion, so that case is a fast-forward in their checkout when it is clean and a refusal when it is not.
    """
    if git("rev-parse", "--verify", "--quiet", "origin/" + name).returncode == 0:
        pushed = git("push", "origin", f"{commit}:refs/heads/{name}")
        return "" if pushed.returncode == 0 else (pushed.stderr or pushed.stdout).strip().splitlines()[-1]
    head = git("symbolic-ref", "--quiet", "--short", "HEAD")
    if head.returncode == 0 and head.stdout.strip() == name:
        # Tracked changes only. An untracked file does not stop a fast-forward unless the merge wants to
        # create that same path, and `--ff-only` refuses that case itself with a better sentence than a
        # blanket check would — while a blanket check would refuse every harbour, since a run's own
        # `.slipwai/` is untracked in anything but a generated project.
        if git("status", "--porcelain", "--untracked-files=no").stdout.strip():
            return (f"this checkout is on {name} with uncommitted changes, so trunk cannot be moved under "
                    f"it. Commit or stash them and ask again")
        moved = git("merge", "--ff-only", commit)
        return "" if moved.returncode == 0 else (moved.stderr or moved.stdout).strip().splitlines()[-1]
    moved = git("update-ref", f"refs/heads/{name}", commit)
    return "" if moved.returncode == 0 else (moved.stderr or moved.stdout).strip().splitlines()[-1]


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


def merge(slice_id: str) -> tuple[str, str, bool]:
    """Rebase this slice onto trunk, gate it there, and advance trunk.

    `(commit, "", False)` where it landed, or `("", why not, whether a berth can fix it)`. That last flag is
    what tells a captain whether to go back into its berth and try again or to stop and park: a conflict and
    a failed gate are work on code, and a missing branch or an unmovable trunk are not.

    Everything happens in a scratch worktree made for this merge and removed afterwards either way, so a
    failure leaves no half-rebased branch anywhere a captain or a person is working.
    """
    branch = BRANCH.format(slice=slice_id)
    if git("rev-parse", "--verify", "--quiet", branch).returncode != 0:
        return "", f"there is no branch {branch} to merge", False
    # A rebase that replays a commit writes one, and writing one needs a committer. Asked before the
    # worktree is made rather than read out of a failed rebase: git's own answer there is nine lines of
    # advice about `--global`, inside a refusal that has already said something else went wrong.
    if git("var", "GIT_COMMITTER_IDENT").returncode != 0:
        return "", ("this repository has no `user.name` and `user.email`, and a rebase writes commits. "
                    "`git config user.email you@example.com` here, or set one globally"), False
    git("fetch", "--quiet", "origin", trunk())
    onto = base()
    git("worktree", "remove", "--force", str(SCRATCH))  # a worktree left by a run that was killed
    SCRATCH.parent.mkdir(parents=True, exist_ok=True)
    made = git("worktree", "add", "--quiet", "--detach", str(SCRATCH), branch)
    if made.returncode != 0:
        return "", f"a worktree for {branch} could not be made ({(made.stderr or made.stdout).strip()})", False
    try:
        rebased = git("rebase", onto, where=SCRATCH)
        if rebased.returncode != 0:
            paths = conflicting()
            git("rebase", "--abort", where=SCRATCH)
            return "", (f"{branch} conflicts with {onto} in {', '.join(paths) or 'files git did not name'}. "
                        f"The rebase was aborted, so nothing is half-done; resolve it in your own berth and "
                        f"ask again"), True
        done = subprocess.run(gate(), cwd=SCRATCH, capture_output=True, text=True, check=False)
        if done.returncode != 0:
            said = [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]
            return "", (f"the full gate failed on {branch} rebased onto {onto}: "
                        f"{said[-1] if said else 'no output'}"), True
        commit = git("rev-parse", "HEAD", where=SCRATCH).stdout.strip()
        fault = advance(trunk(), commit)
        if fault:
            return "", f"{branch} passed the gate and trunk could not be moved: {fault}", False
        return commit, "", False
    finally:
        git("worktree", "remove", "--force", str(SCRATCH))


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
    if trunk_state == "red":
        return [logs.entry("refused", harbour=True, fairway=fairway, request=request,
                           why="trunk is red, and nothing merges onto a red trunk. The harbour log says "
                               "which commit and which job; no fairway is granted a merge until it is "
                               "green, and the queue drains the moment it is",
                           resolve=False)]
    slice_id = slice_asked(entry)
    if not slice_id:
        return [logs.entry("refused", harbour=True, fairway=fairway, request=request,
                           why="a merge request says which slice, in `slice` or in an id of `merge-<slice>`; "
                               "this one says neither, and guessing which branch to merge is not a thing to "
                               "guess at")]
    commit, fault, resolvable = merge(slice_id)
    if fault:
        # `resolve` says whether going back into the berth could change the answer. A captain reads it to
        # decide between another turn and a park, which is the difference between a conflict it can fix and
        # a trunk nobody here can move.
        return [logs.entry("refused", harbour=True, fairway=fairway, request=request, why=fault,
                           resolve=resolvable)]
    # `after-merge`, and only here: the slice is on trunk and pushed, which is a different event from the
    # gate passing on the rebased branch — `before-merge` is that one, and the merge can still be refused
    # after it. An extension with something to do once the commit exists had no point to say so at, and
    # `before-merge` was the nearest wrong answer.
    fire("after-merge", slice=slice_id, fairway=fairway, commit=commit)
    # `ci` says what was known about trunk when this was granted. `unverified` is not `green`: a harbour
    # with no forge keeps working, and nobody reads the line later as a run that was checked.
    return [logs.entry("granted", harbour=True, fairway=fairway, request=request, what=what,
                       slice=slice_id, commit=commit, ci=trunk_state)]


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
    """Every berth the harbour log has already allocated, in the order it did, so a restart repeats none."""
    taken: list[str] = []
    for entry in harbour_entries():
        if entry.kind == "berth-allocated":
            berth = str(entry.fields.get("berth", ""))
            if berth not in taken:
                taken.append(berth)
    return taken


def harbour_entries() -> list[logs.Entry]:
    path = ROOT / logs.HARBOUR
    if not path.is_file():
        return []
    try:
        return logs.fold(path.read_text(encoding="utf-8").splitlines(), harbour=True)
    except logs.Unreadable:
        return []


def append(entries: list[logs.Entry]) -> None:
    path = ROOT / logs.HARBOUR
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
    if written:
        append(written)
    write_cursors(cursors)
    return len(written)


def fetch() -> None:
    """Bring in what other machines' captains have written. Never fatal: a harbour on one machine has no
    remote, and one that cannot reach its forge still has every local fairway to carry between."""
    run = subprocess.run(["git", "fetch", "--quiet", "origin", "refs/slipwai/logs/*:refs/slipwai/logs/*"],
                         cwd=ROOT, capture_output=True, text=True)
    if run.returncode != 0:
        said = (run.stderr or run.stdout).strip().splitlines()
        print(f"harbourmaster: the logs could not be fetched ({said[-1] if said else 'git failed'}); "
              f"carrying what is here", file=sys.stderr)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="harbourmaster",
        description="Carry between fairways, allocate berths, and answer a captain's requests")
    parser.add_argument("--once", action="store_true", help="one pass, rather than the loop")
    parser.add_argument("--interval", type=float, default=HEARTBEAT, help="seconds between passes")
    parser.add_argument("--no-fetch", action="store_true", help="do not reach the forge for other machines")
    parsed = parser.parse_args(argv)
    while True:
        if not parsed.no_fetch:
            fetch()
        count = once()
        if count:
            print(f"harbourmaster: {count} line(s) carried to {logs.HARBOUR}")
        if parsed.once:
            return 0
        time.sleep(parsed.interval)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
