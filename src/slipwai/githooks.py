"""Point a checkout at the hooks the project carries, without ever taking somebody else's.

`.githooks/pre-push` is a file like any other and travels with the clone. What does **not** travel is
`core.hooksPath`, because git config is per-checkout and no clone, worktree or cloud runner inherits it. So
the one rule in the method that holds whoever is driving is, by default, installed nowhere — which is the
same shape as the bug it exists to catch, and would have been funny in a year's time.

So generation sets it, and `slipwai migrate` sets it again for a project that predates this: both already
derive per-checkout state after they write the tree, and this is one more line of that.

**An existing `core.hooksPath` is never overwritten.** An adopted repository may already be pointed at
husky, lefthook or its own directory, and a factory that quietly repointed it would disable somebody's
hooks and tell them nothing. Reported and left alone, with the one line a person needs to chain them.

Nothing here raises. A checkout with no `.git` — an export, a tarball, a `pip` sdist — is a checkout where
there is nothing to configure and no failure either.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import NamedTuple

from .layout import AT_ROOT, Layout

#: Where the hooks the project carries live, relative to the repository root.
HOOKS = ".githooks"
#: The config key git reads them from. Per-checkout, which is the whole reason this module exists.
KEY = "core.hooksPath"


class Installed(NamedTuple):
    """What happened, and the sentence a person reads when it is not what they expected."""

    set: bool
    why: str = ""


def git(root: Path, *argv: str) -> tuple[int, str]:
    try:
        done = subprocess.run(["git", *argv], cwd=root, capture_output=True, text=True, check=False)
    except OSError as error:  # pragma: no cover - a machine with no git cannot have cloned this
        return 1, f"{type(error).__name__}: {error}"
    return done.returncode, (done.stdout or done.stderr).strip()


def repository(root: Path) -> bool:
    """Whether `root` is a repository's own top level, and not merely somewhere inside one.

    The difference matters: `core.hooksPath` is resolved relative to the top level, so setting it from a
    subdirectory would write a path into the *enclosing* repository's config that points somewhere else
    entirely. A path this is handed that is not a root is a caller's mistake, and silently configuring the
    wrong repository is the expensive way to find that out.
    """
    code, said = git(root, "rev-parse", "--show-toplevel")
    if code != 0 or not said:
        return False
    try:
        return Path(said).resolve() == root.resolve()
    except OSError:  # pragma: no cover - a path that cannot be resolved is not a root either
        return False


def configured(root: Path) -> str:
    """What `core.hooksPath` is here, or `""` where it is unset."""
    code, said = git(root, "config", "--get", KEY)
    return said if code == 0 else ""


def install(root: Path, layout: Layout = AT_ROOT) -> Installed:
    """Point this checkout at the project's own hooks, unless something else already has it.

    Idempotent: a checkout already pointed here is left exactly as it is and says so, so that generation,
    `migrate` and a person running `make hooks` can each call it without the other two having to know.
    """
    where = layout.place(HOOKS)
    if not (root / where).is_dir():
        return Installed(False, f"{where}/ is not in this checkout, so there are no hooks to point at")
    if not repository(root):
        return Installed(False, "this is not a git repository, so there is no hook path to set")
    already = configured(root)
    if already == where:
        return Installed(False, "")
    if already:
        return Installed(False, f"{KEY} is already `{already}`, which is somebody else's and not this "
                                f"command's to repoint. Chain {where}/pre-push from it, or run "
                                f"`git config {KEY} {where}` to take it over")
    code, said = git(root, "config", KEY, where)
    if code != 0:
        return Installed(False, f"{KEY} could not be set: {said or 'git failed'}")
    return Installed(True, "")


def note(hooked: bool, why: str) -> list[str]:
    """What a migration's report says about the hooks, or nothing. Here rather than in the report, so the
    module that owns the config owns the sentence about it and there is one wording to keep right."""
    if hooked:
        return ["This checkout is now pointed at the project's own git hooks, so a push naming work no plan "
                "knows is refused here as well as in CI. It is per-checkout config: every other clone, "
                "worktree and cloud runner needs `make hooks` once."]
    return [f"The git hooks were left alone: {why}."] if why else []
