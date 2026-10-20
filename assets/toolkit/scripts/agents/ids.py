#!/usr/bin/env python3
"""The next id for a fairway, counted out of its own deck log so two fairways can never mint the same one.

In the first attempt every berth took the next number after the last one it could see in its own checkout,
and every berth appended to one `decisions.md`. That cost 54 renumbering commits in a single night, and one
renumber rewrote 91 citations — every one of which had been correct when it was written. A claimed range of
numbers only shrinks the window; it does not close it.

So the id carries its fairway, and the counter is per fairway: `D-ORD-07`, `A-BIL-03`,
`ADR-ORD-2026-10-07-event-store`. Two fairways cannot collide because they are not counting the same thing.
Nothing is ever renumbered, which means a citation written today still resolves in a year.

**The count comes from the deck log, not from the file.** The file is rendered from the fairway's own
entries and a reader could be looking at a stale render, mid-merge, or at a feature-level aggregate that
holds two fairways' entries. The log is append-only, has one writer, and is the thing that recorded the
decision being counted.

**Version 1's ids stay valid.** A project that already has `D1` to `Dn` keeps them, resolving as they
always did, and only new ids carry a fairway. Renumbering the old ones to a new scheme would be the exact
cost this scheme exists to avoid, and `migrate` does not do it either.

**A project still on version 1's `D<n>` reserves its numbers.** Slices worked abreast are one fairway, so
the per-fairway counter does not separate them, and each delegating session took *the next after the last
entry it could see* — which in hr-test-2 was D28 to D30 for two slices at once. `reserve` takes the
highest number anything here knows — every `specs/*/decisions.md` in this checkout, on trunk and on every
local and remote `slice/*` branch, and every number already reserved — under a lock, writes what it hands
out to `.slipwai/logs/decision-numbers`, and prints them. The lock and the file are under `.slipwai/logs`,
which every berth links to the project's own, so the siblings on one machine take turns at one counter; a
sibling on another machine is seen through its pushed branch. A number reserved and never used is a gap,
which `check-decisions.py` allows: a gap costs nothing and a duplicate costs every citation of it.

    python3 scripts/agents/ids.py decision ORD      # D-ORD-07
    python3 scripts/agents/ids.py adversary BIL     # A-BIL-03
    python3 scripts/agents/ids.py reserve decision 3 L06   # D31 D32 D33, held for slice L06
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def project_root(script: Path) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[2]


ROOT = project_root(Path(__file__).resolve())
LOGS = ROOT / ".slipwai/logs"
V = 1
#: What each kind of record is counted and prefixed by. A kind not here has no id scheme and is refused
#: rather than given a guessed prefix, because an id is a citation and a wrong one resolves to nothing.
PREFIXES = {"decision": "D", "adversary": "A"}
#: The deck-log line kind that records each.
COUNTED = {"decision": "decision", "adversary": "stowed"}


def lines(feature: str, fairway: str) -> list[dict]:
    """Every line of one fairway's deck log, in the order written."""
    path = LOGS / feature / f"{fairway}.jsonl"
    if not path.is_file():
        return []
    found = []
    for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not text.strip():
            continue
        try:
            line = json.loads(text)
        except ValueError:
            raise SystemExit(f"ids: {path.name}:{number} is not JSON. Counting past a line nobody can read "
                             f"would mint an id somebody else already used.") from None
        if isinstance(line, dict) and line.get("v") != V:
            raise SystemExit(f"ids: {path.name}:{number} says v{line.get('v')} and this reader knows v{V}. "
                             f"Run `slipwai upgrade`.")
        if isinstance(line, dict):
            found.append(line)
    return found


def feature_in_flight() -> str:
    """The one feature with a log. A project between features has none, and the first id is 1."""
    found = sorted(path.name for path in LOGS.glob("*/") if path.is_dir()) if LOGS.is_dir() else []
    return found[0] if found else ""


def next_number(kind: str, fairway: str, feature: str = "") -> int:
    """How many of this kind this fairway has recorded, plus one."""
    if kind not in PREFIXES:
        raise SystemExit(f"ids: no id scheme for {kind!r}. There is one for: {', '.join(sorted(PREFIXES))}")
    counted = COUNTED[kind]
    written = lines(feature or feature_in_flight(), fairway)
    return sum(1 for line in written if line.get("kind") == counted) + 1


