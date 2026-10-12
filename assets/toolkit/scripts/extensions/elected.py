#!/usr/bin/env python3
"""Which extensions this project was generated to elect, as the words `./init` passes on.

A project generated from a quickstart carries `.slipwai/quickstart.json`: the quickstart's name, the
extensions it elects, and the guards the person who wrote it already agreed to. This prints the keys, space
separated, so `./init` can elect them without showing a menu to somebody who has already answered it.

    selected_extensions=$(python3 scripts/extensions/elected.py)

Silent and empty for a project that came from no quickstart, which is most of them — the menu then appears
exactly as it always has. A record that cannot be read is empty too: a bootstrap is not the place to argue
about a file, and `./init --extension <key>` is always there.

Standalone and dependency-free: this ships inside a generated project, which has no slipwai to import.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORD = ".slipwai/quickstart.json"


def project_root() -> Path:
    for candidate in HERE.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return HERE.parents[1]


def elected(path: Path) -> list[str]:
    """The keys the record names, in the order it names them, with anything that is not a key dropped."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return []
    found = document.get("extensions") if isinstance(document, dict) else None
    if not isinstance(found, list):
        return []
    return [key.strip() for key in found if isinstance(key, str) and key.strip()]


def main() -> int:
    print(" ".join(elected(project_root() / RECORD)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
