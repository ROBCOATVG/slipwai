#!/usr/bin/env python3
"""What travels between machines: the logs, and the work that is still in flight.

Two processes here ran `git fetch origin refs/slipwai/logs/*` on every pass and **nothing anywhere wrote
those refs**. The fetch was ceremony: a second machine saw none of the first's lines, and getting one
machine's log onto another was a person with `scp`. That is section 14's fourth broken link, and
multiplayer sits downstream of it rather than beside it.

**One ref per writer, and nothing is ever merged into one file.** A deck log's only writer is the captain
holding that fairway, so it travels as `refs/slipwai/logs/<fairway>`. A harbour log's only writer is that
machine's harbourmaster, so it travels as `refs/slipwai/logs/harbour/<machine>`. Each ref has exactly one
writer and therefore neither can conflict — and folding two writers' lines into one file is the only way a
line can be lost, because append-only holds per writer and merging is what breaks it. Nothing here merges.

**A push that is not an append is refused.** The ref carries the whole file rather than a diff, so the one
thing that could silently drop lines is pushing a local log that is not a continuation of what the ref
already holds. That is checked on the way out and again on the way in, and a log that fails it is left
exactly where it is with a sentence saying so — a refusal is recoverable and a lost line is not.

**Where another machine's deck log lands is a cache of the ref, and only ever forward.** The decision of
2026-10-12 dissolved the question by saying a deck log lands nowhere and is read from the ref; what made
landing dangerous there was *appending another writer's lines into our own file*, which risks duplicates
and disorder. With one ref per fairway holding the whole file, and the claim making the writer unique at
any instant, there is nothing to merge: the local file is replaced wholesale by the ref's bytes, never
where this machine holds that fairway's claim, and never where the ref is not a continuation of what is
already here. So the ref stays the authority — `land` only ever copies it — and every reader of a deck log
goes on reading one file per fairway, knowing nothing about refs.

**And the in-flight branch travels the same way.** A captain holds no credential, so a slice branch lives
only on the machine that built it: a lapsed claim leaves the work not merely unclaimed but *unreachable*,
and whoever takes the stream starts from nothing. So the harbourmaster pushes it each pass as
`refs/slipwai/wip/<fairway>` — one ref per fairway's in-flight work, pushed by the machine that owns it —
and the taking captain lands it in its own berth and re-dispatches `/sail`, which enters at the first
incomplete stage because it reads artefacts from disk rather than conversation memory. The work survives
the machine, which is the whole point.

Standalone and dependency-free beyond `logs.py` and `claims.py` beside it: this ships inside a generated
project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import claims  # noqa: E402
import logs  # noqa: E402

#: Where the logs travel. A namespace no forge's branch protection covers and no clone fetches by default,
#: which is why the claims are there too.
REFS = "refs/slipwai/logs"
#: Where a fairway's in-flight branch travels. Not under `refs/heads/`: a WIP branch is a machine's working
#: state, and a forge that listed every half-finished slice as a branch would bury the ones people opened.
WIP = "refs/slipwai/wip"
#: The one directory a harbour log's ref lives under, so that `refs/slipwai/logs/harbour/<machine>` and
#: `refs/slipwai/logs/<fairway>` can never be mistaken for one another — a fairway called `harbour` would
#: need a slash in its name to collide, and a ref component cannot have one.
HARBOUR = "harbour"
#: A claim's lease, as a multiple of the stage bound. **Derived and not chosen**, which is the berth rule.
#: A captain that writes nothing for `stage_bound` ends that stage itself and says so, so the deck log of a
#: working captain is never silent for longer than that — and a lease above it therefore cannot take a
#: stream from a captain that is working. The guarantee falls out rather than being asserted. Two, because
#: liveness is judged on the *pushed* log and what a taker reads is older than what was written.
OF_STAGE = 2.0
#: How late the pushed log is behind the pen: the captain's heartbeat, the harbourmaster's push interval and
#: the taker's own fetch interval. The lease clears this whatever the telegraph is at, because at `stop`
#: every stage budget floors at a minute and a multiple of that alone would be under the round trip. `stop`
#: lights no berths, but a lease that *could* lapse on a live captain must not exist at any position.
ROUND_TRIP = 60.0 + 60.0 + 30.0
#: The empty tree, which every git repository has. A ref with no parent starts from it.
EMPTY_TREE = claims.EMPTY_TREE
#: What the branch for a slice is called. Declared here because travelling is what needs it to be one
#: name: a machine that pushed `slice/<id>` and one that landed some other spelling would be two names for
#: one piece of work, and neither would find the other's. The captain and the harbourmaster read it here.
BRANCH = "slice/{slice}"


def deck_ref(fairway: str) -> str:
    """Where one fairway's deck log travels. Its writer is whichever captain holds the claim."""
    return f"{REFS}/{fairway}"


