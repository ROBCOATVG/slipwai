#!/usr/bin/env python3
"""`make release`: assemble the entry, write the version, tag it, and leave nothing to remember.

A release is four things that have to agree: the number in `VERSION`, the entry at the top of
`CHANGELOG.md`, the tag, and the fragments being gone. Doing them by hand means doing three of them and
discovering the fourth from somebody's bug report.

**The number is derived, not typed.** The fragments claim a level each; the entry's level is the highest of
them, and the release is the last one bumped by that. So `1.14.2` with a fix and a new option among its
fragments is `1.15.0`, and nobody has to remember which of the two wins. `--release <version>` overrides it
for the one case arithmetic cannot answer — a `2.0.0` that is a decision rather than a sum.

**Nothing is written until everything can be.** A release that got as far as the tag and then found a
fragment it could not read would leave a tag pointing at a tree whose changelog is wrong, which is a thing
nobody can fix afterwards without rewriting history.

`--check` is the gate: the fragments are readable, each claims a level, and the number they imply is the
one `VERSION` carries. It runs in `make verify`, so a branch that writes a fragment claiming MAJOR and
leaves `VERSION` at a patch is red before it merges rather than at the release.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slipwai.changelog import GUIDE, LEVELS, entry, fragments, implied, level  # noqa: E402
from slipwai.versions import is_release, is_snapshot, parse  # noqa: E402

VERSION = ROOT / "VERSION"
CHANGELOG = ROOT / "CHANGELOG.md"
#: Where the released entries start. Everything above it is the file's own preamble and is never rewritten.
MARK = "Each entry's level"


def held() -> str:
    return VERSION.read_text(encoding="utf-8").strip()


def last_released() -> str | None:
    """The newest release `CHANGELOG.md` holds, or None where it holds none.

    The number a release is bumped *from*, and it comes from the changelog rather than from `VERSION`:
    `VERSION` on a branch is a snapshot of the release being written, so bumping from it would bump from
    the thing being decided.
    """
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            return line[3:].split(" — ")[0].strip()
    return None


def last_final() -> str | None:
    """The newest release `CHANGELOG.md` holds that was not a candidate — what a candidate's successor is
    bumped from, since the candidate did not spend its number."""
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines():
        if line.startswith("## ") and is_release(found := line[3:].split(" — ")[0].strip()):
            return found
    return None


def base(version: str) -> str:
    """A snapshot as the release it is heading for: `2.0.0.dev0` is a claim about `2.0.0`."""
    match = parse(version)
    if match is None:
        raise SystemExit(f"release: VERSION is {version!r}, which is not a version this factory released")
    return ".".join(match.groups()[:3])


def findings(found: list, release: str | None, releasing: bool) -> list[str]:
    """Everything wrong with the fragments, said at once rather than one per run.

    An empty `changelog.d/` is only a fault when a release is being cut. It is also the state a release
    leaves behind, and `--check` runs in `make verify` on every branch — so the gate would be red from the
    moment a release landed until the next change, which is a gate nobody would keep.
    """
    said: list[str] = []
    if not found and releasing:
        said.append(f"changelog.d/ holds no fragment but {GUIDE}, so there is nothing to release. "
                    f"A release with no entry is a version number nobody can find out the meaning of")
    for path, claim, body in found:
        if claim is None:
            said.append(f"{path.name}'s first line is not one of {', '.join(LEVELS)}, so nothing says what "
                        f"this change is worth")
        if not body.strip():
            said.append(f"{path.name} says nothing under its level. The entry is what a person reads after "
                        f"upgrading; an empty one tells them a number and no more")
    if found and release is None:
        said.append("no fragment claims a level, so there is no number these changes imply")
    return said


def assembled(release: str, found: list, first: bool) -> str:
    """`CHANGELOG.md` with this entry written in above the released ones."""
    text = CHANGELOG.read_text(encoding="utf-8")
    at = text.index(MARK)
    head, rest = text[:at], text[at:]
    after = rest.split("\n", 1)
    preamble = head + after[0] + "\n\n"
    return preamble + entry(release, found, first=first) + (after[1].lstrip("\n") if len(after) > 1 else "")


def run(argv: list[str]) -> int:
    run_git = ["git", "-C", str(ROOT)]
    parser = argparse.ArgumentParser(
        prog="make release", description="Assemble the entry, write the version, and tag it")
    parser.add_argument("--check", action="store_true", help="say whether a release could be cut, and stop")
    parser.add_argument("--release", default=None, help="the version, where it is a decision and not a sum")
    parser.add_argument("--dry-run", action="store_true", help="write nothing; print what would be written")
    parsed = parser.parse_args(argv)

    version = held()
    found = fragments(ROOT)
    last = last_released()
    # With no release behind it there is nothing to bump from, and the number `VERSION` is heading for is
    # the only claim there is. That is this fork's own state until 2.0.0 is cut: `2.0.0` is a decision about
    # what version 2 is, not a sum over the changes that got there.
    release = parsed.release or (implied(last, found, last_final()) if last and found
                                 else base(version) if found else None)
    faults = findings(found, release, releasing=not parsed.check)

    if parsed.check:
        # A snapshot is a claim about the release it is heading for, so what is checked is that the
        # fragments imply that release and not some other one.
        if found and release and last and is_snapshot(version) and release != base(version):
            faults.append(f"the fragments imply {release} and VERSION is {version}, a snapshot of "
                          f"{base(version)}. Change VERSION, or the level a fragment claims")
        if faults:
            print("check-release: a release could not be cut from this tree", file=sys.stderr)
            for fault in faults:
                print(f"  {fault}", file=sys.stderr)
            return 1
        said = f"{release} from {len(found)} fragment(s), level {level(found)}" if found else "nothing yet"
        print(f"check-release: {said}")
        return 0

    if faults:
        for fault in faults:
            print(f"release: {fault}", file=sys.stderr)
        return 1
    assert release is not None
    # `first` omits the level, which is only right for a repository's genuinely first release — where
    # "MAJOR relative to nothing" means nothing. This fork has 1.x behind it, so the level is the point.
    whole = assembled(release, found, first=False)
    if parsed.dry_run:
        print(whole[:2000])
        print(f"release: would write VERSION {release} and delete {len(found)} fragment(s)")
        return 0
    CHANGELOG.write_text(whole, encoding="utf-8")
    VERSION.write_text(f"{release}\n", encoding="utf-8")
    for path, _claim, _body in found:
        path.unlink()
    subprocess.run([*run_git, "add", "-A"], check=True)
    subprocess.run([*run_git, "commit", "-m", f"Release {release}"], check=True)
    subprocess.run([*run_git, "tag", "-a", f"v{release}", "-m", f"slipwai {release}"], check=True)
    print(f"release: {release} written, committed and tagged v{release}. "
          f"`git push --follow-tags` publishes it")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
