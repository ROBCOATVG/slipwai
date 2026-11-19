"""`project.json` across a migration: merged by what it says, never by the order its keys are written in.

A manifest is a record of answers, and two writers that agree on every answer can still write it in two
orders: the factory in the order it assembles the record, a crossing from version 1 sorted. Git merges lines,
so a project whose copy is in one order met a replay in the other as a file changed on every line by both
sides, and each later migration stopped on a conflict whose only real difference was `generator.updatedWith`
(manda-pir, three times running). A person was asked to resolve a difference that was not one.

Two halves. `ordered_like` is the replay's: the factory's side is written in the key order the project's copy
already has, so from the next migration on the two differ only where an answer does and git merges them
itself. `settled` is the merge's: where git has stopped on `project.json` it reads the three stages as JSON
and merges them key by key — a key only one side changed is taken, a key the project added is kept, the
result is written in the project's order — and leaves the file exactly as git left it where both sides gave
one key different values, because that is a real conflict and the project decides it.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .errors import GenerationError
from .scaffold import NO_MAINTENANCE

MANIFEST = "project.json"
#: A key one side does not have, as a value like any other: a key the project deleted and the factory left
#: alone stays deleted by the same rule that keeps a value the project changed.
ABSENT = object()


class Disagreement(Exception):
    """Both sides changed one value, differently: a conflict in what the manifest says, not in how it is written."""


def ordered_like(document: Any, like: Any) -> Any:
    """`document`, its keys in the order `like` has them wherever both are objects; a key `like` has not got
    follows, in the order it was written. Nothing but order changes."""
    if not isinstance(document, dict) or not isinstance(like, dict):
        return document
    first = [key for key in like if key in document]
    return {key: ordered_like(document[key], like.get(key))
            for key in [*first, *(key for key in document if key not in like)]}


def three_way(base: Any, ours: Any, theirs: Any) -> Any:
    """One value from three, in the project's order. Equality is of values, so two objects holding the same
    answers in two orders are the same and neither side has changed anything."""
    if ours == theirs or theirs == base:
        return ours
    if ours == base:
        return ordered_like(theirs, ours)
    if not all(isinstance(side, dict) for side in (ours, theirs)):
        raise Disagreement
    before = base if isinstance(base, dict) else {}
    result = {}
    for key in [*ours, *(key for key in theirs if key not in ours)]:
        value = three_way(before.get(key, ABSENT), ours.get(key, ABSENT), theirs.get(key, ABSENT))
        if value is not ABSENT:
            result[key] = value
    return result


def merged(base: str | None, ours: str, theirs: str) -> str | None:
    """The three copies merged as records, written as the project writes its own; None where one cannot be
    read as an object or the two sides really disagree."""
    try:
        sides = [json.loads(text) if text is not None else {} for text in (base, ours, theirs)]
        if not all(isinstance(side, dict) for side in sides):
            return None
        result = three_way(*sides)
    except (ValueError, Disagreement):
        return None
    return json.dumps(result, indent=2, ensure_ascii=ours.isascii()) + ("\n" if ours.endswith("\n") else "")


def stage_of(root: Path, number: int) -> str | None:
    shown = subprocess.run(["git", "show", f":{number}:{MANIFEST}"], cwd=root, capture_output=True, check=False)
    try:
        return shown.stdout.decode("utf-8") if shown.returncode == 0 else None
    except UnicodeDecodeError:
        return None


def settled(root: Path, conflicts: tuple[str, ...]) -> tuple[str, ...]:
    """The conflicts a merge in progress still has once `project.json` is merged as a record.

    Where it was the only one, the merge is concluded here with the message git was given, so a migration
    that moved nothing but the version stamp is the one merge commit a clean migration always was."""
    if MANIFEST not in conflicts:
        return conflicts
    ours, theirs = stage_of(root, 2), stage_of(root, 3)
    result = merged(stage_of(root, 1), ours, theirs) if ours is not None and theirs is not None else None
    if result is None:
        return conflicts
    (root / MANIFEST).write_text(result, encoding="utf-8", newline="")
    subprocess.run(["git", "add", "--", MANIFEST], cwd=root, capture_output=True, check=True)
    left = tuple(path for path in conflicts if path != MANIFEST)
    if not left:
        done = subprocess.run(["git", *NO_MAINTENANCE, "commit", "--quiet", "--no-edit"], cwd=root, text=True,
                              capture_output=True, check=False)
        if done.returncode != 0:
            raise GenerationError(
                "the merge is resolved and staged, and the commit that concludes it was refused: "
                f"{done.stderr.strip() or done.stdout.strip() or 'no reason given'}. Deal with what refused it, "
                "then run `git commit --no-edit`; or `git merge --abort` to walk away from all of it"
            )
    return left