def harbour_ref(machine: str) -> str:
    """Where one machine's harbour log travels. Its writer is that machine's harbourmaster, always."""
    return f"{REFS}/{HARBOUR}/{machine}"


def wip_ref(fairway: str) -> str:
    """Where one fairway's in-flight branch travels, pushed by the machine that holds the fairway."""
    return f"{WIP}/{fairway}"


def git(root: Path, *argv: str, machine: str = "") -> subprocess.CompletedProcess[str]:
    """One git command in this harbour. Never raises: every caller here reads the return code.

    A machine's name is the identity, as it is for a claim, because what a log ref records is which
    *machine* pushed it and not which person configured git on it.
    """
    named = {}
    if machine:
        named = {"GIT_AUTHOR_NAME": machine, "GIT_AUTHOR_EMAIL": f"{machine}@slipwai.invalid",
                 "GIT_COMMITTER_NAME": machine, "GIT_COMMITTER_EMAIL": f"{machine}@slipwai.invalid"}
    return subprocess.run(["git", *argv], cwd=root, capture_output=True, text=True, check=False,
                          env={**os.environ, **named} if named else None)


def forge(root: Path) -> bool:
    """Whether there is anywhere to travel to. Without one every ref here is local and travels nowhere."""
    return claims.forge(root)


def fetch(root: Path) -> None:
    """Bring in every log and every in-flight branch other machines have pushed.

    Forced, because what the forge holds is the answer and the local copy is a cache of it. Never fatal: a
    harbour on one machine has no remote, and one that cannot reach its forge still has its own logs.
    """
    if not forge(root):
        return
    git(root, "fetch", "--quiet", "--force", "origin",
        f"{REFS}/*:{REFS}/*", f"{WIP}/*:{WIP}/*")


def carried(root: Path, ref: str) -> tuple[str, str] | None:
    """What a log ref holds: (the path it is the log for, its whole text), or None where there is no ref.

    **The path is in the tree rather than in the ref's name**, so a landing knows exactly where the file
    goes without having to work out which feature a fairway belongs to — which is a question the ref's name
    cannot answer and a machine that has never run that fairway has nothing else to answer it with.
    """
    listed = git(root, "ls-tree", "-r", "--name-only", ref)
    if listed.returncode != 0:
        return None
    found = [line.strip() for line in listed.stdout.splitlines() if line.strip()]
    if len(found) != 1:
        return None
    shown = git(root, "show", f"{ref}:{found[0]}")
    return (found[0], shown.stdout) if shown.returncode == 0 else None


def held(root: Path, ref: str) -> str | None:
    """The log's whole text as this ref has it, or None where nothing has pushed it."""
    found = carried(root, ref)
    return found[1] if found else None


def last_heard(root: Path, ref: str) -> str:
    """The instant of the last line in this ref's log, or `""` where there are none.

    This is the evidence a lease is judged on, and it is deliberately the *pushed* log rather than the
    local one: what a second machine can know about the first is exactly what the first has pushed.
    """
    text = held(root, ref) or ""
    for line in reversed(text.splitlines()):
        if not line.strip():
            continue
        try:
            body = json.loads(line)
        except ValueError:
            return ""
        return str(body.get("t", "")) if isinstance(body, dict) else ""
    return ""


