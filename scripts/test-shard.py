#!/usr/bin/env python3
"""The test modules one CI job of several runs: `test-shard.py <index> <count>` prints them, one a line.

The suite on one process took 27 minutes on Windows and 13 to 16 elsewhere, and a run is as long as its
slowest job. So `verify.yml` splits it, and this is the split: every `tests/test_*.py` in exactly one shard,
balanced on what each module took on this platform in CI (`tests/fixtures/test-durations.json`). Each is
placed, the heaviest first, in whichever shard is lightest so far. A module the record does not know yet
weighs what the Makefile says of it — a `SLOW` one eight times a fast one — until the record is refreshed.

    make test TESTS="$(python3 scripts/test-shard.py 0 4)"
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DURATIONS = ROOT / "tests/fixtures/test-durations.json"
SLOW_WEIGHT = 8


def slow() -> set[str]:
    """The modules the Makefile's `SLOW :=` and `SLOW +=` lines name."""
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    return {name for line in re.findall(r"^SLOW \+?:?= (.*)$", text, re.MULTILINE) for name in line.split()}


def weights(modules: list[str], platform: str) -> dict[str, float]:
    """Each module's cost here: its measured seconds, or for one not measured yet the median module's,
    times eight where the Makefile calls it slow."""
    try:
        measured = json.loads(DURATIONS.read_text(encoding="utf-8")).get(platform) or {}
    except (OSError, ValueError):
        measured = {}
    usual = statistics.median(measured.values()) if measured else 1.0
    named = slow()
    return {one: float(measured.get(one, usual * (SLOW_WEIGHT if one in named else 1))) for one in modules}


def shards(count: int, platform: str | None = None) -> list[list[str]]:
    modules = sorted(path.stem for path in (ROOT / "tests").glob("test_*.py"))
    cost = weights(modules, platform or sys.platform)
    held: list[list[str]] = [[] for _ in range(count)]
    load = [0.0] * count
    for module in sorted(modules, key=lambda one: (-cost[one], one)):
        lightest = load.index(min(load))
        held[lightest].append(module)
        load[lightest] += cost[module]
    return [sorted(one) for one in held]


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not all(one.isdigit() for one in argv) or not 0 <= int(argv[0]) < int(argv[1]):
        print("usage: test-shard.py <index> <count>, with 0 <= index < count", file=sys.stderr)
        return 2
    print("\n".join(shards(int(argv[1]))[int(argv[0])]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
