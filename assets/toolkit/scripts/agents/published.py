#!/usr/bin/env python3
"""Before the fleet is cast off: the plan it is lit from is on the trunk its slices are cut from.

A captain reads the chart in this checkout and cuts each slice's worktree from `origin/main`. Those are two
places, and the launch that charts and splits a feature commits here and pushes nothing: a fleet cast off
straight after it claimed three slices whose worktrees held no model entry, no chart row, no storyboard and no
split for them, and each session's first act was to go looking for a slice that was not in its checkout.

So casting off publishes first. Where this checkout is the trunk branch and is only ahead of the remote, it is
pushed, and the line says how many commits went. Where it cannot be — the push is refused, or the checkout and
the remote have each moved and the commits only here change the chart or the model — nothing is cast off and
the line says what to do. A checkout that is merely behind is left alone: the fleet's own merges put it there
all day, and the chart it reads is still one the remote has.

    python3 scripts/agents/published.py     # say what casting off would do about it, and do it
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
#: Where the plan is: every feature's chart, and the model the event profile renders them from.
PLAN = (":(glob)specs/*/chart.yaml", "docs/event-model/model.yaml")


def git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True, check=False)


def remote_trunk(root: Path) -> str:
    """`origin/main` or `origin/master`, whichever this repository has; empty where it has no remote trunk."""
    for candidate in ("origin/main", "origin/master"):
        if git(root, "rev-parse", "--verify", "--quiet", candidate).returncode == 0:
            return candidate
    return ""


def publish(root: Path = ROOT) -> tuple[bool, str]:
    """Whether the fleet may be cast off on this checkout's plan, and the line to say about it.

    `(True, "")` where there is nothing to do: no remote trunk, the two at one commit, or this checkout
    behind. `(True, line)` where it was ahead and has been pushed. `(False, line)` where the plan here is
    not the remote's and could not be made so.
    """
    remote = remote_trunk(root)
    if not remote:
        return True, ""
    name = remote.partition("/")[2]
    git(root, "fetch", "--quiet", "origin", name)  # a remote that cannot be reached is judged as last seen
    ahead = git(root, "rev-list", "--count", f"{remote}..HEAD").stdout.strip()
    if ahead in ("", "0"):
        return True, ""
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    only_ahead = git(root, "merge-base", "--is-ancestor", remote, "HEAD").returncode == 0
    if branch == name and only_ahead:
        pushed = git(root, "push", "--quiet", "origin", f"HEAD:refs/heads/{name}")
        if pushed.returncode == 0:
            return True, (f"pushed {ahead} commit(s) from this checkout to {remote}: every slice's worktree is "
                          f"cut from there, so the plan the fleet is lit from has to be there first")
        said = (pushed.stderr or pushed.stdout).strip().splitlines()
        return False, (f"this checkout is {ahead} commit(s) ahead of {remote} and the push was refused "
                       f"({said[-1] if said else 'git said nothing'}). Every slice's worktree is cut from "
                       f"{remote}, so nothing is cast off until they are there: push them, then cast off again")
    touched = git(root, "log", "--format=%h", f"{remote}..HEAD", "--", *PLAN).stdout.split()
    if not touched:
        return True, ""
    where = f"on {branch}, which is not {name}" if branch != name else f"and {remote} has moved since"
    return False, (f"{len(touched)} commit(s) here change the chart or the model and are not on {remote} "
                   f"({where}). Every slice's worktree is cut from {remote}, so a slice lit from this chart "
                   f"would not find itself in its own checkout: bring them onto {name} and push, then cast "
                   f"off again")


def main() -> int:
    fine, said = publish()
    if said:
        print(f"published: {said}", file=sys.stdout if fine else sys.stderr)
    return 0 if fine else 2


if __name__ == "__main__":
    raise SystemExit(main())
