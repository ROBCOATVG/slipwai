#!/usr/bin/env python3
"""A conflict in the harbourmaster's rebase, settled where it stopped instead of sent back to the slice.

A refused merge costs a session: the captain goes back into the slice's worktree, rebases by hand, walks
its gate and asks again. manda's second feature was refused 27 times for a conflict in a day and a half,
with five slices building at once, and 20 of those were in the feature's own record — `decisions.md`,
`adversary-log.md`, `benchmark.md` — where two slices had each added an entry and neither had disagreed
with the other. The rule for those files held only a commit that added to the very end of the file and
changed nothing else, and a slice that reworded a line of its own entry in the same commit fell outside it.

So there are two answers here, and the gate runs on what either makes:

- **A record file is woven** (`woven`): the commit's changes and trunk's are both applied wherever they do
  not touch the same lines, and two additions at one place are both kept, trunk's first. Only the same lines
  changed two ways is still a conflict.
- **Anything else is the mender's** (`settle`): one bounded session of `agents/harbour-trunk-mender.md` in
  the scratch worktree, mid-rebase, asked to make both changes hold in the files git stopped on. It is held
  mechanically, not by its brief: the rebase must be where it was, no other file may have changed, and no
  conflict marker may be left. Where it cannot, the merge is refused exactly as before and the slice
  resolves it in its own worktree.

Standalone and dependency-free, like everything under `scripts/`.
"""
from __future__ import annotations

import difflib
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import mender

