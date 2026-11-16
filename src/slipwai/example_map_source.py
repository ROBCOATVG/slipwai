"""Where a slice's example map is read from: its `slice/<id>` branch in flight, trunk's working tree once done.

**The board's poll spawns nothing of its own for a map.** The card of a slice in flight is handed the branch
head `slice_rungs.branch_facts` already resolved for that poll, and the map is read again only when that
head moves; a done slice is read from trunk, which costs a `stat` of two files. Only the slice's window,
which knows neither, asks git for the head: one `rev-parse` a window poll, and the ancestry check once a pair
of heads for a slice the board has not yet said is done.

**Done is the board's word, not git's.** A branch rebased as it merged is never an ancestor of trunk, so
asking git would read CL1's branch for ever; the board knows the slice merged, says so, and its window then
reads trunk too.

One cache, keyed by the slice alone and stamped by what it was read from, so the card and the window share
a read rather than evicting each other's; the folder is remembered by slice for the same reason, since the
card knows the slice's feature and the window does not.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .example_map import ExampleMap, card_counts, read

#: What was read last time, by slice: the stamp it was read at (a branch head, or the files' times) and the map.
SEEN: dict[tuple[str, str], tuple[tuple, ExampleMap | None]] = {}
#: The slice's folder once found, by slice.
FOLDERS: dict[tuple[str, str], str] = {}
#: The slices the board has seen merged, and those it has seen in flight.
DONE: set[tuple[str, str]] = set()
FLIGHT: set[tuple[str, str]] = set()
#: Whether a branch head is in trunk yet, by the pair of heads, so a window asks git once a pair.
MERGED: dict[tuple[str, str], bool] = {}


def git(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True, check=False,
                          encoding="utf-8", errors="replace")


def folder_of(root: Path, slice_id: str, ref: str = "") -> str:
    """`specs/<feature>/slices/<id>/`, found on the branch or on trunk where no feature was given."""
    if ref:
        listed = git(root, "ls-tree", "-r", "--name-only", ref, "specs/").stdout.splitlines()
        names = sorted(line for line in listed if re.fullmatch(rf"specs/[^/]+/slices/{re.escape(slice_id)}/"
                                                               r"examples\.md", line))
    else:
        names = sorted(str(path.relative_to(root)) for path in root.glob(f"specs/*/slices/{slice_id}/examples.md"))
    return names[0].removesuffix("examples.md") if names else ""


def window_head(root: Path, key: tuple[str, str], slice_id: str) -> str:
    """The branch head a window reads, or "" where it reads trunk."""
    if key in DONE:
        return ""
    asked = git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/slice/{slice_id}")
    head = asked.stdout.strip() if asked.returncode == 0 else ""
    if head and key not in FLIGHT:
        trunk = git(root, "rev-parse", "HEAD").stdout.strip()
        if (head, trunk) not in MERGED:
            MERGED[(head, trunk)] = git(root, "merge-base", "--is-ancestor", head, trunk).returncode == 0
        return "" if MERGED[(head, trunk)] else head
    return head


def found_map(root: Path, slice_id: str, feature: str = "", head: str | None = None,
              done: bool = False) -> ExampleMap | None:
    """The slice's map, or None where it has no `examples.md` yet.

    `head` is the branch head the caller already has ("" for no branch), and `done` that the board has the
    slice merged; the window passes neither and asks git.
    """
    if not slice_id or "/" in slice_id or slice_id.startswith("."):
        return None
    key = (str(root.resolve()), slice_id)
    if feature:
        FOLDERS[key] = f"specs/{feature}/slices/{slice_id}/"
    if done:
        DONE.add(key)
        FLIGHT.discard(key)
        head = ""
    elif head is not None:
        FLIGHT.add(key)
        DONE.discard(key)
    else:
        head = window_head(root, key, slice_id)
    if head:
        stamp: tuple = ("branch", head)
        if SEEN.get(key, ((), None))[0] == stamp:
            return SEEN[key][1]
        ref = f"refs/heads/slice/{slice_id}"
        folder = FOLDERS.get(key) or folder_of(root, slice_id, ref)
        shown = git(root, "show", f"{ref}:{folder}examples.md") if folder else None
        found = (read(shown.stdout, git(root, "show", f"{ref}:{folder}tasks.md").stdout)
                 if shown is not None and shown.returncode == 0 else None)
    else:
        folder = FOLDERS.get(key) or folder_of(root, slice_id)
        page, proof = root / (folder or "-/") / "examples.md", root / (folder or "-/") / "tasks.md"
        stamp = ("trunk", folder, *(path.stat().st_mtime_ns if path.is_file() else 0 for path in (page, proof)))
        if SEEN.get(key, ((), None))[0] == stamp:
            return SEEN[key][1]
        try:
            found = read(page.read_text(encoding="utf-8"),
                         proof.read_text(encoding="utf-8") if proof.is_file() else "") if page.is_file() else None
        except (OSError, UnicodeDecodeError):
            found = None
    if folder:
        FOLDERS[key] = folder
    SEEN[key] = (stamp, found)
    return found


def card_line(root: Path, feature: str, slice_id: str, head: str | None = None, done: bool = False) -> str:
    """The counts a slice's card carries, or nothing before the file exists."""
    try:
        return card_counts(found_map(root, slice_id, feature, head, done))
    except OSError:
        return ""
