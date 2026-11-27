#!/usr/bin/env python3
"""Commit a stage's files onto a branch of their own and hand that branch on to trunk — never onto local trunk.

The board's triage ran in the main checkout while it was on `main`, and `commands/triage.md` said to commit
on the current branch. It did, twice, and pushed nothing. From then on every merge the harbourmaster granted
went to the forge's `main`, and it could not bring local `main` forward without throwing those two commits
away — rightly, it would not. Thirteen hours later the checkout was 1168 commits behind and the board,
drawn from it, showed an old project.

So a stage that writes files outside a slice does not commit them where it stands. This does it:

1. **A commit built from the forge's trunk, not from this checkout's.** The files named are laid over
   `origin/<trunk>` (local trunk only where there is no remote) in an index of their own, and committed on
   `<kind>/<slug>`. Nothing in the working tree, the index or any existing branch is touched — local trunk
   least of all — so the person's checkout, and the board that reads it, are exactly as they were.
2. **Pushed**, where there is an `origin`, so the work exists somewhere other than this folder.
3. **Queued for the harbourmaster** under `.slipwai/run/landing/`. Its next pass lands the branch the way it
   lands a slice — rebase onto trunk, the full gate, advance — and writes `landed` or `land-refused`, so it
   reaches trunk with nobody present and through the one gate everything else takes.

A checkout that does still hold the same files untracked is not left stuck behind: when the harbourmaster
brings local trunk level and those files are what block the fast-forward, it keeps their bytes and puts
them back after (`harbourmaster.level`). Nothing here, or there, resets, rebases or drops a commit.

    python3 scripts/agents/landing.py <kind>/<slug> "<commit message>" <path>...
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import logs  # noqa: E402
import need_check  # noqa: E402


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
#: The prefixes a queued branch may carry: a stage's own, never a slice's (the captain asks for those) and
#: never trunk. The harbourmaster refuses anything else it finds queued.
KINDS = ("triage", "assess", "draft", "launch", "stage")
BRANCH = re.compile(rf"^(?:{'|'.join(KINDS)})/[A-Za-z0-9][\w.,-]*$")


def git(*argv: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], cwd=ROOT, capture_output=True, text=True, check=False,
                          env={**os.environ, **(env or {})}, encoding="utf-8", errors="replace")


def queue() -> Path:
    """Where branches wait for the harbourmaster: one file each, on this machine."""
    return logs.run_dir(ROOT) / "landing"


def trunk() -> str:
    try:
        held = json.loads((ROOT / "harbour.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        held = {}
    return need_check.trunk_name(ROOT, held.get("trunk") if isinstance(held, dict) else None)


def free(branch: str) -> str:
    """`branch`, or `branch-2`, `branch-3`… where one of that name already exists here."""
    name, count = branch, 1
    while git("rev-parse", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0:
        count += 1
        name = f"{branch}-{count}"
    return name


def commit(branch: str, message: str, paths: list[str]) -> tuple[str, str]:
    """(the branch it is on, "") once committed, or ("", why not). Builds the commit without touching the
    working tree, the person's index or any branch but the new one."""
    if not BRANCH.match(branch):
        return "", f"{branch!r} is not a stage's own branch: <{'|'.join(KINDS)}>/<slug>"
    name = trunk()
    onto = need_check.base(ROOT, name)
    if git("rev-parse", "--verify", "--quiet", onto).returncode != 0:
        return "", f"there is no {onto} to build on"
    if git("var", "GIT_COMMITTER_IDENT").returncode != 0:
        return "", "this repository has no `user.name` and `user.email`; `git config user.email you@example.com`"
    with tempfile.TemporaryDirectory() as scratch:
        index = {"GIT_INDEX_FILE": str(Path(scratch) / "index")}
        for step in (["read-tree", onto], ["add", "--", *paths]):
            done = git(*step, env=index)
            if done.returncode != 0:
                return "", f"`git {' '.join(step[:2])}` failed: {(done.stderr or done.stdout).strip()}"
        tree = git("write-tree", env=index).stdout.strip()
    if tree == git("rev-parse", f"{onto}^{{tree}}").stdout.strip():
        return "", f"nothing to land: {', '.join(paths)} already read on {onto} as they do here"
    made = git("commit-tree", tree, "-p", onto, "-m", message)
    if made.returncode != 0:
        return "", f"the commit could not be made: {made.stderr.strip()}"
    branch = free(branch)
    git("update-ref", f"refs/heads/{branch}", made.stdout.strip())
    return branch, ""


