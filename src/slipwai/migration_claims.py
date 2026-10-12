"""Preflight version 1 slice branches and prepare their declared renames without touching a worktree."""
from __future__ import annotations

import tempfile
from pathlib import Path

from .errors import GenerationError
from .migration_merge import git, materialise, modes, tracked
from .migration_renames import moved, renamed


def ahead(root: Path, *, with_claims: bool = False) -> dict[str, str]:
    if git(root, "branch", "--show-current").decode().strip() != "main":
        raise GenerationError("the version 1 crossing runs on main; `git switch main` before `slipwai migrate`")
    found = {}
    for ref in git(root, "for-each-ref", "--format=%(refname)", "refs/heads/slice/").decode().splitlines():
        if int(git(root, "rev-list", "--count", f"main..{ref}").decode()):
            found[ref] = git(root, "rev-parse", ref).decode().strip()
    if found and not with_claims:
        names = ", ".join(ref.removeprefix("refs/heads/") for ref in found)
        raise GenerationError(f"claim branches are ahead of main: {names}; finish or merge them first, "
                              "or run `slipwai migrate --with-claims` then rebase each claim")
    worktrees = git(root, "worktree", "list", "--porcelain").decode().splitlines()
    occupied = {line.removeprefix("branch ") for line in worktrees if line.startswith("branch ")}
    active = occupied & set(found)
    if active:
        raise GenerationError(f"claims are checked out elsewhere: {', '.join(sorted(active))}; "
                              "park those sessions and detach their worktrees before `slipwai migrate --with-claims`")
    return found


def prepare(root: Path, branches: dict[str, str], rows: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    """Fetch prepared commits into the object store; move no branch until the main merge is ready."""
    prepared = {}
    for ref, original in branches.items():
        with tempfile.TemporaryDirectory(prefix="slipwai-claim-") as scratch:
            clone = Path(scratch) / "claim"
            git(root, "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(root), str(clone))
            git(clone, "checkout", "--quiet", "--detach", original)
            own = tracked(clone)
            updated = renamed(own, rows)
            if own == updated:
                continue
            executable = {moved(name, rows): mode for name, mode in modes(clone).items()}
            materialise(clone, updated, executable)
            git(clone, "add", "-A")
            git(clone, "add", "-f", "--", *updated)
            git(clone, "-c", "user.name=slipwai migration", "-c", "user.email=migration@slipwai.invalid",
                "commit", "--quiet", "-m", "Apply version 2's declared renames before rebasing this claim")
            commit = git(clone, "rev-parse", "HEAD").decode().strip()
            git(root, "fetch", "--quiet", str(clone), commit)
            prepared[ref] = (original, commit)
    return prepared


def update(root: Path, prepared: dict[str, tuple[str, str]]) -> None:
    if not prepared:
        return
    commands = "start\n" + "".join(f"update {ref} {new} {old}\n" for ref, (old, new) in prepared.items())
    git(root, "update-ref", "--stdin", data=(commands + "prepare\ncommit\n").encode())
