#!/usr/bin/env python3
"""Hold a crossing open until a person confirms every proposed context and places every slice."""
from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path


def project_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "project.json").is_file():
            return candidate
    return Path(__file__).resolve().parents[1]


def chart(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        loaded = json.loads(text)
    except ValueError:
        try:
            import yaml
        except ImportError:
            raise ValueError("YAML needs PyYAML; run `python3 -m pip install PyYAML`, then retry") from None
        loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} is not a chart; run `/chart`, then retry")
    return loaded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="record the person's confirmation of the current charts")
    args = parser.parse_args(argv)
    root = project_root()
    path = root / ".slipwai/migration.json"
    if not path.is_file():
        print("migration: no crossing remains to confirm")
        return 0
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("v") != 1 or not isinstance(state.get("features"), dict):
            raise ValueError("unknown migration state; run `slipwai upgrade` before retrying")
        pending = []
        for feature, record in state["features"].items():
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", feature) or feature in {".", ".."}:
                raise ValueError("a feature name leaves specs/; restore .slipwai/migration.json before retrying")
            if not isinstance(record, dict) or not all(isinstance(record.get(key), list) and
                    all(isinstance(name, str) and name for name in record[key]) for key in ("proposed", "unplaced")):
                raise ValueError(f"{feature}: migration state is unreadable; restore .slipwai/migration.json and retry")
            if not record.get("proposed") and not record.get("unplaced"):
                continue
            if args.confirm:
                current = chart(root / "specs" / feature / "chart.yaml")
                fairways = current.get("fairways") or {}
                slices = current.get("slices") or {}
                unplaced = [slice_id for slice_id, item in slices.items()
                            if not isinstance(item, dict) or item.get("fairway") == "unplaced"
                            or item.get("fairway") not in fairways]
                missing = set(record.get("unplaced") or []) - set(slices)
                if unplaced or missing:
                    raise ValueError(f"{feature}: slices still unplaced or missing: "
                                     f"{', '.join(sorted(set(unplaced) | missing))}; "
                                     "place them on the chart with `/chart`, then retry --confirm")
                record["proposed"], record["unplaced"] = [], []
            else:
                pending.append(f"{feature}: {len(record.get('proposed') or [])} fairways proposed, "
                               f"{len(record.get('unplaced') or [])} slices in unplaced")
        if pending:
            print("migration: " + "; ".join(pending) + ". Run this command with --confirm after `/chart`.")
            return 1
        if args.confirm:
            state["confirmed"] = datetime.now(UTC).isoformat()
            path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("migration: fairway confirmation satisfied")
        return 0
    except (OSError, ValueError, TypeError, AttributeError) as error:
        print(f"migration: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
