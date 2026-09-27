"""Whose uncommitted changes these are: the method's own, which a run may write over, or a person's, which it may not.

Brownfield adoption (#74; experimental as `AGENTS.md` defines the word). `/ground` records its answers one at a
time — `adopt --confirm` for each application, the rows in `project.json`, `adopt --refresh` so the pages follow —
and commits them as one change at the end. Each of those commands refused any uncommitted change at all, so the
first answer was refused by what `./init` had just left for the person to read, the second by the first, and the
refresh by the rows it exists to follow. The first repository taken end to end got through by committing after
every answer, which is the history nobody asked for, and by an agent deciding on its own to commit init's output.

What the refusal protects is a person's work, and a run can only lose that where it writes. So it looks at the
paths this run writes — the factory's listing in `.written` and the survey's pages — and refuses only where one of
those holds an uncommitted change that is not what slipwai itself last left there. What slipwai left is recorded,
path by digest, in `.delivery-tools/written.json` — ignored, so it belongs to this checkout and is never
committed, and outside `.git`, which an agent's sandbox can make read-only (Codex's does). Everything else
uncommitted — `project.json`, which is the input, what `./init` wrote, and a person's own source — is left alone,
because nothing here touches it.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import subprocess
from collections.abc import Iterable
from pathlib import Path

from .assets import WRITTEN_RECORD
from .errors import GenerationError


def changed(root: Path) -> list[str] | None:
    """Every path with an uncommitted change, untracked ones included; None where this is not a Git repository."""
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=root, capture_output=True, check=False
    )
    if status.returncode != 0:
        return None
    fields, paths = status.stdout.decode(errors="surrogateescape").split("\0"), []
    while fields:
        entry = fields.pop(0)
        if len(entry) > 3:
            paths.append(entry[3:])
            if entry[0] in "RC" and fields:  # a rename or copy names where it came from next
                fields.pop(0)
    return paths


def record_path(root: Path) -> Path:
    return root / WRITTEN_RECORD


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def recorded(root: Path) -> dict[str, str | None]:
    try:
        read = json.loads(record_path(root).read_text())
    except (OSError, ValueError):
        return {}
    return read if isinstance(read, dict) else {}


def stamp(root: Path, paths: Iterable[str]) -> None:
    """Record what slipwai has just left at each of these paths, keeping only what is still uncommitted."""
    where, now = record_path(root), changed(root)
    if now is None:
        return
    kept = {path: value for path, value in recorded(root).items() if path in now}
    kept.update({path: digest(root / path) for path in paths if path in now})
    with contextlib.suppress(OSError):
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(json.dumps(dict(sorted(kept.items())), indent=2) + "\n")


def refuse_foreign(root: Path, writes: set[str], verb: str) -> None:
    """Refuse where a path this run writes holds an uncommitted change slipwai did not make."""
    now = changed(root)
    if not now:
        return
    left = recorded(root)
    foreign = sorted(
        path for path in now
        if path in writes and path != "project.json" and not (path in left and left[path] == digest(root / path))
    )
    if foreign:
        more = f" and {len(foreign) - 8} more" if foreign[8:] else ""
        shown = ", ".join(f"`{path}`" for path in foreign[:8]) + more
        raise GenerationError(
            f"{verb} writes {shown}, and each holds an uncommitted change that is not what slipwai left there — "
            "writing over it would lose it. Commit or stash those first. Nothing else uncommitted stops this: "
            "project.json, what ./init wrote, an earlier answer's regeneration and your own source are left alone."
        )
