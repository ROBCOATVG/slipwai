#!/usr/bin/env python3
"""Tick off the slices the history says are done, in the plan's own tables.

A plan that records its own progress by hand is a plan that is wrong by Friday. This reads `git log` and
writes a Status column in each phase's table of `docs/slipwai-2-plan.md`. Nothing claims to be done that
is not in the history, and nothing in the history goes unticked.

What counts as landed is the trailer `Slice-done: <n>.<m>`, not the subject line. The subject was the
first thing tried and it was wrong within an hour: the commit that *added* slice 9.5 to the plan was
written `Slice 9.5: the three contributor skills…`, and the ticker marked a slice done whose work had not
started. A trailer is deliberate. A subject is a sentence, and a sentence can be about a slice without
being the slice.

`--check` compares the committed plan against what this would write and fails if they differ, which is
what `tests/test_progress.py` runs. Finish a slice, run `make progress`, commit both.

A slice is done when its commit is an ancestor of the branch this runs on. A slice still on its own branch
is not done — rule 10 says people hold the merge, so the merge is what done means.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/slipwai-2-plan.md"
SECTION = "## 11. The implementation plan"
TRAILER = re.compile(r"^Slice-done: (\d+\.\d+[a-z]?)\s*$", re.MULTILINE)
# The slices that landed before the trailer existed, by the commit that landed each. Written once, on
# 2026-10-06, and never added to: everything after carries its own trailer.
BEFORE_THE_TRAILER = {
    "1.1": "5209785", "1.2": "0ba7af6", "1.3": "a6ef34f", "1.4": "941f7c8",
    "1.5": "7001d7c", "1.6": "37cf944", "2.2": "1841091", "2.7": "357700a",
}
ROW = re.compile(r"^\| (\d+\.\d+[a-z]?) \|")
DONE, TODO = "done", ""


def shipped() -> dict[str, str]:
    """Each slice the history has landed, by id, with the short hash of the commit that landed it."""
    # Read as UTF-8 and never in the console's code page: on Windows a pipe is read on a thread, and a
    # commit message with one byte cp1252 has not got killed that thread and left `stdout` as `None`.
    log = subprocess.run(
        ["git", "log", "--format=%h%x1e%B%x1f"], cwd=ROOT, capture_output=True, text=True, check=True,
        encoding="utf-8", errors="replace",
    ).stdout
    found: dict[str, str] = {}
    for entry in log.split("\x1f"):
        short, _, message = entry.strip().partition("\x1e")
        for slice_id in TRAILER.findall(message):
            found.setdefault(slice_id, short)  # the first landing, not a later touch
    return {**{k: v for k, v in BEFORE_THE_TRAILER.items() if has(v)}, **found}


def headings(ids: list[str]) -> dict[str, list[str]]:
    """Each row that is a heading over others, and the rows under it.

    A row like `3.3` whose work is done by `3.3a` to `3.3h` is a heading, not a slice: nothing carries a
    `Slice-done: 3.3` trailer and nothing ever will, so without this it counts as outstanding for ever and
    the total is wrong by one from the day the group lands.
    """
    found: dict[str, list[str]] = {}
    for one in ids:
        under = [other for other in ids if other != one and other.startswith(one)
                 and other[len(one):].isalnum()]
        if under:
            found[one] = under
    return found


#: A row whose description is only a pointer at the slice its work moved to. Nothing will ever carry its
#: trailer, so without this it counts as outstanding for as long as the plan exists.
MOVED = re.compile(r"^\*Moved to .*? as (?P<to>\d+\.\d+[a-z]?)\b")


def moved(page: str) -> dict[str, str]:
    """Each redirecting row, and the slice its work moved to."""
    found: dict[str, str] = {}
    for line in page.splitlines():
        match = ROW.match(line)
        if match:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            pointer = MOVED.match(cells[1]) if len(cells) > 1 else None
            if pointer:
                found[match.group(1)] = pointer.group("to")
    return found


def with_headings(done: dict[str, str], ids: list[str], page: str = "") -> dict[str, str]:
    """`done`, plus every heading all of whose rows are done, and every row whose work moved elsewhere."""
    whole = dict(done)
    for heading, under in headings(ids).items():
        if heading not in whole and all(one in done for one in under):
            whole[heading] = done[under[-1]]
    for row, to in moved(page).items():
        if row not in whole and to in done:
            whole[row] = done[to]
    return whole


def has(short: str) -> bool:
    """Whether a commit of `BEFORE_THE_TRAILER` is an ancestor of what is checked out, so a branch that
    predates one does not claim its slice."""
    done = subprocess.run(
        ["git", "merge-base", "--is-ancestor", short, "HEAD"], cwd=ROOT, capture_output=True
    )
    return done.returncode == 0


def ticked(page: str, done: dict[str, str]) -> str:
    """The plan with every slice table carrying a Status column that the history, not a person, fills in.

    Each line is stripped of the column this script last wrote before the new one is added, so running it
    twice leaves the page exactly as running it once did. A table that grows a column per run is the
    classic shape of this bug.
    """
    lines = page.splitlines()
    start = lines.index(SECTION)
    out = lines[:start]
    for line in lines[start:]:
        if line.startswith("| Slice |"):
            out.append(without_status(line) + " Status |")
        elif re.fullmatch(r"\|(-+\|)+", line) and out[-1].endswith(" Status |"):
            # Built from the header rather than edited: a separator cell is `---` whichever column it is,
            # so stripping "the one this script wrote" would take a real column on the first run.
            out.append("|" + "---|" * (out[-1].count("|") - 1))
        elif match := ROW.match(line):
            short = done.get(match.group(1))
            out.append(without_status(line) + (f" {DONE} |" if short else f" {TODO} |"))
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def without_status(row: str) -> str:
    """A header or row with the Status cell this script last wrote removed, and nothing else touched.

    Every trailing cell that *says* status — `done`, the older `done <hash>`, or the `Status` header — is
    taken off, because a row can carry more than one: changing the cell's shape once left `| done <hash> |
    done |` behind, and stripping only the last of those is how a column quietly doubles. After those, at
    most one empty cell is taken, which is what an unticked row's cell is. No more than one, because a
    table row may legitimately end in an empty cell of its own.

    Not for separators: `---` is what every cell of one holds, so there is no telling this script's from a
    real column. `ticked` rebuilds those from the header's width instead.
    """
    body = row.rstrip()
    said = re.compile(r"\|\s*(done(?: [0-9a-f]{7,})?|Status)\s*\|$")
    while said.search(body):
        body = body[: body.rfind("|", 0, len(body) - 1) + 1].rstrip()
    if re.search(r"\|\s*\|$", body):
        body = body[: body.rfind("|", 0, len(body) - 1) + 1].rstrip()
    return body


def summary(page: str, done: dict[str, str]) -> str:
    """One line under section 11's heading saying how far the build has got, by phase."""
    ids = [m.group(1) for line in page.splitlines() if (m := ROW.match(line))]
    phases: dict[str, list[str]] = {}
    for slice_id in ids:
        phases.setdefault(slice_id.split(".")[0], []).append(slice_id)
    parts = [
        f"phase {phase} {sum(1 for i in found if i in done)}/{len(found)}"
        for phase, found in sorted(phases.items(), key=lambda kv: int(kv[0]))
    ]
    return (
        f"**Progress: {sum(1 for i in ids if i in done)} of {len(ids)} slices done** — "
        + ", ".join(parts)
        + ". Written by `scripts/progress.py` from the history; run `make progress` after a slice merges."
    )


# The cell says `done` and not the commit that did it, on purpose: a slice is committed with its trailer
# and ticked in the same commit, and amending to fold the tick in changes the hash the tick just recorded.
# The history holds the hashes; the plan holds the fact.
def rendered() -> str:
    page = PLAN.read_text(encoding="utf-8")
    ids = [m.group(1) for line in page.splitlines() if (m := ROW.match(line))]
    done = with_headings(shipped(), ids, page)
    page = ticked(page, done)
    line = summary(page, done)
    lines = page.splitlines()
    at = lines.index(SECTION) + 1
    if at + 1 < len(lines) and lines[at + 1].startswith("**Progress:"):
        lines[at + 1] = line
    else:
        lines[at:at] = ["", line]
    return "\n".join(lines) + "\n"


def without_the_total(page: str) -> str:
    """The page with its one shared line blanked, which is what `--check` compares.

    Two things of different natures live in this file and only one of them is concurrent-safe.

    A **Status cell** is per slice and disjoint: the slice that lands `10.1` ticks row `10.1` and no other
    branch touches it. That is the same shape `check-slice-scope.py` already grants a slice over its own
    block of `docs/event-model/model.yaml` — "every other slice's block reads exactly as on `main`" — and
    it merges cleanly however many fairways are open.

    The **`**Progress:` line** is one shared line that every branch rewrites, because its totals count
    every slice in the plan. That is precisely the conflict `changelog.d` was created to eliminate: one
    block at a known spot, and "every pair of branches that overlapped in time inserted at the same spot".
    Worse than the conflict, it made the gate unpassable — a captain on a branch with one new trailer
    computed a different total from trunk's, so `--check` was red and the only way to green was to edit a
    file every other fairway was also holding.

    So the totals stop being gated. They are rendered, like `docs/event-model/model.drawio`, which
    `check-slice-scope` says the host regenerates after each merge. `make progress` still writes them; what
    is *held* to the history is the ticks, which is what the plan is read for.
    """
    lines = page.splitlines()
    return "\n".join("**Progress:**" if line.startswith("**Progress:") else line for line in lines) + "\n"


def main(arguments: list[str]) -> int:
    wanted = rendered()
    if "--check" not in arguments:
        PLAN.write_text(wanted, encoding="utf-8")
        ids = [m.group(1) for line in wanted.splitlines() if (m := ROW.match(line))]
        print(summary(wanted, with_headings(shipped(), ids, wanted)).split(" — ")[0].replace("**", ""))
        return 0
    if without_the_total(PLAN.read_text(encoding="utf-8")) == without_the_total(wanted):
        print("progress: the plan's ticks match the history")
        return 0
    print("progress: the plan's ticks are out of step with the history.\n  Run: make progress", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
