#!/usr/bin/env python3
"""Print the commits the entry being written has to account for, split by whether they reach a user.

The entry is written by hand, one fragment per change in `changelog.d/` — a commit subject says what was
done, and an entry has to say what it means for someone whose project was generated last month — but
*remembering every commit* is not judgement, and that is what this hands over. Run it before writing one:

    python3 scripts/changelog-draft.py            # since the last release
    python3 scripts/changelog-draft.py 1.2.0      # since 1.2.0 was released

The entry it is for is the one for the release `main` is working towards — the base of the snapshot in
`VERSION`, `1.3.0` for `1.3.0.dev0` — and everything since the last tag belongs to it. The split mirrors
the one `AGENTS.md` decides the level by: a commit touching `assets/`, `catalog.json`, `src/slipwai/` or the
CLI reached a user and belongs in the entry; a commit touching only `tests/`, `docs/`, `scripts/` or the
repository's own files did not, and is listed under a second heading so leaving it out is a decision rather
than an oversight. The fragments already written are listed with the number they add up to, so a commit
accounted for by one of them is visible as such. Nothing here writes a fragment: what an entry says is the
author's.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slipwai.changelog import fragments, level  # noqa: E402 — after the path that makes it importable
from slipwai.versions import base  # noqa: E402 — after the path that makes it importable

# What makes a change user-visible, from AGENTS.md's versioning rule. A path outside these reaches whoever
# works on the factory and nobody who runs it. `VERSION` is not in the list: the release script's own two
# commits touch nothing else, and a change that raises the number does so beside the change that needs it.
USER_VISIBLE = ("assets/", "catalog.json", "src/slipwai/")


def git(*arguments: str) -> str:
    done = subprocess.run(["git", "-C", str(ROOT), *arguments], text=True, capture_output=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"changelog-draft: git {' '.join(arguments)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def version_commits() -> list[tuple[str, str]]:
    """Every commit that changed `VERSION`, newest first, as (sha, the version it set)."""
    found = []
    for sha in git("log", "--format=%H", "--", "VERSION").splitlines():
        version = git("show", f"{sha}:VERSION")
        found.append((sha, version.strip()))
    return found


def release_tags() -> list[str]:
    """Every `v*` tag this history has, newest first."""
    return git("tag", "--list", "v*", "--sort=-v:refname").split()


def since(version: str | None) -> tuple[str, str]:
    """The commit to list from, and how to describe it: the last release, or the release of `version`.

    A version this history has an entry for but never tagged — the numbers spent before releases were cut
    from snapshots, or one whose tag is not fetched here — is found by the commit that set `VERSION` to it,
    so the older history stays readable.
    """
    tags = release_tags()
    if version is None:
        if tags:
            return tags[0], f"the release {tags[0]}"
        bumps = version_commits()
        if not bumps:
            raise SystemExit("changelog-draft: no release tag and no commit that changed VERSION in this history")
        sha, was = bumps[0]
        return sha, f"the commit that set VERSION to {was}"
    if f"v{version}" in tags:
        return f"v{version}", f"the release v{version}"
    for sha, was in version_commits():
        if was == version:
            return sha, f"the commit that set VERSION to {was}"
    known = ", ".join(dict.fromkeys([*(tag.lstrip("v") for tag in tags), *(was for _sha, was in version_commits())]))
    raise SystemExit(
        f"changelog-draft: no v{version} tag and no commit set VERSION to {version} (this history has: {known})"
    )


def touched(sha: str) -> list[str]:
    return git("show", "--name-only", "--format=", sha).splitlines()


def reaches_a_user(sha: str) -> bool:
    return any(path.startswith(USER_VISIBLE) for path in touched(sha) if path)


def main(argv: list[str]) -> int:
    if len(argv) > 1 or (argv and argv[0].startswith("-")):
        print(__doc__, file=sys.stderr)
        return 2
    start, described = since(argv[0] if argv else None)
    written = (ROOT / "VERSION").read_text().strip()
    # The entry is the release's, not the snapshot's: `1.3.0` for a VERSION of `1.3.0.dev0`.
    current = base(written) or written
    landed = git("log", "--format=%H %s", "--no-merges", f"{start}..HEAD").splitlines()
    commits = [line.split(" ", 1) for line in landed]
    # The moment this is most useful is while a bump is being prepared, which is a moment with uncommitted
    # work in the tree — so say that rather than let "nothing has landed" read as "nothing has changed".
    dirty = "\n  (this working tree has uncommitted changes, which are not commits and so are not listed)" \
        if git("status", "--porcelain") else ""
    if not commits:
        print(f"VERSION is {written}, and nothing has landed since {described}.{dirty}")
        print(written_so_far())
        return 0

    visible = [(sha, subject) for sha, subject in commits if reaches_a_user(sha)]
    internal = [(sha, subject) for sha, subject in commits if (sha, subject) not in visible]
    print(f"VERSION is {written}. {len(commits)} commit(s) since {described}.{dirty}\n")
    print(f"## Reached a user — belongs in the {current} entry\n")
    for sha, subject in visible or [("", "(none)")]:
        print(f"- {subject}" + (f"  [{sha[:7]}]" if sha else ""))
    print("\n## Did not — say so only if it changes what the entry means\n")
    for sha, subject in internal or [("", "(none)")]:
        print(f"- {subject}" + (f"  [{sha[:7]}]" if sha else ""))
    print(written_so_far())
    print(
        f"\nWrite a fragment in changelog.d/ for the {current} entry — the release VERSION is a snapshot of —"
        "\nwith its bump level on the first line and, where the change asks anything of a repository already"
        "\ngenerated, what that is. changelog.d/README.md has the shape."
    )
    return 0


def written_so_far() -> str:
    """The fragments already in `changelog.d/`, and the release they add up to claiming.

    Listed because a commit above may already be accounted for by one of them, and because the number they
    imply is the one `main` has to carry — seeing both at once is how that is noticed before the gate says it.
    """
    found = fragments(ROOT)
    if not found:
        return "\nNothing is written in changelog.d/ yet."
    entered = "\n".join(f"- {path.name}  [{claim or 'no level'}]" for path, claim, _body in found)
    return f"\nWritten in changelog.d/ so far, claiming a {level(found)} in total:\n{entered}"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
