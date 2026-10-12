#!/usr/bin/env python3
"""Who holds a fairway: one git ref per fairway, taken by a push a second taker cannot win.

Two people running version 2 on two machines works today in a way that is misleading. The logs sync, the
marks carry, the board folds — and **nothing stopped two machines running a captain for the same fairway**,
which is two processes appending to one `.slipwai/logs/<feature>/<fairway>.jsonl` through two worktrees.
That is a merge conflict in the one file the whole design promised would never have one, and, where one
side forces the ref, lines nobody can tell are missing. A `claimed` line was never a candidate for fixing
it: the deck log is the thing being protected.

**A claim is `refs/slipwai/claims/<fairway>`.** A captain takes it before it writes `claimed`, and a
machine that cannot take it is told who holds it and since when. The mechanism is a push that is not a
fast-forward, which every forge refuses — an atomic compare-and-swap with nothing of ours running, no
server, no lease daemon and no election. With no forge at all it is `git update-ref` against the value the
ref must already have, which is the same compare-and-swap made smaller rather than a weaker rule.

**The ref is a chain and nothing is ever deleted.** Its tip is a commit whose author is the machine, whose
date is *since when*, and whose message is `held` or `released`. Taking a free fairway pushes a child of
the tip you read; if another machine took it between the read and the push, your commit's parent is no
longer the tip and the push is refused — which is the compare-and-swap, written as git already writes it.
Releasing pushes a `released` child rather than deleting the ref, so `git log refs/slipwai/claims/ordering`
still answers *who had this fairway last Tuesday*, which is a question somebody asks after a bad merge.

**`held_by` in the split's table is rendered from this and written by nothing.** There were two answers to
*who holds this fairway* — a name in a markdown table and a running process with a pid — and a third would
have been worse than either. A person taking a lane by hand takes the same ref, with `--take` below.

    python3 scripts/agents/claims.py                    # every fairway the chart has, and who holds it
    python3 scripts/agents/claims.py --take ordering    # take it by hand, as a captain would
    python3 scripts/agents/claims.py --release ordering # give it back

Standalone and dependency-free beyond `logs.py` beside it: this ships inside a generated project, which has
no slipwai to import.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import logs  # noqa: E402

#: Where a claim lives. One ref per fairway, under a namespace no forge's branch protection covers and no
#: clone fetches by default — the logs are already there, for the same reasons.
REFS = "refs/slipwai/claims"
#: The one thing in a harbour that genuinely needs a decider, taken and released exactly as a claim is.
#: The harbour log became one file per machine so the single writer could be removed rather than elected —
#: and the merge is what that costs: two harbourmasters rebasing onto one trunk at once is two gates each
#: measured against a trunk the other is about to move. Section 14 settled that merges are one at a time in
#: request order, so the same mechanism serialises them across machines as within one.
MERGE = "refs/slipwai/merge"
#: The two things a claim's tip can say. Nothing else is written, and a tip saying anything else is read as
#: held, because an unreadable claim must never read as free.
HELD = "held"
RELEASED = "released"
#: The empty tree, which every git repository has whether or not anything is in it. A claim carries no
#: content — the commit's author, date and message are the whole of it — so this is what it points at.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
#: Separates the fields of one `git show`. The unit separator, asked for with git's own `%x1f` escape: a
#: NUL is what one would otherwise use and it cannot be carried in an argument vector.
GAP = "\x1f"


@dataclass(frozen=True)
class Claim:
    """One fairway's claim as its ref says it is."""

    fairway: str
    machine: str
    since: str
    state: str
    commit: str
    local: bool

    def held(self) -> bool:
        return self.state != RELEASED

    def said(self) -> str:
        """The refusal, as a captain prints it: who holds it, since when, and what to do about it."""
        where = " on this machine, which has no forge to push to" if self.local else ""
        return (f"{self.fairway} is held by {self.machine} since {self.since}{where}. One machine holds a "
                f"fairway at a time, or two captains append to one deck log. It frees when that captain "
                f"stops, or run `python3 scripts/agents/claims.py --release {self.fairway}` there")