def lease(stage_bound: float) -> float:
    """Seconds a claim may go unheard from before another machine may take it.

    Derived from the stage bound and never chosen, so it moves with the telegraph for free: `stage_scale`
    multiplies every stage budget, so a harbour somebody has slowed down gets a longer lease without
    anybody editing a number.
    """
    return max(OF_STAGE * stage_bound, OF_STAGE * ROUND_TRIP)


def tree_of(root: Path, where: str, text: str, machine: str) -> str:
    """A tree holding this one file at this one path, built through an index of its own.

    An index rather than `mktree` because the path is nested — `.slipwai/logs/model/ordering.jsonl` is four
    deep — and `mktree` writes one flat level at a time. The index is a temporary file and is never the
    repository's own, so nothing a person has staged is touched.
    """
    made = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=root, input=text,
                          capture_output=True, text=True, check=False)
    if made.returncode != 0:
        raise RuntimeError((made.stderr or made.stdout).strip() or "git hash-object failed")
    blob = made.stdout.strip()
    with tempfile.TemporaryDirectory() as scratch:
        index = {**os.environ, "GIT_INDEX_FILE": str(Path(scratch) / "index"),
                 "GIT_AUTHOR_NAME": machine, "GIT_AUTHOR_EMAIL": f"{machine}@slipwai.invalid",
                 "GIT_COMMITTER_NAME": machine, "GIT_COMMITTER_EMAIL": f"{machine}@slipwai.invalid"}
        added = subprocess.run(["git", "update-index", "--add", "--cacheinfo", f"100644,{blob},{where}"],
                               cwd=root, env=index, capture_output=True, text=True, check=False)
        if added.returncode != 0:
            raise RuntimeError((added.stderr or added.stdout).strip() or "git update-index failed")
        written = subprocess.run(["git", "write-tree"], cwd=root, env=index, capture_output=True,
                                 text=True, check=False)
        if written.returncode != 0:
            raise RuntimeError((written.stderr or written.stdout).strip() or "git write-tree failed")
        return written.stdout.strip()


def tip(root: Path, ref: str) -> str:
    """What this ref is at, or `""` where it is at nothing."""
    found = git(root, "rev-parse", "--verify", "--quiet", ref)
    return found.stdout.strip() if found.returncode == 0 else ""


def swap(root: Path, ref: str, commit: str, was: str) -> bool:
    """Move the ref to `commit` only if it is still at `was` — the same compare-and-swap a claim uses.

    With a forge the forge decides, because it is the one copy two machines share: a push that is not a
    fast-forward of what it holds is refused by `receive-pack`, which is nothing of ours. Without one there
    is only the local ref, and `update-ref`'s own old-value argument is the same test made smaller.
    """
    if forge(root):
        pushed = git(root, "push", "--quiet", "origin", f"{commit}:{ref}")
        if pushed.returncode != 0:
            fetch(root)
            return False
        git(root, "update-ref", ref, commit)
        return True
    return git(root, "update-ref", ref, commit, was).returncode == 0


def appends(onto: str, text: str) -> bool:
    """Whether `text` is a continuation of `onto` — the whole of the rule, in one line.

    A byte prefix and not a line count: a log that was rewritten to the same length is still not the log
    the ref holds, and the one failure here that cannot be recovered from is a line nobody can tell is gone.
    """
    return text.startswith(onto)


