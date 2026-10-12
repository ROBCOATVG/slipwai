#!/usr/bin/env python3
"""Install a built wheel in an isolated environment and exercise its bundled keel."""
from __future__ import annotations

import argparse
import subprocess
import tempfile
import venv
from pathlib import Path

from smoke_distribution import smoke

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        environment = Path(temporary)
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if (environment / "Scripts").is_dir() else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)], check=True)
        smoke([str(python), "-m", "slipwai"], (ROOT / "VERSION").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