def hand_on(branch: str, message: str) -> str:
    """Push the branch where there is a remote, and queue it for the harbourmaster. What was done, in words."""
    said = [f"committed on {branch}, built from {need_check.base(ROOT, trunk())}; local {trunk()} untouched"]
    if git("remote", "get-url", "origin").returncode == 0:
        pushed = git("push", "--quiet", "origin", f"refs/heads/{branch}:refs/heads/{branch}")
        said.append(f"pushed to origin/{branch}" if pushed.returncode == 0
                    else f"not pushed ({(pushed.stderr or pushed.stdout).strip().splitlines()[-1:]}); "
                         f"`git push origin {branch}` when the forge can be reached")
    place = queue()
    place.mkdir(parents=True, exist_ok=True)
    (place / f"{branch.replace('/', '__')}.json").write_text(json.dumps({
        "branch": branch, "message": message, "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}),
        encoding="utf-8")
    said.append("queued for the harbourmaster, which lands it on trunk through the full gate at its next pass")
    return "; ".join(said)


def harbour_running() -> bool:
    """Whether this machine's harbourmaster is alive: while it is, trunk moves on the forge under this
    checkout, and a commit on local trunk is one it cannot bring forward."""
    try:
        import fleet  # noqa: PLC0415 — beside this script, and heavy; asked only here
    except Exception:  # noqa: BLE001 — a checkout whose fleet will not load has no harbourmaster to ask
        return False
    pid = fleet.read_pid(fleet.RUNNING / "harbourmaster.pid")
    return pid is not None and fleet.alive(pid)


def step_aside(kind: str, slug: str) -> tuple[str, str]:
    """Before a stage that commits in this checkout: on trunk while a harbourmaster runs, switch to a branch
    of the stage's own, carrying the working tree as it is. (the branch, the trunk it left), or ("", "")
    where nothing needed doing — off trunk already, or no fleet moving trunk, where a commit here is pushed
    by casting off (`published.py`) as it always was."""
    name = trunk()
    head = git("symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    if head != name or not harbour_running():
        return "", ""
    branch = free(f"{kind}/{re.sub(r'[^A-Za-z0-9.,-]+', '-', slug).strip('-') or 'work'}")
    switched = git("switch", "--quiet", "-c", branch)
    return (branch, name) if switched.returncode == 0 else ("", "")


def step_back(branch: str, left: str, message: str) -> str:
    """After it: whatever the session committed on `branch` is pushed and queued for the harbourmaster, and
    the checkout goes back to trunk. Uncommitted work rides along as git carries it; where git will not
    switch, the checkout stays on `branch` and says so, with nothing touched."""
    ahead = git("rev-list", "--count", f"{left}..{branch}").stdout.strip()
    said = hand_on(branch, message) if ahead not in ("", "0") else f"nothing was committed on {branch}"
    back = git("switch", "--quiet", left)
    if back.returncode != 0:
        return f"{said}; this checkout stays on {branch}, because git would not switch back to {left}: " \
               f"{(back.stderr or back.stdout).strip()}"
    if ahead in ("", "0"):
        git("branch", "--quiet", "-D", branch)
    return f"{said}; back on {left}"


def land(branch: str, message: str, paths: list[str]) -> tuple[bool, str]:
    made, why = commit(branch, message, paths)
    if not made:
        return False, why
    return True, hand_on(made, message)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    ok, said = land(argv[0], argv[1], argv[2:])
    print(f"landing: {said}", file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