def push_log(root: Path, path: Path, ref: str, machine: str) -> tuple[bool, str]:
    """Put this log's bytes on its ref. (it travelled, why it did not).

    Refused where the local log is not a continuation of the ref's, which is the one case that would drop
    lines nobody could tell were missing. Nothing happens where they are already the same: every pass
    pushes and most passes have nothing new, and a commit per pass would make a ref's history longer than
    the log it carries.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as fault:
        return False, f"{path} cannot be read ({fault}), so there is nothing to put on {ref}"
    try:
        where = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return False, f"{path} is not inside {root}, and a log ref carries the log's own path"
    there = held(root, ref)
    if there is not None and not appends(there, text):
        return False, (f"{ref} holds {len(there.splitlines())} line(s) that {where} is not a continuation "
                       f"of, so pushing it would drop them and nothing would say which. A log ref only "
                       f"ever appends. Read it with `git show {ref}:{where}` and reconcile before the next "
                       f"pass")
    if there == text:
        return True, ""
    try:
        tree = tree_of(root, where, text, machine)
    except RuntimeError as fault:
        return False, f"{ref} could not be written: {fault}"
    was = tip(root, ref)
    argv = ["commit-tree", tree, "-m", f"{len(text.splitlines())} line(s)"]
    if was:
        argv += ["-p", was]
    made = git(root, *argv, machine=machine)
    if made.returncode != 0:
        return False, f"{ref} could not be written: {(made.stderr or made.stdout).strip()}"
    if not swap(root, ref, made.stdout.strip(), was):
        return False, (f"{ref} moved while this pass was reading it, which is another writer for a ref "
                       f"that has one. Nothing was pushed; the next pass reads it afresh")
    return True, ""


def log_refs(root: Path) -> list[str]:
    """Every log ref this machine can see, in name order."""
    found = git(root, "for-each-ref", "--format=%(refname)", REFS)
    return sorted(line.strip() for line in found.stdout.splitlines() if line.strip())


def land_ref(root: Path, ref: str) -> str:
    """Write one ref's log into the file it is the log for, and say which. `""` where nothing was written.

    Nothing is written where the file is already the ref's, and nothing where the ref is not a continuation
    of what is here: a ref and a file that disagree about their shared past is one of us being wrong, and
    overwriting would destroy the evidence of which.
    """
    found = carried(root, ref)
    if found is None:
        return ""
    where, text = found
    target = root / where
    if target.is_file():
        try:
            already = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""
        if already == text or not appends(already, text):
            return ""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return where


def land(root: Path, machine: str, held: list[str]) -> list[str]:
    """Write what other machines have pushed into the files every reader here already reads.

    Two files are never touched, and both for the same reason — one writer per file:

    - **this machine's own harbour log**, which its harbourmaster is appending to; and
    - **the deck log of any fairway in `held`**, which this machine's captain is appending to.

    Nor is any file the ref is not a continuation of. A ref and a file that disagree about their shared
    past is one of us being wrong, and overwriting would destroy the evidence of which.

    It fetches first, because landing what was fetched some passes ago is landing a stale answer, and the
    cost of asking is one `git fetch` of a namespace nothing else is in.
    """
    fetch(root)
    skip = {harbour_ref(machine), *(deck_ref(fairway) for fairway in held)}
    return [where for ref in log_refs(root) if ref not in skip
            if (where := land_ref(root, ref))]


def push_wip(root: Path, branch: str, ref: str) -> tuple[bool, str]:
    """Put a fairway's in-flight branch on its ref. (it travelled, why it did not).

    `--force-with-lease` and not a plain force: the ref is rewritten whenever a captain rebases in its own
    berth, so a fast-forward is not the rule here — but a push that discarded commits another machine put
    there would be exactly what the never-list forbids, and the lease is the difference.
    """
    commit = tip(root, f"refs/heads/{branch}")
    if not commit:
        return False, (f"there is no branch {branch} on this machine, so {ref} has nothing to carry. "
                       f"`/sail` makes it at the slice's first rung")
    was = tip(root, ref)
    if was == commit:
        return True, ""
    if not forge(root):
        moved = git(root, "update-ref", ref, commit, was)
        return (True, "") if moved.returncode == 0 else (False, (moved.stderr or moved.stdout).strip())
    pushed = git(root, "push", "--quiet", f"--force-with-lease={ref}:{was}", "origin", f"{branch}:{ref}")
    if pushed.returncode != 0:
        said = (pushed.stderr or pushed.stdout).strip().splitlines()
        return False, (f"{ref} moved under this pass ({said[-1] if said else 'git failed'}), which is "
                       f"another machine holding {branch}. Nothing was pushed")
    git(root, "update-ref", ref, commit)
    return True, ""


def dirty(root: Path) -> list[str]:
    """The tracked paths with uncommitted changes, which are a person's and not ours to discard.

    Untracked files are not counted: a run's own `.slipwai/` is untracked in anything but a generated
    project, and counting it would refuse every takeover there has ever been.
    """
    found = git(root, "status", "--porcelain", "--untracked-files=no")
    return sorted({line[3:].strip() for line in found.stdout.splitlines() if line.strip()})


def land_wip(root: Path, ref: str, branch: str) -> tuple[bool, str]:
    """Bring a fairway's in-flight branch into this berth and stand on it. (it landed, why it did not).

    This is what makes a lapsed claim recoverable rather than merely transferable: `/sail` enters at the
    first incomplete stage because it reads the artefacts on disk, and the artefacts are on this branch.
    """
    fetch(root)
    commit = tip(root, ref)
    if not commit:
        return False, (f"nothing has pushed {ref}, so this fairway's in-flight work is still only on the "
                       f"machine that built it and there is nothing here to carry on from")
    outstanding = dirty(root)
    if outstanding:
        return False, (f"this checkout has uncommitted changes to {', '.join(outstanding[:5])}, which are "
                       f"somebody's and not this process's to discard. Commit or stash them and take the "
                       f"fairway again")
    moved = git(root, "checkout", "--quiet", "-B", branch, commit)
    if moved.returncode != 0:
        said = (moved.stderr or moved.stdout).strip().splitlines()
        return False, f"{branch} could not be made from {ref}: {said[-1] if said else 'git failed'}"
    return True, ""


def ours(root: Path) -> list[str]:
    """The fairways this machine holds the claim for, which are the only deck logs it may push.

    One ref per writer, and a fairway's writer is whichever captain holds it: a machine pushing the log of
    a fairway it does not hold would be a second writer on that ref, which is the one thing there may never
    be. Asked in one fetch rather than one per fairway.
    """
    machine = logs.machine()
    fairways = [path.stem for path in logs.deck_logs(root)]
    return [fairway for fairway, claim in claims.every(root, fairways).items()
            if claim is not None and claim.machine == machine]


def in_flight(path: Path) -> str:
    """The slice this fairway is still working on — claimed, and not merged — or `""` where there is none.

    What travels is work that is *in flight*: a merged slice's branch is in trunk already, and a WIP ref
    that went on being pushed after the merge would be a ref nobody reads growing for ever.
    """
    try:
        found = logs.fold(path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeDecodeError, logs.Unreadable):
        return ""
    merged = {str(entry.fields.get("slice", "")) for entry in found if entry.kind == "merged"}
    for entry in reversed(found):
        if entry.kind == "claimed" and str(entry.fields.get("slice", "")) not in merged:
            return str(entry.fields.get("slice", ""))
    return ""


def arrive(root: Path) -> list[str]:
    """Bring in what other machines have written, and put it where this project's readers already look.

    Never fatal: a project on one machine has no remote, and one that cannot reach its forge still has
    every local fairway to read. What it returns is the files it wrote, for a caller that says so.
    """
    return land(root, logs.machine(), ours(root))


def wrote(root: Path, machine: str) -> list[str]:
    """The fairways whose deck log this machine is the author of, **whether or not it still holds them**.

    Not `ours`, and the difference is a line that would otherwise never arrive. A captain writes its final
    `merged` or `parked` line and *then* releases; the next pass still owes that suffix to the forge, and a
    set built from held claims alone would have dropped the fairway one pass before its last line travelled.
    A released claim retains its author, so this is still one publisher until the claim changes hands, and
    a cache on another machine cannot publish itself.
    """
    claims.fetch(root)
    return [path.stem for path in logs.deck_logs(root)
            if (claim := claims.read(root, path.stem)) is not None and claim.machine == machine]


def departing(root: Path, machine: str, authored: list[str]) -> list[tuple[Path, str]]:
    """Each file this machine may push, with the ref it travels as: its own harbour log, and the deck log
    of every fairway it wrote. Nothing else — a second writer on a ref is the one thing there may never be.
    """
    found = [(root / logs.harbour_path(machine), harbour_ref(machine))]
    found += [(path, deck_ref(path.stem)) for path in logs.deck_logs(root) if path.stem in authored]
    return [(path, ref) for path, ref in found if path.is_file()]


def depart(root: Path) -> tuple[list[str], list[str]]:
    """Put this machine's logs and in-flight branches where the other machines can read them.

    (the refs that travelled, the reasons the rest did not). This is the writing end of section 14's fourth
    broken link: both processes fetched `refs/slipwai/logs/*` and neither ever wrote them, so the fetch was
    ceremony and getting one machine's log onto another was a person with `scp`.

    Every refusal is returned rather than swallowed. A push that is not an append is a log about to lose
    lines, and the whole design rests on hearing about that rather than on it being rare.
    """
    machine = logs.machine()
    if not forge(root):
        return [], []
    # Two different sets, and conflating them loses a line. A **log** travels for every fairway this
    # machine authored, released or not, because the release follows the final line. A **branch** travels
    # only for one still held: pushing the in-flight work of a fairway somebody else has taken would be a
    # second writer on that ref.
    authored, held = wrote(root, machine), ours(root)
    went: list[str] = []
    refused: list[str] = []
    for path, ref in departing(root, machine, authored):
        ok, why = push_log(root, path, ref, machine)
        if ok:
            went.append(ref)
        else:
            refused.append(why)
    for path in logs.deck_logs(root):
        slice_id = in_flight(path) if path.stem in held else ""
        if not slice_id:
            continue
        ok, why = push_wip(root, BRANCH.format(slice=slice_id), wip_ref(path.stem))
        if ok:
            went.append(wip_ref(path.stem))
        else:
            refused.append(why)
    return went, refused


def arrived(root: Path) -> int:
    """`--arrive`: land every other machine's lines here, and say what landed."""
    machine = logs.machine()
    if not forge(root):
        print(f"travel: no `origin`, so nothing travels onto {machine} and nothing is missing here")
        return 0
    landed = arrive(root)
    for where in landed:
        print(f"travel: landed {where}")
    print(f"travel: {len(landed)} log(s) landed on {machine}; what the other machines wrote is here")
    return 0


