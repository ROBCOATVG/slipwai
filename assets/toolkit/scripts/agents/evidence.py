#!/usr/bin/env python3
"""Whether a slice's `demo` and `seeded` lines are still evidence of the code its branch holds now.

The captain closes a slice on a `demo` line that says `accepted` and, where it has a story, a `seeded` line;
the harbourmaster holds its merge on the `seeded` line too. They read those lines by two different rules: the
captain counted only the lines the turn that just ran had written, the harbourmaster any line ever written.
manda's S114 lost all three of its attempts in the gap, at one commit: run 1 demoed and was told it had not
seeded, run 2 seeded and was told it had not demoed, run 3 demoed again and was told it had not seeded, and
it parked for a person with nothing wrong with its code (issue 170).

**One rule, read here by both.** A line counts while the code it was written against is the code the slice
branch holds now, whichever turn wrote it. Each line says which commit that was — `seeded` has always
carried `commit`, and `deck_line.py demo` writes it now — and a later commit makes the line stale where it
changes the code or the slice's own story. A commit that only adds records — under `specs/` a demo log, a gates
record, tasks ticked; the dispatch ledger the captain commits at every run (`RECORDS`) — changes nothing the
line was evidence of, so it is not asked for again; manda's S116 wrote its gates and its hand-backs after its
seed and merged on it.

A line that records no commit — one written before lines carried it, or where the berth's head could not be
read — and any line where the branch's head cannot be read, is read as each reader read it before: the
captain counts it where the turn that just ran wrote it (`turn`), the harbourmaster wherever it is (`turn`
of None).

Standalone and dependency-free beyond `logs.py` beside it: this ships inside a generated project.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import logs  # noqa: E402

ACCEPTED = "accepted"
#: Where a project keeps records about its code rather than code: the specifications and the slices' own
#: records, the fairways' careens, and the run's own ledgers — the captain commits a dispatch line to the
#: slice branch at every run it starts. A commit that touches only these changes nothing a line was evidence of.
RECORDS = ("specs", "fairways", ".slipwai")
#: What a writer puts in `commit` where it could not read its head; the same as no commit at all.
UNRECORDED = "unrecorded"


def recorded(line: logs.Entry) -> str:
    """The commit a line says it was written at, or `""` where it says none."""
    commit = str(line.fields.get("commit", "") or "").strip()
    return "" if commit == UNRECORDED else commit


def same(one: str, other: str) -> bool:
    """Whether two names are of one commit, either of them abbreviated."""
    return bool(one and other) and (one.startswith(other) or other.startswith(one))


def moved(root: Path, since: str, head: str, story: str = "") -> bool:
    """Whether the code, or the story at `story`, differs between `since` and `head`.

    A commit git cannot find — one from another clone, or rewritten away — is one nothing here can compare,
    so it is read as moved: a line is evidence only of a tree this repository can show is the one it holds.
    """
    if same(since, head):
        return False
    for paths in ([".", *(f":(exclude){where}" for where in RECORDS)], [story] if story else []):
        if not paths:
            continue
        done = subprocess.run(["git", "diff", "--quiet", since, head, "--", *paths], cwd=root,
                              capture_output=True, text=True)
        if done.returncode != 0:
            return True
    return False


@dataclass(frozen=True)
class Standing:
    """What a slice's lines are evidence of at its branch's head."""

    #: The newest `demo` verdict that counts, or `""` where none does.
    verdict: str = ""
    #: Whether a `seeded` line counts.
    seeded: bool = False
    #: The kinds that had a line which would have counted had the code not moved since it: `demo`, `seeded`.
    stale: tuple[str, ...] = ()


def standing(lines: list[logs.Entry], slice_id: str, head: str, root: Path, story: str = "",
             turn: list[logs.Entry] | None = None) -> Standing:
    """The `demo` verdict and the `seeded` line that count for `slice_id` at `head`, by the rule above.

    `lines` is the slice's log in the order it was written, so the newest demo that counts is the verdict;
    `story` is the slice's `try-it.json` from the project's root, whose change makes a `seeded` line stale.
    """
    asked: dict[tuple[str, str], bool] = {}

    def counts(line: logs.Entry) -> bool | None:
        """True or False by its commit; None where it records none and is not this turn's to count."""
        commit = recorded(line)
        if commit and head:
            path = story if line.kind == "seeded" else ""
            if (commit, path) not in asked:
                asked[(commit, path)] = not moved(root, commit, head, path)
            return asked[(commit, path)]
        return True if turn is None or line in turn else None

    verdict, seeded, stale = "", False, set()
    for line in lines:
        if line.kind not in ("demo", "seeded") or str(line.fields.get("slice", "")) != slice_id:
            continue
        held = counts(line)
        if held is False:
            stale.add(line.kind)
        elif held and line.kind == "demo":
            verdict = str(line.fields.get("verdict", ""))
        elif held:
            seeded = True
    stale -= {kind for kind, has in (("demo", bool(verdict)), ("seeded", seeded)) if has}
    return Standing(verdict, seeded, tuple(sorted(stale)))
