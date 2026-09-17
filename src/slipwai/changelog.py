"""The entry for the release in flight, held as one file per change under `changelog.d/`.

A released entry is finished prose in `CHANGELOG.md`. The entry being written is not: every branch in flight
adds its own paragraph to it, and while that entry was a block of lines at the top of one file, every pair of
branches that overlapped in time was two branches inserting at the same spot. `union` in `.gitattributes`
made the merge itself clean, and was still not enough — a forge decides whether to *offer* the merge with
`git merge-file` in a bare repository, which knows nothing of merge drivers, so the pull request read as
conflicted for a merge that would have succeeded. One file per change has no shared line to conflict on, in
any tool, and `make release` assembles them into the entry in the commit it tags.

Three readers, one shape. `scripts/tag-release.py` assembles and deletes them; `tests/test_changelog.py`
holds each one to the shape and the set of them to the number `VERSION` carries; and `catch_up.py` reads
them as the entry for a snapshot, because a project migrating onto `1.15.0.dev7` is owed what the release it
is a snapshot of asks of it, and that is not written anywhere else yet.
"""
from __future__ import annotations

from pathlib import Path

from .assets import ROOT
from .versions import bumped

# Where a change in flight writes its paragraph. Bundled with the package and the executable, beside
# `CHANGELOG.md` and for the same reason: an installed `slipwai` has no checkout to read either from.
FRAGMENTS = ROOT / "changelog.d"
# The file that says what belongs here, and keeps the directory in the repository when a release has just
# emptied it. Not a fragment, and skipped as one.
GUIDE = "README.md"
# Ascending, because the highest claim among the fragments is the entry's: a release carrying a fix and a new
# option is a MINOR, not both.
LEVELS = ("PATCH", "MINOR", "MAJOR")

# What a fragment is read as: where it is, the level it claims — `None` when its first line is not one — and
# the prose it contributes to the entry.
Fragment = tuple[Path, str | None, str]


def read(path: Path) -> Fragment:
    """One fragment: its level off the first line, and everything after it as the entry's prose."""
    level, _, body = path.read_text().strip().partition("\n")
    return path, level.strip() if level.strip() in LEVELS else None, body.strip()


def fragments(root: Path = ROOT) -> list[Fragment]:
    """Every fragment, in filename order — the entry is a set of blocks and not a timeline."""
    directory = root / "changelog.d"
    if not directory.is_dir():
        return []
    return [read(path) for path in sorted(directory.glob("*.md")) if path.name != GUIDE]


def level(found: list[Fragment]) -> str | None:
    """The entry's level: the highest any fragment claims, or `None` when none of them claims one."""
    claimed = [claim for _path, claim, _body in found if claim is not None]
    return max(claimed, key=LEVELS.index) if claimed else None


def implied(last_release: str, found: list[Fragment]) -> str | None:
    """The release the fragments justify, from the last one: `1.14.2` and a MINOR among them is `1.15.0`.

    `None` when there is nothing to justify a number at all, which is the state a release leaves behind —
    the snapshot `main` opens then is a claim about nothing until a change lands.
    """
    claimed = level(found)
    return None if claimed is None else bumped(last_release, claimed)


def entry(release: str, found: list[Fragment], *, first: bool = False) -> str:
    """The `CHANGELOG.md` entry these fragments are, headed by the release and the level they add up to.

    Ends with the blank line that separates it from the entry below, so the released prose under it is
    untouched by a release being cut above it.
    """
    claimed = None if first else level(found)
    heading = f"## {release}" + (f" — {claimed}" if claimed else "")
    blocks = "\n\n".join(body for _path, _claim, body in found if body)
    return f"{heading}\n\n{blocks}\n\n"
