#!/usr/bin/env python3
"""Materialize every starter combination into build/starters/ for local inspection.

The starters are pure derived artifacts of the generator, so no copy of them is committed anywhere:
`assets/toolkit/` and its overlays are the single source, and a change there reaches every
combination the moment it is generated. Run `make starters` to browse the current output of every
profile/backend combination under build/starters/<profile>/<backend>/.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FACTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY / "src"))

from slipwai.catalog import CATALOG  # noqa: E402

STARTERS_ROOT = FACTORY / "build/starters"


def starters() -> list[tuple[str, str, str]]:
    """Every profile and backend, keyed by the backend rather than by its language.

    Named `--backend` below for the same reason: a backend key is only ever a bare language name
    while its family has one member, so passing one as `--language` works by coincidence and stops
    working the moment a family gains a second framework.
    """
    return [
        (profile, backend, f"{profile}-{backend}-starter")
        for profile in CATALOG["profiles"]
        for backend in CATALOG["backends"]
    ]


def generate(parent: Path, profile: str, backend: str, name: str) -> Path:
    subprocess.run(
        [
            str(FACTORY / "slipwai"),
            "generate",
            name,
            "--profile",
            profile,
            "--backend",
            backend,
            "--frontend",
            "none",
            "--output",
            str(parent),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    repo = parent / name
    shutil.rmtree(repo / ".git")
    return repo


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        parent = Path(directory)
        for profile, backend, name in starters():
            fresh = generate(parent, profile, backend, name)
            target = STARTERS_ROOT / profile / backend
            if target.exists():
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(fresh, target)
            print(f"materialized: build/starters/{profile}/{backend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
