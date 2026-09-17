"""How this factory's version strings read: a release, or a snapshot on the way to one.

`main` never carries a released number. Between releases `VERSION` reads `1.3.0.dev0` — the release it is
working towards, with a suffix that says it is not there yet — and every green push to `main` is published
as `1.3.0.dev<N>`, `N` counting the commits since the last release. `make release` strips the suffix, tags
`v1.3.0`, and opens `1.3.1.dev0` in the next commit. So there are two shapes and this module is the one
place that reads them: what a snapshot is a snapshot *of*, which of two strings is newer, and what the next
snapshot after a release is called.

The grammar is PEP 440's, kept to the part this factory writes, because the artifact is a wheel and the
installers already agree on what `.dev` means: a pre-release, which `pip install slipwai` and `uv tool
install slipwai` pass over unless asked for. That is what lets a snapshot sit in the same registry as the
releases without ever reaching somebody who did not ask for it.
"""
from __future__ import annotations

import re

# `1.3.0`, or `1.3.0.dev4`; the pre-release segments PEP 440 also allows are read but never written.
VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?(?:\.dev(\d+))?$")
# Sorted the way PEP 440 sorts them: a dev release below every pre-release of its number, all of them below
# the release itself.
PHASE = {"dev": 0, "a": 1, "b": 2, "rc": 3, "": 4}


def parse(version: str) -> re.Match[str] | None:
    return VERSION.match(version.strip())


def key(version: str) -> tuple[int, ...]:
    """A version as what it sorts by, so `1.5.10` is above `1.5.9` and `1.3.0.dev4` is below `1.3.0`.

    An unreadable one sorts below every real version rather than raising: a registry may hold a file this
    factory never wrote, and a stray name is not a reason to refuse to answer.
    """
    match = parse(version)
    if match is None:
        return (0,)
    major, minor, patch, pre, pre_number, dev = match.groups()
    numbers = (int(major), int(minor), int(patch))
    if dev is not None and pre is None:
        return (*numbers, PHASE["dev"], int(dev))
    if pre is not None:
        # `1.3.0rc1.dev2` is below `1.3.0rc1`; PEP 440 allows the combination even though nothing here
        # writes it.
        return (*numbers, PHASE[pre], int(pre_number), 0 if dev is None else -1, int(dev or 0))
    return (*numbers, PHASE[""], 0)


def base(version: str) -> str | None:
    """The release a version is, or is on the way to: `1.3.0` for both `1.3.0` and `1.3.0.dev4`.

    `None` for a string that is not a version at all, so a caller comparing provenance it cannot read gets
    nothing rather than a guess.
    """
    match = parse(version)
    return None if match is None else ".".join(match.groups()[:3])


def is_release(version: str) -> bool:
    """`1.3.0` and nothing else: no `.dev`, no pre-release segment."""
    match = parse(version)
    return match is not None and match.group(4) is None and match.group(6) is None


def is_snapshot(version: str) -> bool:
    """A `.dev` version: the shape `main` carries, and the only pre-release this factory publishes."""
    match = parse(version)
    return match is not None and match.group(6) is not None


def is_prerelease(version: str) -> bool:
    """Anything an installer would pass over unless told `--pre`: a snapshot, or an `a`/`b`/`rc`."""
    return parse(version) is not None and not is_release(version)


def snapshot(release: str, number: int) -> str:
    """The snapshot `number` commits past `release`'s base: `1.3.0.dev7`."""
    return f"{base(release)}.dev{number}"


def bumped(release: str, level: str) -> str:
    """`release` raised by one bump level: `1.14.2` and MINOR is `1.15.0`.

    The table in `AGENTS.md` as arithmetic, so the number `main` carries can be checked against the claims
    the changes since the last release actually make rather than taken on trust.
    """
    match = parse(release)
    if match is None:
        raise ValueError(f"{release!r} is not a version this factory could have released")
    major, minor, patch = (int(piece) for piece in match.groups()[:3])
    if level == "MAJOR":
        return f"{major + 1}.0.0"
    if level == "MINOR":
        return f"{major}.{minor + 1}.0"
    if level == "PATCH":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"{level!r} is not a bump level: MAJOR, MINOR or PATCH")


def next_snapshot(release: str) -> str:
    """What `main` opens after `release` is cut: the next PATCH, as a snapshot.

    PATCH rather than MINOR because it is the smallest claim — the first change that lands raises it to
    whatever it needs, and a claim made before any change exists is a claim about nothing.
    """
    match = parse(release)
    if match is None:
        raise ValueError(f"{release!r} is not a version this factory could have released")
    major, minor, patch = (int(piece) for piece in match.groups()[:3])
    return f"{major}.{minor}.{patch + 1}.dev0"
