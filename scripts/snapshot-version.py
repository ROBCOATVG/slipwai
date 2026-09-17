#!/usr/bin/env python3
"""Say which snapshot this commit of `main` is, and — asked to — write it into `VERSION` for one build.

`VERSION` on `main` reads `1.3.0.dev0`: the release being worked towards, marked as not there yet. Every
green push publishes that commit as a snapshot, and two snapshots cannot share a number — the registry takes
a name and version once — so the number is counted rather than written: `1.3.0.dev<N>`, `N` the commits
since the newest release tag. Counted from the tag rather than from the commit that opened the number, so
`N` only ever rises across a cycle, including when a change raises `1.12.1.dev0` to `1.3.0.dev0` midway.

    python3 scripts/snapshot-version.py            # print it: 1.3.0.dev7
    python3 scripts/snapshot-version.py --write    # and write it into VERSION, uncommitted

`--write` is for the publish job and for nothing else: the checkout it runs in is thrown away, and the wheel
and executable built from it then carry the number they were published under, so `slipwai --version` on an
installed snapshot says which one it is. Nothing here commits — a committed `.dev7` would be a second place
the number is written, and the next push would make it wrong.

Exit 3 when `VERSION` is a release rather than a snapshot. That is the `Release 1.3.0` commit, which the
tag publishes; a snapshot job that finds itself there has nothing of its own to publish and says so.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slipwai.versions import is_snapshot, snapshot  # noqa: E402 — after the path that makes it importable

NOT_A_SNAPSHOT = 3


def git(*arguments: str) -> str:
    done = subprocess.run(["git", "-C", str(ROOT), *arguments], text=True, capture_output=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"snapshot-version: git {' '.join(arguments)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def newest_release_tag() -> str | None:
    """The newest `v*` tag this history has, or `None` in a history that has never released."""
    tags = git("tag", "--list", "v*", "--sort=-v:refname").split()
    return tags[0] if tags else None


def commits_since(tag: str | None) -> int:
    """How many commits `HEAD` is past the tag — or past the root, before the first release."""
    return int(git("rev-list", "--count", f"{tag}..HEAD" if tag else "HEAD"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="write the snapshot into VERSION (uncommitted)")
    args = parser.parse_args()

    version_file = ROOT / "VERSION"
    written = version_file.read_text().strip()
    if not is_snapshot(written):
        print(
            f"snapshot-version: VERSION is {written}, a release rather than a snapshot; the tag publishes "
            f"this commit and main has nothing of its own to publish here",
            file=sys.stderr,
        )
        return NOT_A_SNAPSHOT
    if git("rev-parse", "--is-shallow-repository") == "true":
        raise SystemExit(
            "snapshot-version: this checkout is shallow, so the commits since the last release cannot be "
            "counted; check out with fetch-depth: 0"
        )
    version = snapshot(written, commits_since(newest_release_tag()))
    if args.write:
        version_file.write_text(f"{version}\n")
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
