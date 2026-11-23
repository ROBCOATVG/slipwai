"""Records a project keeps that a newer keel keeps somewhere else: what `slipwai migrate` moves after the merge.

The rename table (`docs/rename.json`) moves what the keel *generates*, on both sides of version 1's crossing,
before the merge. A record the project wrote itself is neither side's template — no replay ever generates the
dispatch ledger a run appended to — so no merge can carry it to a new home. This table is for those: each row
a pattern over tracked paths and where a match now lives, moved with `git mv` so history follows the file, and
staged for the commit `migrate.refresh` makes after the merge.

The readers of every moved record still accept the old path, so a checkout that has not migrated yet, or a
branch cut before the move, is never red because of where a file sits.

`split_logs` is the other kind of move: a feature's `decisions.md` and `adversary-log.md`, which every slice
appended to and whose merges dropped lines, split into one file per entry beside them by the project's own
`render-fairways.py --split`, which then renders the two logs from those files.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .layout import AT_ROOT, Layout
from .shell_environment import python3

#: (where a record was, as a pattern over its tracked path; where it lives now, filled from the pattern's groups).
MOVES: tuple[tuple[re.Pattern[str], str], ...] = (
    # The dispatch ledger left `specs/` in 2.0.0: it is evidence about the run, not part of a feature's
    # specification, and `.slipwai/` is where the run's committed records already are.
    (re.compile(r"specs/(?P<feature>[^/]+)/dispatch-ledger\.jsonl"), ".slipwai/dispatch/{feature}.jsonl"),
)


def git(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], cwd=root, text=True, capture_output=True, check=False,
                          encoding="utf-8", errors="replace")


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


#: The renderer that splits the two logs, where the merge has just put it, and the flag older copies lack.
RENDERER, SPLIT = "scripts/render-fairways.py", "--split"
#: What it prints for a log it split: the log, how many entries, and the folder they went to.
SPLIT_SAID = re.compile(r"^render-fairways: (\S+): (\d+) entr(?:y|ies) moved into (\S+), one file each$", re.M)


def split_logs(root: Path, layout: Layout = AT_ROOT) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split each feature's decisions and adversary log into one file per entry, staged and not committed.
    Returns `log -> folder (n entries)` for each log split, and every path it staged. Nothing where the
    project's renderer predates the split or has nothing to split; the renderer refuses to drop an entry."""
    script = root / layout.place(RENDERER)
    if not script.is_file() or SPLIT not in script.read_text(encoding="utf-8", errors="replace"):
        return (), ()
    before = set(git(root, "diff", "--cached", "--name-only", "--", "specs").stdout.split())
    done = subprocess.run([python3(), "-B", str(script), SPLIT], cwd=root, text=True, capture_output=True,
                          check=False, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        return (), ()
    git(root, "add", "-A", "--", "specs")
    staged = [path for path in git(root, "diff", "--cached", "--name-only", "--", "specs").stdout.split()
              if path not in before]
    said = SPLIT_SAID.findall(done.stdout)
    moves = [f"{log} -> {folder} ({count} entries)" for log, count, folder in said]
    split = {log for log, _, _ in said}
    # A log already folded from a fairway's copies is only rendered again, under the banner that names its records.
    moves += [f"{path} -> rendered from its records" for path in staged if path.endswith(".md")
              and path.count("/") == 2 and path not in split]
    return tuple(moves), tuple(staged)
