#!/usr/bin/env python3
"""The trunk mender: what the harbourmaster sends when trunk is red, and to land a shared surface a slice
handed back.

**A red trunk stops the line, and mending it is the next job** — minimumCD's rule, the owner's since phase 25
(`docs/stop-the-line-plan.md`). Until then a red trunk refused every merge and sent `fix-trunk` to the captain
whose merge made it, while every other fairway kept building on top. In game-club-manager that found nobody:
the red came from the scaffold's own workflow (`actions/upload-artifact@v3`, refused at *Set up job*), the
captain it would have gone to had parked and left, and the order was never written because the reader of
`merged` ran eighteen minutes before the captain wrote it. Trunk stayed red overnight with four slices
built and waiting.

So the harbourmaster sends one agent, `agents/harbour-trunk-mender.md`, into a worktree of its own made from
trunk, with the red commit, the failed job and its log. It fixes forward or reverts the merge that went red,
commits on its branch, and ends. Nothing it does reaches trunk except through the harbourmaster: its branch
is held to `refusal` below, then rebased and gated by `make verify` exactly like a slice's, and landed as the
one change allowed onto a red trunk. Every attempt is a harbour line — `mend`, then `mended` or
`mend-failed` — and after `attempts` of them the red parks for a person, which is the only point a person is
asked at all.

**Between reds it lands what slices hand back.** A `need` naming a shared surface — the `.env.example` lines,
a section of `docs/design.md`, a typed `post` in `packages/api-client` — had nobody to do it unless a person
did. game-club-manager's five slices left eleven of them. The mender takes one at a time while trunk is
green: a need written `by: fleet`, and under `/cruise` one written `by: person` as well when its check is a
shared surface's text, because the person asked not to be waited on. The receipt is the need's own check
passing on trunk, which `needs_met` already writes; nothing here ticks anything.

**What the mender may change is held mechanically, not by its brief.** A gate passes on its own merits, so
no gate is the mender's to edit: `scripts/`, `tools/`, the hooks, the Makefile, the controlled files and the
agents' own material are refused outright. A workflow under `.github/workflows/` may change only by moving
an action's `uses:` to another ref of the same action — which is what a deprecated action refused at *Set
up job* needs, and which cannot remove, skip or weaken a step. A revert is allowed to touch what the merge
it reverts touched. A need's change touches shared surfaces only, and has to touch the file its check reads.

Standalone and dependency-free, like everything under `scripts/`. The harbourmaster drives it and passes in
the three things that are its own — the trunk it measures, the base it rebases onto, and the merge.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import logs  # noqa: E402


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


ROOT = project_root()
#: The brief the session is started from, as every harness projects it.
BRIEF = "agents/harbour-trunk-mender.md"
#: What is mended: a red trunk, or a need a slice handed back.
TRUNK, NEED = "trunk", "need"
#: Where each attempt's worktree is made, and the failed run's log written beside it. Ignored with the rest
#: of the run's state, and removed when the attempt is over.
PLACE = logs.run_dir(ROOT) / "mend"
#: What this machine's harbourmaster knows about the attempt in flight, so a restart can find it again.
RECORD = logs.run_dir(ROOT) / "running/mender.json"
#: The branch an attempt commits on. Not `slice/<id>`, so `check-slice-scope` has nothing to hold it to;
#: `refusal` below is what holds it.
BRANCH = "mend/{job}-{key}"
#: Used where `harbour.json` names neither.
DEFAULT_ATTEMPTS, DEFAULT_MINUTES = 3, 60
#: Never the mender's, whatever the job. A gate passes on its own merits, so nothing that is a gate, runs
#: one, or decides what an agent may do is a file it may edit.
NEVER = ("scripts/", "tools/", ".githooks/", ".slipwai/", ".specify/", "agents/", "commands/", "skills/",
         "Makefile", "harbour.json", "project.json", ".github/")
#: Where a need's change may land: the shared surfaces a slice may not edit and hands back instead.
SHARED = (".gitignore", ".env.example", "docs/", "packages/", "design-system/")
WORKFLOWS = ".github/workflows/"
#: A `uses:` line, as a workflow's step names an action: its indent and dash, the action, and its ref.
USES = re.compile(r"^(\s*-?\s*)uses:\s*['\"]?([^@\s'\"]+)@([^\s'\"#]+)")
#: The attempt in flight in this process, by job. A process that exited is not asked again by pid, which
#: would find its zombie and call it alive.
FLYING: dict[str, subprocess.Popen] = {}


def config() -> dict:
    try:
        held = json.loads((ROOT / "harbour.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def attempts() -> int:
    held = config().get("attempts")
    return held if isinstance(held, int) and held > 0 else DEFAULT_ATTEMPTS


def bound() -> float:
    """Seconds one attempt may run before it is ended and counted as failed."""
    held = config().get("mend_minutes")
    return (held if isinstance(held, int | float) and held > 0 else DEFAULT_MINUTES) * 60.0


def cruising() -> bool:
    try:
        held = json.loads((ROOT / ".specify/cruise.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return False
    return isinstance(held, dict) and held.get("enabled") is True \
        and str(held.get("decide") or "recommended-first") in ("recommended-first", "skipper-always")


def git(*argv: str, where: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], cwd=where or ROOT, capture_output=True, text=True, check=False)


# What is in flight.

def record() -> dict:
    try:
        held = json.loads(RECORD.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def running() -> bool:
    """Whether an attempt is still going: this process's own child by `poll`, or a recorded pid."""
    held = record()
    if not held:
        return False
    child = FLYING.get(str(held.get("job", "")))
    if child is not None:
        return child.poll() is None
    pid = held.get("pid")
    return isinstance(pid, int) and alive(pid)