#: The files every slice of a feature adds to: its decisions, its adversary log, its benchmark overview.
RECORDS = re.compile(r"^specs/[^/]+/(decisions|adversary-log|benchmark)\.md$")
#: The two of them `make decisions` renders from one file per entry, `specs/<feature>/<name>/*.md`, once a
#: feature has those records: never woven, because weaving is what lost lines (below), but rendered again.
RENDERED = re.compile(r"^specs/(?P<feature>[^/]+)/(?P<name>decisions|adversary-log)\.md$")
#: Where the renderer is in a checkout, as it is in this one: `<delivery>/scripts/render-fairways.py`.
RENDERER = Path(__file__).resolve().parent.parent / "render-fairways.py"
#: One `## ` entry of a log, to its next one.
ENTRY = re.compile(r"^## .*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
CONFLICT = "conflict"
#: Used where `harbour.json` does not say `conflict_minutes`. 0 there turns the session off.
DEFAULT_MINUTES = 15
#: How many times one merge may stop for a session: one per replayed commit that conflicts. A slice a
#: thousand commits behind trunk stopped on one file seven times; at four the merge was refused with the
#: file half-way settled and nothing saying the mender had been at it.
STOPS = 12
MARKS = re.compile(r"^(<{7}|>{7})( |$)", re.MULTILINE)

Hunk = tuple[int, int, list[str]]


def _lines(text: str) -> list[str]:
    return (text if not text or text.endswith("\n") else text + "\n").splitlines(keepends=True)


def _hunks(base: list[str], other: list[str]) -> list[Hunk]:
    """What `other` did to `base`: each run of base lines it replaced, and with what. A run replaced by a
    longer one is a replacement and then an addition, so an entry added after a reworded line is an addition."""
    found: list[Hunk] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base, other, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if i2 > i1 and j2 - j1 > i2 - i1:
            found += [(i1, i2, other[j1:j1 + i2 - i1]), (i2, i2, other[j1 + i2 - i1:j2])]
        else:
            found.append((i1, i2, other[j1:j2]))
    return found


def woven(before: str, onto: str, commit: str) -> str | None:
    """`onto` with what `commit` did to `before` applied as well, or None where both changed the same lines.

    Two additions at the same place are both kept, trunk's first; one that trunk already holds is not put
    in twice. A change beside an addition is not a conflict here, as it is to git: the order is not in doubt.
    """
    base = _lines(before)
    theirs, ours = _hunks(base, _lines(onto)), _hunks(base, _lines(commit))
    out: list[str] = []
    at = 0

    def put(upto: int, lines: list[str], after: int) -> None:
        nonlocal at
        out.extend([*base[at:upto], *lines])
        at = after

    while theirs or ours:
        if theirs and ours:
            (t1, t2, tl), (o1, o2, ol) = theirs[0], ours[0]
            if (t1, t2) == (o1, o2):
                if t1 == t2:
                    again = "".join(ol).strip() in onto
                    put(t1, tl if tl == ol or again else [*tl, *ol], t2)
                elif tl == ol:
                    put(t1, tl, t2)
                else:
                    return None
                theirs.pop(0)
                ours.pop(0)
                continue
            if max(t1, o1) < min(t2, o2) or (t1 == t2 and o1 < t1 < o2) or (o1 == o2 and t1 < o1 < t2):
                return None
        mine = bool(ours) and (not theirs or ours[0][:2] < theirs[0][:2])
        start, end, lines = (ours if mine else theirs).pop(0)
        if mine and start == end and "".join(lines).strip() and "".join(lines).strip() in onto:
            lines = []  # an entry trunk already holds: this commit landed once before
        put(start, lines, end)
    put(len(base), [], len(base))
    return "".join(out)


def kept(onto: str, commit: str) -> str:
    """Trunk's log with every entry of the commit's that trunk has not got after it, matched by heading. Never
    the file's answer — the render that follows is — but what that render adopts from: an entry a page older
    than the records appended to the log rather than writing a record of its own is in neither side's records,
    and would otherwise be lost with the side not taken."""
    heads = {found.group(0).split("\n", 1)[0] for found in ENTRY.finditer(onto)}
    extra = [found.group(0).rstrip() + "\n" for found in ENTRY.finditer(commit)
             if found.group(0).split("\n", 1)[0] not in heads]
    return onto.rstrip("\n") + "\n\n" + "\n".join(extra) if extra else onto


def rendered(where: Path, path: str, onto: str, commit: str) -> bool:
    """A conflicted log `make decisions` renders, rendered again in the checkout at `where` from the records as
    the rebase has them — both sides', since a record is a file of its own and two slices never write one.
    False where it is not such a log, the feature keeps no records yet (it is woven, as it was), or the
    renderer could not run.

    Weaving was the wrong answer for these. Two slices each appending a decision ending `- **Status:**
    standing` is two additions whose last line is the same, and a weave that keeps an addition only when
    trunk has not already got it dropped the slice's: manda restored a dropped Status line by hand six times,
    after `check-decisions` refused the next merge each time.
    """
    found = RENDERED.match(path)
    if found is None or not (where / "specs" / found.group("feature") / found.group("name")).is_dir():
        return False
    try:
        renderer = where / RENDERER.relative_to(mender.ROOT.resolve())
    except ValueError:
        return False
    if not renderer.is_file() or "--split" not in renderer.read_text(encoding="utf-8", errors="replace"):
        return False  # a renderer older than the records would drop what the slice appended, and fold the split
    (where / path).write_text(kept(onto, commit), encoding="utf-8", newline="")
    try:
        ran = subprocess.run([sys.executable, "-B", str(renderer), "--split"], cwd=where, capture_output=True,
                             text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if ran.returncode != 0:
        return False
    folder = f"specs/{found.group('feature')}/{found.group('name')}"
    return mender.git("add", "-A", "--", path, folder, where=where).returncode == 0


def bound() -> float:
    """Seconds one session may run. 0 where `harbour.json` turns it off."""
    held = mender.config().get("conflict_minutes")
    return float(held if isinstance(held, int | float) and not isinstance(held, bool) and held >= 0
                 else DEFAULT_MINUTES) * 60.0


def wanted(branch: str) -> bool:
    """Whether a conflict on this branch is the mender's before it is the slice's: a slice's branch, under
    `/cruise` — where a person asked not to be waited on, as for a need — and not turned off."""
    return branch.startswith("slice/") and bound() > 0 \
        and (bool(os.environ.get("SLIPWAI_MENDER")) or mender.cruising())


def _others(where: Path, paths: list[str]) -> set[str]:
    """Every path git has anything to say about but the conflicted ones, with what it says."""
    said = mender.git("status", "--porcelain=v1", "-z", "--untracked-files=all", where=where).stdout
    return {entry for entry in said.split("\0") if entry and entry[3:] not in paths}


def _head(where: Path) -> str:
    stopped = mender.git("rev-parse", "--verify", "--quiet", "REBASE_HEAD", where=where).stdout.strip()
    return f"{mender.git('rev-parse', 'HEAD', where=where).stdout.strip()} {stopped}"


def settle(where: Path, paths: list[str], branch: str, onto: str, beat: Callable[[], None] | None = None,
           every: float = 60.0) -> str:
    """One session on the files this rebase stopped on, in `where`, and the paths staged if it settled
    them. Why it did not, or "". `beat` is called every `every` seconds while the session runs."""
    replaying = mender.git("log", "-1", "--format=%h %s", "REBASE_HEAD", where=where).stdout.strip()
    told = {"paths": paths, "slice": branch, "onto": onto, "replaying": replaying, "attempt": 1}
    others, head = _others(where, paths), _head(where)
    try:
        argv, environment = mender.command(CONFLICT, where, branch, told)
        out = mender.logs.run_dir(mender.ROOT) / "running/mender.out"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as handle:
            child = subprocess.Popen(argv, cwd=where, env=environment, stdout=handle, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=os.name != "nt")
    except (OSError, RuntimeError, ImportError) as refused:
        return f"the mender could not be started: {refused}"
    ends = time.monotonic() + bound()
    try:
        while True:
            try:
                code = child.wait(timeout=max(0.1, min(every, ends - time.monotonic())))
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() >= ends:
                    mender.end(child)
                    return f"the mender was still at it after {round(bound() / 60)} minute(s) and was ended"
                if beat is not None:
                    beat()
    finally:
        (where.parent / f"{where.name}.json").unlink(missing_ok=True)
    if code != 0:
        return f"the mender's session exited {code}"
    if _head(where) != head:
        return "the mender moved the rebase, which is the harbourmaster's to continue"
    moved = sorted(entry[3:] for entry in _others(where, paths) ^ others)
    if moved:
        return f"the mender changed {', '.join(moved)}, which the rebase had not stopped on"
    for path in paths:
        try:
            left = MARKS.search((where / path).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            left = None  # resolved by removing it, which `add -A` records
        if left:
            return f"the mender left {path} with a conflict marker in it"
        if mender.git("add", "-A", "--", path, where=where).returncode != 0:
            return f"{path} could not be staged as the mender left it"
    return ""