@dataclass(frozen=True)
class Taken:
    """What came of trying to take one: whether it is ours, who has it, and why not where it is not."""

    ours: bool
    holder: Claim | None
    why: str = ""
    #: Whether this was taken off another machine on a lapsed lease, rather than taken free. The caller
    #: has to know: a takeover inherits a stream somebody else was mid-slice in, so the work on that
    #: machine's branch has to be brought over before anything is dispatched. `holder` is who it was.
    took_over: bool = False


def ref(fairway: str) -> str:
    """Where one claim lives: a fairway's under `refs/slipwai/claims/`, or a ref named outright.

    The merge is named outright, because there is one of it and it is not a fairway — and because a
    fairway's name can never begin `refs/`, the two can never collide on one ref by accident.
    """
    return fairway if fairway.startswith("refs/") else f"{REFS}/{fairway}"


def git(root: Path, *argv: str, machine: str = "") -> subprocess.CompletedProcess[str]:
    """One git command in this harbour. Never raises: every caller here reads the return code.

    A machine's name is passed as the identity rather than the repository's, because what the ref has to
    record is which *machine* holds the fairway and not which person configured git on it. That also makes
    the claim readable with `git log` and no tooling of ours.
    """
    named = {}
    if machine:
        named = {"GIT_AUTHOR_NAME": machine, "GIT_AUTHOR_EMAIL": f"{machine}@slipwai.invalid",
                 "GIT_COMMITTER_NAME": machine, "GIT_COMMITTER_EMAIL": f"{machine}@slipwai.invalid"}
    return subprocess.run(["git", *argv], cwd=root, capture_output=True, text=True, check=False,
                          env={**os.environ, **named} if named else None)


def repository(root: Path) -> bool:
    """Whether this is a git repository at all. A directory that is not one can hold no fairway."""
    return git(root, "rev-parse", "--git-dir").returncode == 0


def forge(root: Path) -> bool:
    """Whether there is somewhere to push a claim to. Without one the ref is local and says so."""
    return git(root, "remote", "get-url", "origin").returncode == 0


def fetch(root: Path) -> None:
    """Bring every claim ref up to date. Forced, because what the forge says is the answer and the local
    copy is a cache of it — a non-fast-forward here is another machine having taken a fairway, which is the
    normal case and not a conflict."""
    # The shared merge lock is a raw ref outside the fairway namespace. A wildcard allows it
    # to be absent before the first merge; an exact missing ref would abort the entire fetch.
    git(root, "fetch", "--quiet", "--force", "origin", f"{REFS}/*:{REFS}/*", f"{MERGE}*:{MERGE}*")


def read(root: Path, fairway: str) -> Claim | None:
    """The claim as the local ref has it, without reaching the forge."""
    shown = git(root, "show", "-s", "--format=%H%x1f%an%x1f%aI%x1f%s", ref(fairway))
    if shown.returncode != 0:
        return None
    parts = shown.stdout.strip().split(GAP)
    if len(parts) != 4:
        return None
    commit, who, when, said = parts
    return Claim(fairway=fairway, machine=who, since=when, state=said.strip() or HELD, commit=commit,
                 local=not forge(root))


def holder(root: Path, fairway: str) -> Claim | None:
    """The claim's tip, whatever it says, after asking the forge where there is one."""
    if not repository(root):
        return None
    if forge(root):
        fetch(root)
    return read(root, fairway)


def held_by(root: Path, fairway: str) -> Claim | None:
    """Who holds this fairway, or None where nobody does. A released tip is nobody."""
    found = holder(root, fairway)
    return found if found is not None and found.held() else None


def mint(root: Path, fairway: str, machine: str, state: str, parent: str = "") -> str:
    """A new tip for this fairway's claim: a commit saying who, when and what, on top of what was read."""
    argv = ["commit-tree", EMPTY_TREE, "-m", state]
    if parent:
        argv += ["-p", parent]
    made = git(root, *argv, machine=machine)
    if made.returncode != 0:
        raise RuntimeError((made.stderr or made.stdout).strip() or "git commit-tree failed")
    return made.stdout.strip()