def alive(pid: int) -> bool:
    """`fleet.alive`, which this cannot import without the chart: asked through the process handle on
    Windows, where `os.kill(pid, 0)` ends the process it asks about."""
    if sys.platform == "win32":  # pragma: no cover - the other platform's branch
        import ctypes  # noqa: PLC0415 - only this branch needs it

        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def end(child: subprocess.Popen) -> None:
    try:
        child.terminate()
        child.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        child.kill()


# What the mender may change.

def workflow_refusal(diff: str, path: str) -> str:
    """Why this change to a workflow is refused, or "": every changed line must be a `uses:` moving the same
    action to another ref, so no step is removed, skipped, added or weakened."""
    gone = [line[1:] for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    came = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    if len(gone) != len(came) or not gone:
        return (f"{path} changes more than an action's ref ({len(gone)} line(s) out, {len(came)} in); a "
                f"workflow is the mender's only to move a `uses:` to another ref of the same action")
    for before, after in zip(gone, came, strict=True):
        was, now = USES.match(before), USES.match(after)
        if not was or not now or was.group(1) != now.group(1) or was.group(2) != now.group(2) \
                or before[was.end():].strip() != after[now.end():].strip():
            return (f"{path} changes `{before.strip()}` to `{after.strip()}`, which is not one action moved to "
                    f"another ref; nothing else in a workflow is the mender's")
    return ""


def changed(onto: str, branch: str) -> list[str]:
    return [line for line in git("diff", "--name-only", f"{onto}...{branch}").stdout.splitlines() if line]


def refusal(job: str, onto: str, branch: str, reverting: list[str], reads: str = "") -> str:
    """Why this attempt's branch may not land, or "".

    `reverting` is what the merge that went red touched, which a revert of it may touch too; `reads` is the
    file a need's check reads, which a need's change has to touch.
    """
    paths = changed(onto, branch)
    if not paths:
        return "the mender ended without committing anything on its branch"
    for path in paths:
        if path.startswith(WORKFLOWS) and job == TRUNK:
            why = workflow_refusal(git("diff", "-U0", f"{onto}...{branch}", "--", path).stdout, path)
            if why:
                return why
            continue
        if job == TRUNK and path in reverting:
            continue
        if any(path == never.rstrip("/") or path.startswith(never) for never in NEVER):
            return f"{path} is never the mender's to change: a gate passes on its own merits"
        if job == NEED and not any(path == place or path.startswith(place) for place in SHARED):
            return f"{path} is not a shared surface, and a need's change lands only on one"
    if job == NEED and reads and reads not in paths:
        return f"the need is checked in {reads}, and the change does not touch it"
    return ""


# Starting an attempt.

def prompt(job: str, worktree: Path, branch: str, told: dict) -> str:
    """What the session is asked. The brief is the standing part; this is the task."""
    head = (f"You are the trunk mender: read `{BRIEF}` first, and work only as it says. You are in a worktree "
            f"made from trunk at {worktree}, on branch {branch}. Commit on that branch and end. Never push and "
            f"never merge: the harbourmaster gates your branch and lands it.")
    if job == TRUNK:
        said = (f"\n\nTrunk is red at {told['commit']}: the `{told.get('job', '?')}` workflow failed"
                f"{' (' + told['url'] + ')' if told.get('url') else ''}. This is attempt {told['attempt']}.")
        if told.get("log"):
            said += f" The failed run's log is at {told['log']}."
        if told.get("slice"):
            said += (f" It went red with the merge of slice {told['slice']} (fairway {told.get('fairway')})"
                     f"{', which moved trunk from ' + told['onto'] if told.get('onto') else ''}; reverting that "
                     f"merge is allowed, and touches only what it touched.")
        else:
            said += " No merge the harbour granted accounts for it, so fix forward; revert nothing."
        if told.get("before"):
            said += f" The last attempt did not clear it: {told['before']}."
        return head + said
    return head + (f"\n\nSlice work on fairway {told['fairway']} handed this back to the host: "
                   f"\"{told.get('said', '')}\". The need: \"{told['what']}\". It is met when "
                   f"{told['check']}. Land exactly that from what the slice left, which the need or the note "
                   f"names. If it is not a change to a shared surface — it waits on another slice's merge, a "
                   f"secret or a person — change nothing and end.")


def command(job: str, worktree: Path, branch: str, told: dict) -> tuple[list[str], dict[str, str]]:
    """The session's argv and environment. `SLIPWAI_MENDER` replaces the argv and takes `<job> <told.json>`
    after it, as `SLIPWAI_SAIL` does for the ladder — which is how the suite drives a fake mender."""
    environment = {**os.environ, "SLIPWAI_STAGE": "mend", "SLIPWAI_MEND": job}
    environment.pop("SLIPWAI_FAIRWAY", None)
    named = os.environ.get("SLIPWAI_MENDER")
    if named:
        brief = worktree.parent / f"{worktree.name}.json"
        brief.write_text(json.dumps({**told, "branch": branch}), encoding="utf-8")
        return [*shlex.split(named), job, str(brief)], environment
    import harness  # noqa: PLC0415 - only a real attempt needs the registry

    chosen, _said = harness.choose()
    template, _ = harness.template(chosen)
    line = template.replace("{prompt}", shlex.quote(prompt(job, worktree, branch, told)))
    return shlex.split(line), {**environment, **harness.child_environment(chosen)}


def failed_log(url: str, worktree: Path) -> str:
    """The failed run's log where the forge is GitHub's and `gh` can say it, written beside the worktree."""
    run = re.search(r"/runs/(\d+)", url or "")
    if not run or config().get("ci") not in (None, "gh"):
        return ""
    done = subprocess.run(["gh", "run", "view", run.group(1), "--log-failed"], cwd=ROOT, capture_output=True,
                          text=True, check=False)
    if done.returncode != 0 or not done.stdout.strip():
        return ""
    where = worktree.parent / f"{worktree.name}.log"
    where.write_text(done.stdout[-200_000:], encoding="utf-8")
    return str(where)


def start(job: str, key: str, onto: str, told: dict) -> tuple[logs.Entry, str]:
    """Make the worktree and start the session. (the `mend` line, why it could not start or "")."""
    branch = BRANCH.format(job=job, key=key)
    worktree = PLACE / f"{job}-{key}"
    git("worktree", "remove", "--force", str(worktree))
    PLACE.mkdir(parents=True, exist_ok=True)
    made = git("worktree", "add", "--quiet", "-b", branch, str(worktree), onto)
    line = logs.entry("mend", harbour=True, job=job, commit=str(told.get("commit", "")),
                      attempt=int(told.get("attempt", 1)), branch=branch,
                      **{name: told[name] for name in ("fairway", "parked", "need", "slice") if name in told})
    if made.returncode != 0:
        return line, f"no worktree could be made from {onto} ({(made.stderr or made.stdout).strip()})"
    if job == TRUNK:
        told = {**told, "log": failed_log(str(told.get("url", "")), worktree)}
    try:
        argv, environment = command(job, worktree, branch, told)
        out = (logs.run_dir(ROOT) / "running/mender.out")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as handle:
            child = subprocess.Popen(argv, cwd=worktree, env=environment, stdout=handle, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, RuntimeError, ImportError) as refused:
        return line, f"the mender could not be started: {refused}"
    FLYING[job] = child
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    held = {**told, "job": job, "pid": child.pid, "branch": branch, "onto": onto, "worktree": str(worktree),
            "started": time.time()}
    RECORD.write_text(json.dumps(held), encoding="utf-8")
    return line, ""


def finish(held: dict, land: Callable[[str], tuple[str, str]], onto: str, reverting: list[str]) -> logs.Entry:
    """The attempt is over: hold its branch to `refusal`, land it, say which, and clear up."""
    job, branch = str(held.get("job", TRUNK)), str(held.get("branch", ""))
    named = {name: held[name] for name in ("fairway", "parked", "need") if name in held}
    child = FLYING.pop(job, None)
    code = child.returncode if child is not None else None
    try:
        why = refusal(job, onto, branch, reverting, str(held.get("reads", "")))
        if not why and code not in (None, 0):
            why = f"the mender's session exited {code}"
        if why:
            return logs.entry("mend-failed", harbour=True, job=job, why=why,
                              commit=str(held.get("commit", "")), attempt=int(held.get("attempt", 1)), **named)
        landed, fault = land(branch)
        if fault:
            return logs.entry("mend-failed", harbour=True, job=job, why=fault,
                              commit=str(held.get("commit", "")), attempt=int(held.get("attempt", 1)), **named)
        # Its commits are trunk's now, so the branch is only a second name for them. A branch that did not
        # land is kept, so a person can read what the attempt tried.
        git("branch", "-D", branch)
        return logs.entry("mended", harbour=True, job=job, commit=landed, red=str(held.get("commit", "")),
                          attempt=int(held.get("attempt", 1)), **named)
    finally:
        worktree = Path(str(held.get("worktree", "")))
        if str(held.get("worktree", "")):
            git("worktree", "remove", "--force", str(worktree))
            for left in (worktree.parent / f"{worktree.name}.json", worktree.parent / f"{worktree.name}.log"):
                left.unlink(missing_ok=True)
        RECORD.unlink(missing_ok=True)


def overdue(held: dict) -> bool:
    started = held.get("started")
    return isinstance(started, int | float) and time.time() - started > bound()


# The two jobs, one pass at a time.

def since_red(harbour: list[logs.Entry]) -> list[logs.Entry]:
    """Every harbour line since trunk last went red, or [] where it is not red now."""
    for index in range(len(harbour) - 1, -1, -1):
        if harbour[index].kind == "trunk-green":
            return []
        if harbour[index].kind == "trunk-red":
            return harbour[index:]
    return []


def trunk_turn(state: str, said: dict, harbour: list[logs.Entry], broke: Callable[[str], dict]) -> dict | None:
    """What a red trunk needs started now — the attempt's `told` — or None. A `park` line, as `told["park"]`,
    once every attempt is spent."""
    if state != "red":
        return None
    after = since_red(harbour)
    mends = [e for e in after if e.kind == "mend" and e.fields.get("job") == TRUNK]
    if any(e.kind == "park" and e.fields.get("mend") for e in after):
        return None
    red = str(said.get("commit", ""))
    before = ""
    attempt = 1
    if mends:
        last = mends[-1]
        outcome = next((e for e in after if e.kind in ("mended", "mend-failed") and e.t >= last.t
                        and e.fields.get("job") == TRUNK), None)
        if outcome is None:
            # Nothing is in flight by now (`turn` finishes one first), so an attempt with no word is one that
            # vanished with the process that started it, and counts as tried.
            attempt, before = int(last.fields.get("attempt", 1)) + 1, "the last attempt ended with no word"
        elif outcome.kind == "mended" and red.startswith(str(last.fields.get("commit", ""))[:8]):
            return None  # the fix has landed; trunk's CI has not finished with it yet
        else:
            attempt = int(last.fields.get("attempt", 1)) + 1
            before = (str(outcome.fields.get("why", "")) if outcome.kind == "mend-failed"
                      else f"its fix landed as {str(outcome.fields.get('commit', ''))[:8]} and trunk is still red")
    if attempt > attempts():
        return {"park": logs.entry("park", harbour=True, fairway="", mend=True,
                                   why=f"trunk is red at {red[:8]} ({said.get('job', 'a job')}) and the trunk "
                                       f"mender's {attempts()} attempt(s) did not clear it; the last: {before}. "
                                       f"A person decides what happens; no merge is granted until trunk is green")}
    return {"commit": red, "job": said.get("job", ""), "url": said.get("url", ""), "attempt": attempt,
            "before": before, **broke(red)}


def eligible(need: object, by_person: bool) -> str:
    """The path a need's check reads where the mender may land it, or ""."""
    if not isinstance(need, dict) or not isinstance(need.get("check"), dict):
        return ""
    check = need["check"]
    path = str(check.get("path", ""))
    if check.get("kind") != "text" or not path or not any(path == p or path.startswith(p) for p in SHARED):
        return ""
    by = str(need.get("by", ""))
    return path if by == "fleet" or (by_person and by == "person") else ""


def need_turn(state: str, open_needs: list[tuple[str, logs.Entry, int]], harbour: list[logs.Entry]) -> dict | None:
    """The next need to land — its `told` — or None. One at a time, oldest first, only while trunk is green,
    and each one at most `attempts` times."""
    if state == "red":
        return None
    tried: dict[tuple[str, str, int], int] = {}
    for line in harbour:
        if line.kind == "mend" and line.fields.get("job") == NEED:
            key = (str(line.fields.get("fairway", "")), str(line.fields.get("parked", "")),
                   int(line.fields.get("need", -1)))
            tried[key] = tried.get(key, 0) + 1
    by_person = cruising()
    for fairway, park, index in open_needs:
        need = (park.fields.get("needs") or [])[index]
        reads = eligible(need, by_person)
        if not reads or tried.get((fairway, park.t, index), 0) >= attempts():
            continue
        check = need["check"]
        return {"commit": "", "attempt": tried.get((fairway, park.t, index), 0) + 1, "fairway": fairway,
                "parked": park.t, "need": index, "what": str(need.get("what", "")), "reads": reads,
                "check": f"{check.get('path')} holds `{check.get('has')}` on trunk",
                "said": str(park.fields.get("message") or park.fields.get("why") or "")[:600]}
    return None


def turn(state: str, said: dict, harbour: list[logs.Entry], open_needs: list[tuple[str, logs.Entry, int]],
         onto: Callable[[], str], land: Callable[[str], tuple[str, str]], broke: Callable[[str], dict],
         reverting: Callable[[str], list[str]]) -> list[logs.Entry]:
    """One pass: finish an attempt that is over, start the next thing owed. The lines to write."""
    written: list[logs.Entry] = []
    held = record()
    if held:
        if running():
            if not overdue(held):
                return []
            child = FLYING.get(str(held.get("job", "")))
            if child is not None:
                end(child)
        red = str(held.get("commit", ""))
        written.append(finish(held, land, onto(), reverting(red) if held.get("job") == TRUNK else []))
    seen = [*harbour, *written]
    wanted = trunk_turn(state, said, seen, broke)
    job = TRUNK
    if wanted is None:
        wanted, job = need_turn(state, open_needs, seen), NEED
    if wanted is None:
        return written
    if "park" in wanted:
        return [*written, wanted["park"]]
    key = (str(wanted["commit"])[:8] if job == TRUNK else f"{wanted['fairway']}-{int(wanted['need'])}") \
        + f"-{wanted['attempt']}"
    line, fault = start(job, key, onto(), wanted)
    written.append(line)
    if fault:
        written.append(logs.entry("mend-failed", harbour=True, job=job, why=fault,
                                  commit=str(wanted.get("commit", "")), attempt=int(wanted["attempt"]),
                                  **{n: wanted[n] for n in ("fairway", "parked", "need") if n in wanted}))
    return written
