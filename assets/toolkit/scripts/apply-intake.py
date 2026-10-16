#!/usr/bin/env python3
"""Apply the confirmed rows of `.slipwai/intake-cleanup.json`.

A row that is not confirmed, or whose action is not `intake`, is left where it is and named. A destination
that already exists is a refusal. Nothing else in the tree is moved.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    root = Path.cwd()
    proposal = root / ".slipwai/intake-cleanup.json"
    if not proposal.is_file():
        print("apply-intake: .slipwai/intake-cleanup.json is not there; `slipwai migrate` writes it",
              file=sys.stderr)
        return 2
    try:
        held = json.loads(proposal.read_text(encoding="utf-8"))
    except ValueError as error:
        print(f"apply-intake: .slipwai/intake-cleanup.json does not read: {error}", file=sys.stderr)
        return 2
    rows = held.get("rows") if isinstance(held, dict) else None
    if not isinstance(rows, list):
        print("apply-intake: .slipwai/intake-cleanup.json has no rows; leave it for /catch-up to read",
              file=sys.stderr)
        return 2
    moved, refused = [], []
    for row in rows:
        if not isinstance(row, dict) or not row.get("confirmed") or row.get("action") != "intake":
            continue
        source = root / str(row.get("path") or "")
        destination = root / str(row.get("destination") or "")
        if not source.is_file() or destination == root or not str(row.get("destination") or "").startswith("docs/intake/"):
            refused.append(str(row.get("path") or ""))
            continue
        target = destination / source.name
        if target.exists():
            refused.append(f"{row.get('path')} would overwrite {target.relative_to(root).as_posix()}")
            continue
        destination.mkdir(parents=True, exist_ok=True)
        shutil.move(source, target)
        moved.append(f"{row.get('path')} -> {target.relative_to(root).as_posix()}")
    if refused:
        print("apply-intake: refused: " + "; ".join(refused), file=sys.stderr)
        print("Edit .slipwai/intake-cleanup.json so each confirmed intake row names an empty destination, "
              "then run python3 scripts/apply-intake.py", file=sys.stderr)
        return 1
    print("applied: " + (", ".join(moved) if moved else "nothing confirmed"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
