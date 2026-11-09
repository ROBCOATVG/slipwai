#!/usr/bin/env python3
"""The test modules one CI job of several runs: `test-shard.py <index> <count>` prints them, one a line.

The suite on one process took 27 minutes on Windows and 13 to 16 elsewhere, and a run is as long as its
slowest job. So `verify.yml` splits it, and this is the split: every `tests/test_*.py` in exactly one shard,
the same shards on every platform, balanced by the one thing known about a module's cost in advance —
whether the Makefile's `SLOW` list names it. A slow module counts as eight fast ones; each is placed, the
heaviest first, in whichever shard is lightest so far.

    make test TESTS="$(python3 scripts/test-shard.py 0 4)"
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOW_WEIGHT = 8


def slow() -> set[str]:
    """The modules the Makefile's `SLOW :=` and `SLOW +=` lines name."""
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    return {name for line in re.findall(r"^SLOW \+?:?= (.*)$", text, re.MULTILINE) for name in line.split()}


def shards(count: int) -> list[list[str]]:
    modules = sorted(path.stem for path in (ROOT / "tests").glob("test_*.py"))
    named = slow()
    weighed = sorted(modules, key=lambda one: (-(SLOW_WEIGHT if one in named else 1), one))
    held: list[list[str]] = [[] for _ in range(count)]
    load = [0] * count
    for module in weighed:
        lightest = load.index(min(load))
        held[lightest].append(module)
        load[lightest] += SLOW_WEIGHT if module in named else 1
    return [sorted(one) for one in held]


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not all(one.isdigit() for one in argv) or not 0 <= int(argv[0]) < int(argv[1]):
        print("usage: test-shard.py <index> <count>, with 0 <= index < count", file=sys.stderr)
        return 2
    print("\n".join(shards(int(argv[1]))[int(argv[0])]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
