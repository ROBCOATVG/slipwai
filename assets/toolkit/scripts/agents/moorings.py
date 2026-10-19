#!/usr/bin/env python3
"""Where one slice is worked: a worktree of its own, so two slices of one fairway never share a checkout.

The captain ran its one `/sail` with the project's own checkout as the session's directory, and the
session made itself a worktree because *Running ready slices concurrently* says each slice has one. That
held while there was one session: nothing else was in the checkout to collide with. Two sessions in one
checkout are two agents running `git checkout` under each other, and the second one's branch is whatever
the first left — the failure is not a conflict anybody sees but commits landing on the wrong slice.

**So the captain makes the berth, and the session starts in it.** `../<project>-<id>` on `slice/<id>` —
the name `commands/sail.md` and `dispatch.py` already give a slice's worktree, so one a person or an
earlier session made is found and used rather than made twice. A slice whose branch is already checked
out somewhere — a takeover lands it in the project's checkout — is worked where it is.

**The deck log is the one thing a berth must not have its own copy of.** It is ignored by git, so a
worktree starts without one, and a session in a berth writing `.slipwai/logs/...` would write lines the
captain is not reading — every one of them a gate the captain then says was never passed. The berth's
`.slipwai/logs` is a link to the project's, and the link is listed in the repository's own
`info/exclude`, which every worktree shares, because the project's `.gitignore` names the directory with a
trailing slash and a link is not a directory to git.

**A berth is left when its slice merges.** Without `--force`: a worktree with changes in it is somebody's,
and the line that says it was kept is cheaper than the work it would have cost.

Standalone and dependency-free: this runs inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

#: What every worktree's `.slipwai/logs` link is excluded as, in the repository's shared `info/exclude`.
EXCLUDED = "/.slipwai/logs"


def git(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], cwd=root, capture_output=True, text=True, check=False)


def checked_out(root: Path, branch: str) -> Path | None:
    """The worktree that has this branch checked out, or None where none has."""
    listed = git(root, "worktree", "list", "--porcelain")
    where: Path | None = None
    for line in listed.stdout.splitlines():
        if line.startswith("worktree "):
            where = Path(line[len("worktree "):])
        elif line == f"branch refs/heads/{branch}" and where is not None:
            return where
    return None


def linked(root: Path, berth: Path) -> str:
    """Point the berth's deck logs at the project's, and say why where that could not be done."""
    logs = berth / ".slipwai/logs"
    shared = root / ".slipwai/logs"
    shared.mkdir(parents=True, exist_ok=True)
    if logs.is_symlink() or berth.resolve() == root.resolve():
        return ""
    if logs.is_dir():
        try:
            logs.rmdir()  # empty, and so nothing anybody wrote
        except OSError:
            return (f"{logs} is a directory with lines in it, so it was left; lines written there are not "
                    f"the captain's to read, and the gate will say so")
    logs.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(shared.resolve(), logs, target_is_directory=True)
    except OSError as fault:
        return f"{logs} could not be linked to the project's deck logs ({fault})"
    common = git(root, "rev-parse", "--git-common-dir").stdout.strip()
    if common:
        exclude = (root / common).resolve() / "info/exclude"
        held = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
        if EXCLUDED not in held.splitlines():
            exclude.parent.mkdir(parents=True, exist_ok=True)
            joined = held + ("" if held.endswith("\n") or not held else "\n") + EXCLUDED + "\n"
            exclude.write_text(joined, encoding="utf-8")
    return ""


def berth(root: Path, slice_id: str, branch: str, base: str) -> tuple[Path | None, str]:
    """The slice's own worktree, made where it is not there yet. (where, why not).

    None where there is no commit to make one from — a harbour with no history — or git refused; the
    caller decides whether the checkout itself will do, which it will only while nothing else is in it.
    """
    if git(root, "rev-parse", "--verify", "--quiet", "HEAD").returncode != 0:
        return None, "this checkout has no commit yet, so there is nothing to make a worktree from"
    found = checked_out(root, branch)
    if found is None:
        found = root.parent / f"{root.name}-{slice_id}"
        if found.exists():
            return None, (f"{found} is already there and is not a worktree on {branch}. Move it, or "
                          f"check {branch} out in it, and the slice is carried on")
        exists = git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0
        made = (git(root, "worktree", "add", "--quiet", str(found), branch) if exists
                else git(root, "worktree", "add", "--quiet", "-b", branch, str(found), base or "HEAD"))
        if made.returncode != 0:
            said = (made.stderr or made.stdout).strip().splitlines()
            return None, f"a worktree for {branch} could not be made: {said[-1] if said else 'git failed'}"
    return found, linked(root, found)


def leave(root: Path, berth: Path) -> str:
    """Remove a merged slice's worktree, or say why it was kept. Never the project's own checkout."""
    if berth.resolve() == root.resolve():
        return ""
    gone = git(root, "worktree", "remove", str(berth))
    if gone.returncode != 0:
        said = (gone.stderr or gone.stdout).strip().splitlines()
        return f"{berth} was kept: {said[-1] if said else 'git would not remove it'}"
    return ""
