#!/usr/bin/env python3
"""Cut the release: turn the snapshot `main` carries into a release, tag it, and open the next snapshot.

`main` carries `1.3.0.dev0` — the release it is working towards, marked as not there yet. Cutting the
release is three commits' worth of work and one push:

    Release 1.3.0        VERSION 1.3.0.dev0 → 1.3.0, changelog.d/ assembled into the entry, tagged v1.3.0
    Open 1.3.1.dev0      VERSION 1.3.0 → 1.3.1.dev0, marked `[skip ci]`
    git push --atomic <remote> main v1.3.0

The tag is the trigger — `.github/workflows/package.yml` builds and attaches the Linux executable,
`.github/workflows/publish-package.yml` builds the wheel, proves it scaffolds and uploads it to the forge's
PyPI registry — and the push of `main` is what makes the next green snapshot `1.3.1.dev1` rather than a
second `1.3.0`. Nothing here builds anything; the whole job of this script is to refuse the pushes that
would be wrong.

    python3 scripts/tag-release.py --dry-run    # every check, and what it would do
    python3 scripts/tag-release.py              # commit, tag, commit, push

There is exactly one thing a release cannot recover from, and it is the reason for every check below: a
name and version can be uploaded to the registry once, and a tag that has been fetched must never move. So
a version is spent the moment it is pushed, and being sure *before* the push is the only place the care can
go — the checkout is on `main`, clean, and at the same commit the forge has (which is the commit
`verify.yml` gave a verdict on); `VERSION` is a snapshot, and the release it is a snapshot of is the one the
fragments in `changelog.d/` say it is; and neither the local repository nor the forge already knows this tag.

The entry is assembled by the `Release` commit rather than written by hand into `CHANGELOG.md` while the
version is in flight — `changelog.d/README.md` says why — so that commit carries `VERSION`, the entry it
just made, and the fragments it consumed, and the tag names the verified commit plus prose already reviewed
in the branches that wrote it. The `Open` commit then touches `VERSION` alone: the next entry is an empty
`changelog.d/`, which needs no placeholder to be true.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slipwai.changelog import entry, fragments, implied, level  # noqa: E402 — needs the path
from slipwai.versions import base, is_release, is_snapshot, next_snapshot  # noqa: E402 — needs the path

# Where the forge is, in the order a checkout is likely to name it: `publish-to-gitea.py` adds `gitea`, and
# a clone of what it pushed calls the same thing `origin`. Neither is assumed — `--remote` names another,
# and a checkout with no forge remote at all is told which ones it does have.
REMOTES = ("gitea", "origin")
# `## 1.6.0 — MINOR`, the shape `tests/test_changelog.py` holds every entry to.
ENTRY = re.compile(r"(?m)^## (\d+\.\d+\.\d+)(?: — (MAJOR|MINOR|PATCH))?$")
# The forge creates no run for a push whose commit message holds this, and the `Open` commit is one to skip.
# It raises `VERSION` and touches nothing else, on a tree `verify.yml` has just passed at the tag beneath it;
# running the whole gate again would prove the same thing an hour more slowly and publish a `.dev1` snapshot
# of code identical to the release beside it. The next change to `main` is verified as itself.
#
# Gitea matches it anywhere in the message rather than in the first lines as GitHub does, which is why it can
# go in the body — and why a commit message that only *mentions* the marker skips its own run. `publishing.md`
# says so where somebody writing one would read it.
SKIP_CI = "[skip ci]"


class ReleaseError(RuntimeError):
    pass


def git(repo: Path, *arguments: str, environment: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments], text=True, capture_output=True, env=environment
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ReleaseError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout.strip()


def push_environment() -> dict[str, str] | None:
    """The non-interactive authentication `publish-to-gitea.py` uses, when there is a token to use it with.

    `None` when there is not, which is not an error: a checkout may push over SSH or through a credential
    helper, and refusing those because one environment variable is unset would be inventing a requirement.
    """
    token, username = os.environ.get("GITEA_TOKEN"), os.environ.get("GITEA_USERNAME")
    if not token:
        return None
    return os.environ | {
        "GIT_ASKPASS": str(ROOT / "scripts/gitea-askpass"),
        "GIT_TERMINAL_PROMPT": "0",
        "GITEA_USERNAME": username or os.environ.get("GITEA_OWNER", ""),
        "GITEA_TOKEN": token,
    }


def entries(repo: Path) -> list[tuple[str, str | None]]:
    return [(match.group(1), match.group(2)) for match in ENTRY.finditer((repo / "CHANGELOG.md").read_text())]


def announced(repo: Path, release: str) -> str:
    """The heading this release's entry will carry, which becomes the tag's message.

    The level is not composed here either: it is the highest claim the fragments make, so the tag, the entry
    and the number `main` carries are one fact with three readers rather than three answers to one question.
    The number is held to that claim — a MINOR among the fragments and a `VERSION` that only raised the
    PATCH is a release understating what it contains, and it is cheaper to say so now than after the push.
    """
    found = fragments(repo)
    if not found:
        raise ReleaseError(
            "changelog.d/ has no fragment, so nothing says what this release changed. An entry is written "
            "while the version is in flight, by the commits that make the changes, and a release nobody can "
            "read the meaning of is not one"
        )
    unstated = [path.name for path, claim, _body in found if claim is None]
    if unstated:
        raise ReleaseError(
            f"these fragments do not open with a bump level (PATCH, MINOR or MAJOR alone on the first "
            f"line): {', '.join(unstated)}"
        )
    released = entries(repo)
    if not released:
        if release != "1.0.0":
            raise ReleaseError(
                f"CHANGELOG.md has no released entries: only the first public release may start from "
                f"nothing, and that release is 1.0.0 rather than {release}"
            )
        return "slipwai 1.0.0"
    wanted = implied(released[0][0], found)
    if wanted != release:
        raise ReleaseError(
            f"the fragments in changelog.d/ claim a {level(found)} over {released[0][0]}, which is {wanted}, "
            f"but VERSION is a snapshot of {release}. The number main carries is the claim its changes make "
            f"— raise or lower one of the two before cutting anything"
        )
    return f"slipwai {release} — {level(found)}"


def cut_entry(repo: Path, release: str) -> list[str]:
    """Assemble the fragments into the entry above the newest one, and return the paths the commit carries.

    The fragments are removed by the same commit that publishes what they said: a file left behind here
    would be read as part of the next entry and go out twice.
    """
    changelog = repo / "CHANGELOG.md"
    text = changelog.read_text()
    newest = ENTRY.search(text)
    found = fragments(repo)
    if newest is None:
        changelog.write_text(text.rstrip() + "\n\n" + entry(release, found, first=True))
    else:
        changelog.write_text(text[: newest.start()] + entry(release, found) + text[newest.start() :])
    for path, _claim, _body in found:
        # Removed from the worktree alone: the index still has the entry, which is what lets the commit stage
        # the deletion by naming the path like any other change it carries.
        path.unlink()
    return ["CHANGELOG.md", *(path.relative_to(repo).as_posix() for path, _claim, _body in found)]


def web_url(remote_url: str) -> str:
    """The forge address a person can open, from the URL git pushes to: no credentials, no `.git`."""
    address = remote_url.removesuffix(".git")
    if address.startswith("git@"):
        host, _, path = address.partition(":")
        return f"https://{host.removeprefix('git@')}/{path}"
    scheme, _, rest = address.partition("://")
    return f"{scheme}://{rest.rpartition('@')[2]}" if scheme else address


def forge_remote(repo: Path, named: str | None) -> str:
    """The remote to push to: the one named, or the first of `REMOTES` this checkout has."""
    remotes = git(repo, "remote").splitlines()
    if named is not None:
        if named not in remotes:
            raise ReleaseError(f'no "{named}" remote in this checkout; it has: {", ".join(remotes) or "none"}')
        return named
    for candidate in REMOTES:
        if candidate in remotes:
            return candidate
    raise ReleaseError(
        f"this checkout has no {' or '.join(REMOTES)} remote to push a tag to (it has: "
        f'{", ".join(remotes) or "none"}). `python3 scripts/publish-to-gitea.py` adds one, or name another '
        f"with --remote"
    )


def version_at(repo: Path, revision: str) -> str:
    return git(repo, "show", f"{revision}:VERSION").strip()


def touched(repo: Path, revision: str) -> set[str]:
    return set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", revision).split())


def released_here(repo: Path, revision: str) -> bool:
    """A `Release` commit of this script's: `VERSION`, the entry it assembled, the fragments it consumed —
    or `VERSION` alone, the shape every run before the entry was assembled here left."""
    files = touched(repo, revision)
    if files == {"VERSION"}:
        return True
    rest = files - {"VERSION", "CHANGELOG.md"}
    return {"VERSION", "CHANGELOG.md"} <= files and all(path.startswith("changelog.d/") for path in rest)


def opened_here(repo: Path, revision: str) -> bool:
    """An `Open` commit of this script's: `VERSION` alone — or `VERSION` and the changelog, the shape every
    run that opened a placeholder entry left."""
    return touched(repo, revision) in ({"VERSION"}, {"VERSION", "CHANGELOG.md"})


def unfinished(repo: Path, remote_main: str, head: str) -> str | None:
    """The release an earlier run made here and never pushed, or `None` when this is a fresh cut.

    An earlier run whose push failed leaves exactly this behind: `HEAD` is its `Open` commit, `HEAD~1` its
    `Release` commit with the tag on it, `HEAD~2` what the forge still has, the `Release` commit touched
    `VERSION`, the changelog and the fragments it consumed, and the `Open` commit `VERSION` alone. Anything
    else two commits ahead of the forge is somebody's work, and is refused.
    """
    try:
        if git(repo, "rev-parse", "HEAD~2") != remote_main:
            return None
    except ReleaseError:
        return None
    release_commit = git(repo, "rev-parse", "HEAD~1")
    release = version_at(repo, release_commit)
    tagged = git(repo, "tag", "--points-at", release_commit).split()
    if (
        is_release(release)
        and f"v{release}" in tagged
        and version_at(repo, head) == next_snapshot(release)
        and opened_here(repo, head)
        and released_here(repo, release_commit)
    ):
        return release
    return None


def preflight(repo: Path, remote: str) -> tuple[str, str | None]:
    """Everything that has to be true before anything is written, refused one reason at a time.

    Returns the remote's URL, which the report at the end is written from, and the release an earlier run
    left unpushed here when this run is finishing that one rather than starting another.
    """
    branch = git(repo, "branch", "--show-current")
    if branch != "main":
        raise ReleaseError(f"on branch {branch or 'a detached HEAD'}: a release is cut from main")
    dirty = git(repo, "status", "--porcelain=v1")
    if dirty:
        raise ReleaseError(
            "the checkout has uncommitted changes, so the tag would name a commit that is not what you "
            f"have been running:\n{dirty}"
        )
    remote_url = git(repo, "remote", "get-url", remote)
    environment = push_environment()
    head = git(repo, "rev-parse", "HEAD")
    remote_main = git(repo, "ls-remote", remote, "refs/heads/main", environment=environment).partition("\t")[0]
    if not remote_main:
        raise ReleaseError(f"{remote} has no main branch to release from; push it first")
    resumed = unfinished(repo, remote_main, head) if remote_main != head else None
    if remote_main != head and resumed is None:
        raise ReleaseError(
            f"{remote}/main is at {remote_main[:12]} and this checkout at {head[:12]}: push or pull main "
            f"first. The tag has to name a commit the forge has — it is what the release workflows check "
            f"out, and what verify.yml has already given a verdict on"
        )
    return remote_url, resumed


def spent(repo: Path, remote: str, tag: str, at: str | None) -> None:
    """Refuse a tag the forge already has, or a local one that names a commit other than `at`."""
    if git(repo, "ls-remote", remote, f"refs/tags/{tag}", environment=push_environment()):
        raise ReleaseError(
            f"{remote} already has {tag}: a released version is spent — the registry takes a name and "
            f"version once, and a tag that has been fetched must never move. The entry and the snapshot "
            f"have to move on to the next number before it can be cut"
        )
    local = git(repo, "tag", "--list", tag)
    if local and git(repo, "rev-parse", f"{tag}^{{commit}}") != at:
        raise ReleaseError(
            f"{tag} already exists in this checkout and names a different commit. Delete it "
            f"(`git tag -d {tag}`) if it was a mistake; never move it if anybody has fetched it"
        )


def commit_version(repo: Path, version: str, subject: str, *also: str) -> str:
    (repo / "VERSION").write_text(f"{version}\n")
    # `--all` over the named paths and no others: a fragment the entry consumed is staged as the deletion it
    # is, where a bare `add` would refuse a path that is no longer on disk.
    git(repo, "add", "--all", "--", "VERSION", *also)
    git(repo, "commit", "--quiet", "--only", "VERSION", *also, "--message", subject)
    return git(repo, "rev-parse", "--short", "HEAD")


def report(forge: str, remote: str, tag: str, release: str, opened: str) -> str:
    return (
        f"pushed: main and {tag} to {remote}\n"
        f"main now carries {opened}; its next green push publishes the first snapshot of it.\n"
        f"\nThe forge builds the artifacts from here — watch {forge}/actions:\n"
        f"  package executables   → the Linux archive and its .sha256, attached to {forge}/releases/"
        f"tag/{tag}\n"
        f"  publish package       → the wheel, proved to scaffold, uploaded to this forge's PyPI registry\n"
        f"\nWhen both are green, `slipwai upgrade` finds {release} and every installed copy can take it."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--remote", default=None,
        help=f"the remote to push to (default: whichever of {', '.join(REMOTES)} this checkout has)",
    )
    parser.add_argument(
        "--repository", type=Path, default=ROOT,
        help="the checkout to release (default: this one)",
    )
    parser.add_argument("--dry-run", action="store_true", help="run every check and write nothing")
    args = parser.parse_args()

    repo = args.repository.resolve()
    if not (repo / ".git").is_dir():
        raise ReleaseError(f"{repo} is not a git checkout, so there is nothing here to tag")
    remote = forge_remote(repo, args.remote)
    # The checkout is held to its shape before VERSION is read, so a dirty tree is reported as a dirty tree
    # rather than as whatever the half-finished edit did to `VERSION`.
    remote_url, resumed = preflight(repo, remote)
    forge = web_url(remote_url)
    written = (repo / "VERSION").read_text().strip()

    if resumed is not None:
        # Made by an earlier run whose push failed: preflight proved the two commits are this script's own
        # and the tag is on the right one, so pushing them is finishing that run rather than starting another.
        tag = f"v{resumed}"
        spent(repo, remote, tag, git(repo, "rev-parse", "HEAD~1"))
        if args.dry_run:
            print(f"would push: main and {tag} to {remote} ({forge}) — made by an earlier run, never pushed")
            return
        print(f"release already made here: {tag}, and main has opened {written}")
        git(repo, "push", "--atomic", remote, "main", tag, environment=push_environment())
        print(report(forge, remote, tag, resumed, written))
        return

    if not is_snapshot(written):
        raise ReleaseError(
            f"VERSION is {written}, which is not a snapshot: main carries the release it is working towards "
            f"as `<version>.dev0`, and cutting it is what turns that into a release. Write "
            f"`{base(written) or written}.dev0` if this number has not been released, or the next one if it "
            f"has — the entry in CHANGELOG.md goes with it"
        )
    release = base(written)
    assert release is not None
    tag = f"v{release}"
    opened = next_snapshot(release)
    spent(repo, remote, tag, None)
    message = announced(repo, release)

    written_up = fragments(repo)
    if args.dry_run:
        at = git(repo, "rev-parse", "--short", "HEAD")
        assembled = ", ".join(path.name for path, _claim, _body in written_up)
        heading = release if not entries(repo) else f"{release} — {level(written_up)}"
        print(f"would commit: Release {release} (VERSION {written} → {release}) on {at}")
        print(f"would assemble: `## {heading}` in CHANGELOG.md from {assembled}")
        print(f"would tag: {tag} ({message}) at that commit")
        print(f"would commit: Open {opened} (VERSION {release} → {opened}, {SKIP_CI})")
        print(f"would push: main and {tag} to {remote} ({forge})")
        return

    carried = cut_entry(repo, release)
    released_at = commit_version(repo, release, f"Release {release}\n\n{message}", *carried)
    print(f"committed: Release {release} ({released_at}), with the entry assembled from {len(written_up)} fragment(s)")
    git(repo, "tag", "--annotate", tag, "--message", message)
    print(f"tagged: {tag} ({message})")
    opened_at = commit_version(
        repo, opened,
        f"Open {opened}\n\nThe next snapshot, after {release} was cut; changelog.d/ is empty again.\n\n{SKIP_CI}",
    )
    print(f"committed: Open {opened} ({opened_at})")
    # One push, all or nothing: a tag on the forge with main still at the `Release` commit is a main whose
    # next change has no snapshot number to land under, and a main that has moved on without its tag is a
    # release nobody can install.
    git(repo, "push", "--atomic", remote, "main", tag, environment=push_environment())
    print(report(forge, remote, tag, release, opened))


if __name__ == "__main__":
    try:
        main()
    except (ReleaseError, OSError) as error:
        print(f"release failed: {error}", file=sys.stderr)
        # The message above is the whole diagnosis; a traceback would bury it.
        raise SystemExit(1) from None