def swap(root: Path, fairway: str, commit: str, was: str) -> bool:
    """Move the claim to `commit` only if it is still at `was`. The compare-and-swap, both ways round.

    With a forge the forge decides, because it is the one copy two machines share: a push that is not a
    fast-forward of what it holds is refused by `receive-pack`, which is the whole mechanism and is nothing
    of ours. The local ref is then moved to match. Without one there is only the local ref, and
    `update-ref`'s own old-value argument is the same test — `""` meaning *this must not exist yet*.
    """
    if forge(root):
        pushed = git(root, "push", "--quiet", "origin", f"{commit}:{ref(fairway)}")
        if pushed.returncode != 0:
            fetch(root)
            return False
        git(root, "update-ref", ref(fairway), commit)
        return True
    return git(root, "update-ref", ref(fairway), commit, was).returncode == 0


def instant(said: str) -> datetime | None:
    """One of our own timestamps as a moment, or None where it is not one we wrote.

    None and not a guess: an instant nothing can read is not evidence that a captain is gone, and the one
    thing a lease may never do is take a stream from somebody who is working.
    """
    try:
        return datetime.fromisoformat(said.replace("Z", "+00:00"))
    except ValueError:
        return None


def lapsed(found: Claim, lease: float, heard: str) -> bool:
    """Whether this claim's holder has gone quiet for longer than the lease allows.

    Measured from the later of *when it was taken* and *when its captain last wrote*, because a captain
    that has just taken its claim and not yet written a line is starting rather than gone — a lease run
    from an empty log would take the stream off it before its first rung.

    `heard` is read off the **pushed** log, because what one machine can know about another is exactly what
    the other has pushed. `lease` of `0` is off, and off is the default: working the number out from the
    harbour's own stage budgets is the caller's job, and a caller that has not done it did not mean *take
    this off them*.
    """
    if lease <= 0:
        return False
    since = instant(found.since)
    if since is None:
        return False
    last = since
    if heard:
        spoke = instant(heard)
        if spoke is None:
            return False
        last = max(last, spoke)
    return (datetime.now(UTC) - last).total_seconds() > lease


def take(root: Path, fairway: str, machine: str, lease: float = 0.0, heard: str = "") -> Taken:
    """Take this fairway's claim, or say who has it. Idempotent: holding it already is taking it.

    Idempotent because a captain takes the claim on every turn, so taking what you already hold is the
    common case rather than an error — a restarted captain that could not re-take its own fairway would
    have locked itself out of its own work.

    **A claim held by a machine nothing has been heard from for `lease` seconds is taken over**, which is
    what stops a closed laptop parking a stream for ever: a captain killed outright never releases its
    claim, and until there was a lease the only answer was a person running `--release` on a machine that
    may be shut. The push is still the same compare-and-swap — a child of the tip that was read — so two
    machines deciding at once that a third has gone cannot both win.
    """
    migration = root / ".slipwai/migration.json"
    if migration.is_file():
        try:
            state = json.loads(migration.read_text(encoding="utf-8"))
            if state.get("v") != 1 or not isinstance(state.get("features"), dict):
                raise ValueError("unknown migration state")
            if any(not isinstance(item, dict) or not all(isinstance(item.get(key), list) and
                   all(isinstance(name, str) and name for name in item[key]) for key in ("proposed", "unplaced"))
                   for item in state["features"].values()):
                raise ValueError("malformed migration feature")
            pending = any(fairway in (item.get("proposed") or []) or
                          (fairway == "unplaced" and item.get("unplaced"))
                          for item in state["features"].values())
            if pending:
                return Taken(False, None, f"{fairway} needs confirmation; "
                             "run `python3 scripts/check-migration.py --confirm` after placing every slice")
        except (OSError, ValueError, TypeError, AttributeError):
            return Taken(False, None, "migration state is unreadable; restore .slipwai/migration.json "
                         "and run `python3 scripts/check-migration.py` before taking a claim")
    if not repository(root):
        return Taken(True, None, "there is no git repository here, so nothing can hold a fairway and a "
                                 "second captain on this one cannot be refused; `git init` is what fixes it")
    found = holder(root, fairway)
    over = False
    if found is not None and found.held():
        if found.machine == machine:
            return Taken(True, found)
        if not lapsed(found, lease, heard):
            return Taken(False, found, found.said())
        over = True
    try:
        commit = mint(root, fairway, machine, HELD, parent=found.commit if found else "")
    except RuntimeError as fault:
        return Taken(False, found, f"the claim on {fairway} could not be written: {fault}")
    if swap(root, fairway, commit, found.commit if found else ""):
        if over and found is not None:
            # `holder` is who it was taken *from*, not who has it now: the caller's next move is to bring
            # that machine's in-flight work over, and for that it has to know whose it was.
            return Taken(True, found, f"{fairway} was taken over from {found.machine}, which has written "
                                      f"nothing since {found.since} and is past its lease", took_over=True)
        return Taken(True, read(root, fairway))
    again = holder(root, fairway)
    if again is not None and again.held():
        return Taken(again.machine == machine, again, "" if again.machine == machine else again.said())
    return Taken(False, again, f"the claim on {fairway} was refused and nothing holds it; this is a forge "
                               f"that cannot be reached, not a race. Retry, or run with no remote")


