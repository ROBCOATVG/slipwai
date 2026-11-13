#!/usr/bin/env python3
"""Number a dev build of main: the snapshot `N` commits past the last release, `2.1.0.dev14`.

`VERSION` on main is `<next>.dev0` from the day a release is cut until the next one, so every build of main
published that one string, though each was different code. A project migrated by one dev build could not be
told from one migrated by the next: catch-up listed the whole release as "both are 2.1.0", and the app's
check that it is the release a project was last written by could not see two dev builds apart. The dev number
is what `versions.snapshot` was written for, and this is what fills it in.

`N` counts the commits on this branch since the newest `v*` tag, so it only climbs along main. A tree whose
`VERSION` is a release (`make release` writes it, and its tag builds it) is left as it is. A checkout with no
tag history — CI's default shallow clone — is refused rather than numbered from a count it cannot make.

    python3 scripts/dev-version.py           # print the number this tree builds as
    python3 scripts/dev-version.py --write   # and write it into VERSION, for the build only; never committed
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slipwai.versions import is_release, snapshot  # noqa: E402


def git(*argv: str) -> str:
    done = subprocess.run(["git", *argv], cwd=ROOT, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"dev-version: `git {' '.join(argv)}` failed: {(done.stderr or done.stdout).strip()}. "
                         f"A dev build is numbered from the tag history: check out with `fetch-depth: 0`")
    return done.stdout.strip()


def numbered(version: str) -> str:
    """The version this tree builds as: a release as it is, a snapshot with its commit count."""
    if is_release(version):
        return version
    tag = git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
    return snapshot(version, int(git("rev-list", "--count", f"{tag}..HEAD")))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="dev-version", description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write the number into VERSION for this build")
    parsed = parser.parse_args(argv)
    held = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    version = numbered(held)
    if parsed.write and version != held:
        (ROOT / "VERSION").write_text(version + "\n", encoding="utf-8")
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