def departed(root: Path) -> int:
    """`--depart`: push what this machine wrote, and fail loudly where a log could not travel."""
    machine = logs.machine()
    if not forge(root):
        print(f"travel: no `origin`, so nothing travels off {machine}. Add a remote and the logs and the "
              f"in-flight branches follow it")
        return 0
    went, refused = depart(root)
    for ref in went:
        print(f"travel: pushed {ref}")
    for why in refused:
        print(f"travel: {why}", file=sys.stderr)
    if refused:
        print(f"travel: {len(refused)} of {len(went) + len(refused)} did not travel off {machine}; what is "
              f"written here is not yet readable anywhere else", file=sys.stderr)
        return 1
    print(f"travel: {len(went)} ref(s) pushed from {machine}; what was written here is readable elsewhere")
    return 0


def main(argv: list[str]) -> int:
    """What has travelled, and — asked for — what travels now.

    `--arrive` and `--depart` are the two halves `/sail` runs: the loop's memory is in the deck logs, and a
    session that cannot read the last machine's lines reads exactly like a session in a project where the
    work was never done. Bare, this still only reads.
    """
    root = claims.project_root(Path(__file__).resolve())
    machine = logs.machine()
    if "--arrive" in argv:
        return arrived(root)
    if "--depart" in argv:
        return departed(root)
    if not forge(root):
        print(f"travel: this harbour has no `origin`, so nothing travels off {machine}. Add a remote and "
              f"the logs and the in-flight branches follow it")
        return 0
    if "--no-fetch" not in argv:
        fetch(root)
    for ref in log_refs(root):
        found = carried(root, ref)
        if found is None:
            continue
        where, text = found
        print(f"{ref}: {len(text.splitlines())} line(s) — {where}")
    for ref in sorted(line.strip() for line in
                      git(root, "for-each-ref", "--format=%(refname)", WIP).stdout.splitlines()
                      if line.strip()):
        print(f"{ref}: {tip(root, ref)[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
