"""Records a project keeps that a newer keel keeps somewhere else: what `slipwai migrate` moves after the merge.

The rename table (`docs/rename.json`) moves what the keel *generates*, on both sides of version 1's crossing,
before the merge. A record the project wrote itself is neither side's template — no replay ever generates the
dispatch ledger a run appended to — so no merge can carry it to a new home. This table is for those: each row
a pattern over tracked paths and where a match now lives, moved with `git mv` so history follows the file, and
staged for the commit `migrate.refresh` makes after the merge.

The readers of every moved record still accept the old path, so a checkout that has not migrated yet, or a
branch cut before the move, is never red because of where a file sits.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

#: (where a record was, as a pattern over its tracked path; where it lives now, filled from the pattern's groups).
MOVES: tuple[tuple[re.Pattern[str], str], ...] = (
    # The dispatch ledger left `specs/` in 2.0.0: it is evidence about the run, not part of a feature's
    # specification, and `.slipwai/` is where the run's committed records already are.
    (re.compile(r"specs/(?P<feature>[^/]+)/dispatch-ledger\.jsonl"), ".slipwai/dispatch/{feature}.jsonl"),
)


def git(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], cwd=root, text=True, capture_output=True, check=False)


def relocate(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Move every tracked record a row matches, staged and not committed. Returns `old -> new` for each move,
    and each record left where it was with why: a destination that already exists is never written over —
    the readers take both files, so leaving it costs nothing and overwriting it would lose lines."""
    listed = git(root, "ls-files", "-z")
    paths = [path for path in listed.stdout.split("\0") if path] if listed.returncode == 0 else []
    moved: list[str] = []
    left: list[str] = []
    for path in paths:
        for pattern, home in MOVES:
            match = pattern.fullmatch(path)
            if match is None:
                continue
            destination = home.format(**match.groupdict())
            if (root / destination).exists():
                left.append(f"{path} (both it and {destination} exist; the readers take both, so nothing was "
                            f"overwritten — append one to the other and remove it when convenient)")
                break
            (root / destination).parent.mkdir(parents=True, exist_ok=True)
            done = git(root, "mv", path, destination)
            if done.returncode == 0:
                moved.append(f"{path} -> {destination}")
            else:
                left.append(f"{path} (git mv refused: {done.stderr.strip() or 'no reason given'})")
            break
    return tuple(moved), tuple(left)