def release(root: Path, fairway: str, machine: str) -> bool:
    """Give this fairway back. False where it was not this machine's to give."""
    found = held_by(root, fairway)
    if found is None or found.machine != machine:
        return False
    try:
        commit = mint(root, fairway, machine, RELEASED, parent=found.commit)
    except RuntimeError:
        return False
    return swap(root, fairway, commit, found.commit)


def every(root: Path, fairways: list[str]) -> dict[str, Claim | None]:
    """Who holds each of these, in one fetch rather than one per fairway."""
    if not repository(root):
        return dict.fromkeys(fairways)
    if forge(root):
        fetch(root)
    found = {}
    for fairway in fairways:
        claim = read(root, fairway)
        found[fairway] = claim if claim is not None and claim.held() else None
    return found


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


def charted(root: Path) -> list[str]:
    """Every fairway the chart has, so the command says who holds each rather than only the taken ones."""
    sys.path.insert(0, str(HERE))
    try:
        import clearance
    except ImportError:  # pragma: no cover - a project without the chart reader
        return []
    try:
        chart, _ = clearance.chart()
    except (OSError, ValueError, SystemExit):  # pragma: no cover - a project with no chart yet
        return []
    return sorted({str((body or {}).get("fairway", "")) for body in (chart.get("slices") or {}).values()}
                  - {""})


def main(argv: list[str]) -> int:
    root = project_root(Path(__file__).resolve())
    machine = logs.machine()
    if "--take" in argv:
        fairway = argv[argv.index("--take") + 1]
        taken = take(root, fairway, machine)
        print(f"claims: {fairway} is {machine}'s" if taken.ours else f"claims: {taken.why}")
        return 0 if taken.ours else 1
    if "--release" in argv:
        fairway = argv[argv.index("--release") + 1]
        if release(root, fairway, machine):
            print(f"claims: {fairway} is free")
            return 0
        print(f"claims: {fairway} is not {machine}'s to release; `python3 scripts/agents/claims.py` says "
              f"whose it is")
        return 1
    fairways = charted(root)
    if not fairways:
        print("claims: the chart has no fairways yet, so there is nothing to hold")
        return 0
    for fairway, claim in every(root, fairways).items():
        print(f"{fairway}: {claim.machine} since {claim.since}" if claim else f"{fairway}: —")
    if not forge(root):
        print(f"note: this harbour has no `origin` to push a claim to, so every claim above is local to "
              f"{machine} and no other machine can see it")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except IndexError:
        print("claims: --take and --release each take a fairway, as `claims.py --take ordering`",
              file=sys.stderr)
        raise SystemExit(1) from None
