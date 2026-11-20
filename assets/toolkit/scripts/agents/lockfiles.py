#!/usr/bin/env python3
"""A workspace's lockfile: the slice's to write, and regenerated where two slices' writes meet.

A slice that needs a dependency adds it to its own service's manifest. Where the lock sits beside that
manifest it was always the slice's; where the workspace keeps one lock at the root — npm and pnpm workspaces,
a uv workspace — the lock was "the host's", so the slice handed the need back, the mender landed it, and the
slice waited: one dependency cost a slice a stop for a person, on a file whose contents nobody chooses.

A lock is derived. So a slice writes it, in the same change as the manifest line, and when two slices' locks
conflict in the harbourmaster's rebase nobody resolves it by hand: trunk's lock is taken, the rebase goes on,
and the lock is written again from the manifests as they now stand, by the tool that owns it. The gate still
runs on what that makes. A lock this does not know how to write again is left a conflict, as it was.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

#: A lock by its file name, and the command that writes it again from the manifests beside it, without
#: installing anything or running a package's scripts.
REGENERATED: dict[str, list[str]] = {
    "package-lock.json": ["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"],
    "pnpm-lock.yaml": ["pnpm", "install", "--lockfile-only", "--ignore-scripts"],
    "uv.lock": ["uv", "lock"],
}
#: How long one regeneration may take: it resolves versions over the network, and a registry that does not
#: answer must not hold the merge.
LIMIT = 300.0


def is_lock(path: str) -> bool:
    return Path(path).name in REGENERATED


def regenerate(where: Path, path: str) -> str:
    """Write `path` again, in the checkout at `where`, from the manifests there. Why it could not be, or ""."""
    argv = REGENERATED.get(Path(path).name)
    if argv is None:
        return f"nothing here knows how to write {path} again"
    if shutil.which(argv[0]) is None:
        return f"{path} has to be written again from the manifests and `{argv[0]}` is not on this machine's PATH"
    try:
        ran = subprocess.run(argv, cwd=(where / path).parent, capture_output=True, text=True, timeout=LIMIT,
                             check=False)
    except (OSError, subprocess.TimeoutExpired) as fault:
        return f"`{' '.join(argv)}` could not write {path} again ({fault})"
    if ran.returncode != 0:
        said = [line for line in (ran.stderr or ran.stdout).splitlines() if line.strip()]
        return f"`{' '.join(argv)}` could not write {path} again ({said[-1].strip() if said else 'no output'})"
    return ""