def next_id(kind: str, fairway: str, feature: str = "") -> str:
    """`D-ORD-07`. Two digits, so a fairway's ids sort as text for as long as it has fewer than a hundred."""
    number = next_number(kind, fairway, feature)
    return f"{PREFIXES[kind]}-{fairway}-{number:02d}"


#: Where reserved version-1 numbers are written, one `D<n> <slice> <instant>` per line, and the lock that
#: makes reading the highest and writing the next one a single step.
RESERVED = LOGS / "decision-numbers"
LOCK = LOGS / "decision-numbers.lock"
HEADING = re.compile(r"^## D(\d+) — ", re.M)


def git(*argv: str) -> str:
    done = subprocess.run(["git", *argv], cwd=ROOT, capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else ""


def numbers_in(text: str) -> set[int]:
    return {int(found) for found in HEADING.findall(text)}


def known_numbers() -> set[int]:
    """Every version-1 decision number this checkout can see: its own files, trunk's, every slice branch's,
    and every one already reserved."""
    found: set[int] = set()
    for path in sorted((ROOT / "specs").glob("*/decisions.md")):
        found |= numbers_in(path.read_text(encoding="utf-8", errors="replace"))
    refs = git("for-each-ref", "--format=%(refname)", "refs/heads/slice/", "refs/remotes/origin/slice/",
               "refs/heads/main", "refs/remotes/origin/main", "refs/heads/master",
               "refs/remotes/origin/master").split()
    for ref in refs:
        for path in git("ls-tree", "-r", "--name-only", ref, "--", "specs").splitlines():
            if path.endswith("/decisions.md"):
                found |= numbers_in(git("show", f"{ref}:{path}"))
    if RESERVED.is_file():
        found |= {int(line.split()[0][1:]) for line in RESERVED.read_text(encoding="utf-8").splitlines()
                  if re.match(r"^D\d+\b", line)}
    return found


def exclusive(lock) -> None:  # type: ignore[no-untyped-def]
    """Wait for the reservation lock. `flock` where there is one; Windows has none, and `msvcrt.locking`
    over the file's first byte is its equivalent — retried, because its blocking form gives up after ten
    seconds where `flock` waits as long as it must. Either is dropped with the process that held it."""
    if os.name == "nt":
        import msvcrt

        while True:
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]
                return
            except OSError:
                time.sleep(0.1)
    import fcntl

    fcntl.flock(lock, fcntl.LOCK_EX)


def release(lock) -> None:  # type: ignore[no-untyped-def]
    if os.name == "nt":
        import msvcrt

        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        return
    import fcntl

    fcntl.flock(lock, fcntl.LOCK_UN)


def reserve(count: int, held_for: str = "") -> list[str]:
    """The next `count` version-1 decision numbers, each handed out once on this machine."""
    LOGS.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+", encoding="utf-8") as lock:
        exclusive(lock)
        try:
            start = max(known_numbers(), default=0) + 1
            taken = [f"D{number}" for number in range(start, start + count)]
            stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            with RESERVED.open("a", encoding="utf-8") as file:
                file.writelines(f"{one} {held_for or '-'} {stamp}\n" for one in taken)
        finally:
            release(lock)
    return taken


def main(argv: list[str]) -> int:
    if argv[:1] == ["reserve"]:
        if argv[1:2] != ["decision"]:
            print("ids: reserve hands out version 1's `D<n>`, as `ids.py reserve decision [count] [slice]`",
                  file=sys.stderr)
            return 1
        count = int(argv[2]) if len(argv) > 2 and argv[2].isdigit() else 1
        print(" ".join(reserve(count, argv[3] if len(argv) > 3 else "")))
        return 0
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[-2].strip(), file=sys.stderr)
        print("ids: give a kind and a fairway, as `ids.py decision ORD`", file=sys.stderr)
        return 1
    print(next_id(argv[0], argv[1], argv[2] if len(argv) > 2 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
