#!/usr/bin/env python3
"""The coverage gate `make test` holds a Go service to: the share of its statements the suite reaches.

    python3 scripts/go-coverage.py <service> <minimum>

Reads `<service>/coverage.out`, which the line before this one in the Makefile writes with
`go test -coverpkg=./... -coverprofile=coverage.out ./...`. `-coverpkg=./...` is the part that makes the
number mean something: without it Go credits a package only with its own tests, so the domain package here —
tested through every adapter and holding no `_test.go` of its own — reads 0% while the store's tests
exercise every line of it.

Two kinds of package are left out of the total, and both are read from `go list` rather than named here,
so nothing has to be kept in step with the tree:

- **`main` packages.** An entry point is wiring by construction — the hexagon keeps it thin — and a test
  of one is a test of the framework it wires.
- **Packages whose only tests are behind a build tag** (`//go:build integration`). `go test` without the
  tag cannot run them, so their coverage is `make test-integration`'s to show, not this gate's to miss.

The gate fails below the minimum, and it fails when there is nothing in scope to measure: a coverage gate
that passes on an empty profile is a misconfigured run that looks like a good one.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROFILE = "coverage.out"


def packages(service: Path) -> list[dict]:
    """Every package in the module, as `go list` describes it."""
    fields = "ImportPath,Name,TestGoFiles,XTestGoFiles,IgnoredGoFiles"
    listed = subprocess.run(
        ["go", "list", f"-json={fields}", "./..."], cwd=service, text=True, capture_output=True,
    )
    if listed.returncode != 0:
        sys.stderr.write(listed.stderr)
        sys.exit(listed.returncode)
    decoder = json.JSONDecoder()
    text, position, found = listed.stdout, 0, []
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position >= len(text):
            break
        package, position = decoder.raw_decode(text, position)
        found.append(package)
    return found


def out_of_scope(package: dict) -> str | None:
    """Why a package is not counted, or None when it is."""
    if package.get("Name") == "main":
        return "entry point"
    tested = (package.get("TestGoFiles") or []) + (package.get("XTestGoFiles") or [])
    tagged = [f for f in package.get("IgnoredGoFiles") or [] if f.endswith("_test.go")]
    if tagged and not tested:
        return "tests run under make test-integration"
    return None


def blocks(profile: str) -> dict[tuple[str, str], tuple[int, int]]:
    """Each coverage block once, keyed by file and span: its statement count, and how often it ran.

    With `-coverpkg` the same block appears once per test binary that could reach it, each with its own
    count, and the block is covered if any of them ran it.
    """
    found: dict[tuple[str, str], tuple[int, int]] = {}
    for line in profile.splitlines()[1:]:
        if not line.strip():
            continue
        location, statements, count = line.rsplit(" ", 2)
        file, span = location.split(":", 1)
        key = (file, span)
        previous = found.get(key, (int(statements), 0))
        found[key] = (previous[0], previous[1] + int(count))
    return found


def measure(profile: str, excluded: dict[str, str]) -> tuple[dict[str, tuple[int, int]], int, int]:
    """Statements and covered statements per in-scope package, and the totals."""
    per_package: dict[str, tuple[int, int]] = {}
    total = covered = 0
    for (file, _), (statements, count) in blocks(profile).items():
        package = file.rsplit("/", 1)[0]
        if package in excluded:
            continue
        seen = per_package.get(package, (0, 0))
        hit = statements if count > 0 else 0
        per_package[package] = (seen[0] + statements, seen[1] + hit)
        total += statements
        covered += hit
    return per_package, total, covered


def percent(covered: int, total: int) -> float:
    return 100.0 * covered / total if total else 0.0


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stderr.write("usage: go-coverage.py <service> <minimum-percent>\n")
        return 2
    service, minimum = Path(argv[1]), float(argv[2])
    profile_path = service / PROFILE
    if not profile_path.is_file():
        sys.stderr.write(
            f"{profile_path}: not found; run `go test -coverpkg=./... -coverprofile={PROFILE} ./...` first\n"
        )
        return 2
    excluded = {
        package["ImportPath"]: reason
        for package in packages(service)
        if (reason := out_of_scope(package)) is not None
    }
    per_package, total, covered = measure(profile_path.read_text(), excluded)
    width = max((len(name) for name in [*per_package, *excluded]), default=0)
    for name, (statements, hit) in sorted(per_package.items()):
        print(f"  {name:<{width}}  {percent(hit, statements):6.1f}%  ({hit}/{statements} statements)")
    for name, reason in sorted(excluded.items()):
        print(f"  {name:<{width}}  not counted: {reason}")
    if total == 0:
        sys.stderr.write(f"coverage: no statements in scope in {profile_path}; nothing was measured\n")
        return 1
    score = percent(covered, total)
    verdict = "at or above" if score >= minimum else "below"
    print(f"coverage: {score:.1f}% of {total} statements, {verdict} the {minimum:g}% minimum")
    return 0 if score >= minimum else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
