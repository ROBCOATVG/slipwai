# Written by scripts/shared-modules.py from src/slipwai/need_check.py. Do not edit: edit the keel's module,
# run `make shared`, and commit both. A generated project has no slipwai to import, and both runtimes need
# this one — so there is one source and this copy, and `make check-shared` refuses a copy that has drifted.
"""Whether trunk already holds what a need asks for: the one reading the harbourmaster ticks needs by and the board
asks before it lists one.

A hand-back's need carries a check — a file on trunk holding a string — and the harbourmaster writes its
`need-met` receipt once trunk passes it. But it asks once per trunk commit, and only while it runs: manda's board
listed forty-seven *a slice needs this on trunk* items, most of them landed days before, with nothing that had
looked since. So the board asks the same question, of the same trunk, by the same code — this module, carried into
the toolkit beside the harbourmaster — and a need trunk satisfies leaves *Waiting on you* whether or not a
receipt has been written yet. A `make` check is the harbourmaster's alone: it runs a target in a worktree, which a
board read every two seconds must not.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

#: Used where nothing says otherwise. `origin/HEAD` answers it on a repository with a remote.
DEFAULT_TRUNK = "main"
#: What one trunk commit's text checks answered, by (commit, path, has): a board read asks every need again, and
#: trunk's file at one commit cannot change.
ASKED: dict[tuple[str, str, str], bool] = {}


def git(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    """One git command, never raising."""
    try:
        return subprocess.run(["git", *argv], cwd=root, capture_output=True, text=True, check=False)
    except OSError as fault:
        return subprocess.CompletedProcess(["git", *argv], 1, "", str(fault))


def trunk_name(root: Path, configured: object = None) -> str:
    """The branch a merge lands on: what `harbour.json` says, else what the remote calls its head, else main."""
    if isinstance(configured, str) and configured:
        return configured
    found = git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    head = found.stdout.strip().removeprefix("origin/") if found.returncode == 0 else ""
    return head or DEFAULT_TRUNK


def base(root: Path, name: str) -> str:
    """What trunk is, as this machine sees it: the remote's branch where there is one, else the local one."""
    remote = git(root, "rev-parse", "--verify", "--quiet", f"origin/{name}").returncode == 0
    return f"origin/{name}" if remote else name


def trunk_commit(root: Path, configured: object = None) -> str:
    """The commit trunk is at, or `""` where there is no repository or no trunk."""
    return git(root, "rev-parse", "--verify", "--quiet", base(root, trunk_name(root, configured))).stdout.strip()


def unquoted(has: str) -> str:
    """`has` without the one pair of quotes a shell left round it: `--check 'text:docs/design.md:"(S53)"'`.

    manda's sessions wrote forty such checks — `"intakeTagsOf"`, `"About the business"` — and trunk held every
    word of thirty of them without the quotes, so none was ever ticked and each stayed on the board for days."""
    return has[1:-1] if len(has) >= 2 and has[0] == has[-1] and has[0] in "\"'" else has


def text_check(root: Path, check: dict, commit: str) -> bool:
    """Whether the file at `path` on trunk holds `has` — as written, or without the quotes round it (`unquoted`).
    Read with `git show`, never from a checkout, so a berth's uncommitted edit of the same file never ticks a
    need on trunk's behalf."""
    key = (commit, str(check.get("path", "")), str(check.get("has", "")))
    if key not in ASKED:
        if len(ASKED) > 4096:  # a board left open for weeks: what an old trunk said is not asked again
            ASKED.clear()
        shown = git(root, "show", f"{commit}:{key[1]}")
        ASKED[key] = shown.returncode == 0 and any(one in shown.stdout for one in {key[2], unquoted(key[2])} if one)
    return ASKED[key]
