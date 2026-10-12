#!/usr/bin/env python3
"""Exercise a frozen keel independently of the factory checkout or installed languages."""
from __future__ import annotations

import argparse
from pathlib import Path

from smoke_distribution import smoke

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    smoke([str(args.executable.resolve())], (ROOT / "VERSION").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
