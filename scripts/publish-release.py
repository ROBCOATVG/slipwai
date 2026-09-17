#!/usr/bin/env python3
"""Attach the built release archives to a tag's release on the forge, through the forge's own API.

This is what `.github/workflows/package.yml` finishes a release with, and it is written here rather than as
three lines of shell because the obvious three lines were wrong twice. `gh release upload` is GitHub's
client: it is not installed on this forge's runner image — a release fails at `gh: command not found` with
the archives already built and uploaded as a workflow artifact — and it would not work if it were, because
Gitea serves its own releases API rather than GitHub's. So the upload talks to the forge directly.

    GITEA_TOKEN=... publish-release.py --api <forge>/api/v1 --repository OWNER/NAME --tag v1.6.1 release/*

Three things it will not do, each of them the mistake this repository cannot take back:

- **Create a tag.** Gitea's `POST /releases` accepts a `tag_name` that does not exist yet and *makes* it,
  pointing at the default branch — a tag invented by CI, naming a commit nobody released. So the tag is
  looked up first and a missing one is refused. This is `gh release create --verify-tag`, and it matters
  more here than there, because [AGENTS.md](../AGENTS.md) turns on tags never moving.
- **Attach the same archive twice.** Gitea allows two attachments with one name, so a rerun would leave a
  release holding `slipwai-linux-x86_64.tar.gz` twice with no way for a reader to tell which is the one the
  `.sha256` beside it describes. An asset whose name is already there is deleted and replaced.
- **Compose release notes.** There is no `--generate-notes` to reach for and no need for one: `CHANGELOG.md`
  carries the entry for this version, `scripts/tag-release.py` already refuses a release without one, and
  the tag's own message is read from the same place. The notes are that entry, verbatim.

Rerunning it for a release that is already complete is the intended way to use it, and does nothing.

**The snapshot is the one exception to the first refusal, and it is the whole of the exception.** Every
green push to `main` publishes the executable built from it as a pre-release the forge shows under the tag
`snapshot`, replaced each time:

    GITEA_TOKEN=... publish-release.py --api <forge>/api/v1 --repository OWNER/NAME \\
        --snapshot 1.13.0.dev7 --commit <sha> release/*

`snapshot` is not a release tag — nothing matches `v*` on it, nothing is built *from* it, and no version is
spent by it — it is only how the forge hangs assets on a commit. So here the release *and* the tag are
deleted and made again at the commit named, which is the one thing this script does to a `v*` tag under no
circumstances. Between the delete and the create there is briefly no snapshot to download; the previous one
being wrong for a while would be worse.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

FACTORY = Path(__file__).resolve().parents[1]
# `## 1.6.0 — MINOR`, the shape `tests/test_changelog.py` holds every entry to and `tag-release.py` reads the
# tag's message from. Spelled the same in both places on purpose: the entry is one thing with two readers.
ENTRY = re.compile(r"(?m)^## (\d+\.\d+\.\d+)(?: — (?:MAJOR|MINOR|PATCH))?$")
TIMEOUT = 60


# The tag the rolling snapshot of `main` hangs on. Deliberately not a version and not `v`-anything: the
# release workflows, `test-migration` and `changelog-draft` all look at `v*` and must never see this one.
SNAPSHOT_TAG = "snapshot"


class ReleaseError(RuntimeError):
    pass


class Forge:
    """The forge's releases API, with the token in a header and every refusal quoted.

    The proxy handler is emptied for the same reason `publish-wheel.py` empties it: a runner may carry proxy
    variables aimed at the internet, and the forge is not on the internet.
    """

    def __init__(self, api_url: str, token: str) -> None:
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def open(self, request: urllib.request.Request, what: str) -> bytes:
        request.add_header("Authorization", f"token {self.token}")
        # Named, because a proxy fronting the forge bans the default `Python-urllib/3.x` agent.
        request.add_header("User-Agent", "slipwai-publish")
        request.add_header("Accept", "application/json")
        try:
            with self.opener.open(request, timeout=TIMEOUT) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:400]
            raise ReleaseError(f"{what} failed ({error.code}): {detail}") from error
        except urllib.error.URLError as error:
            raise ReleaseError(f"cannot reach the forge at {self.api_url}: {error.reason}") from error

    def json(self, method: str, path: str, payload: dict[str, object] | None = None) -> dict | list:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(f"{self.api_url}{path}", data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        body = self.open(request, f"{method} {path}")
        return json.loads(body) if body else {}

    def found(self, path: str) -> dict | None:
        """A `GET` whose 404 is an answer rather than a failure: what is there, or `None`."""
        try:
            result = self.json("GET", path)
        except ReleaseError as error:
            if "(404)" in str(error):
                return None
            raise
        return result if isinstance(result, dict) else None

    def upload(self, path: str, file: Path) -> None:
        """`POST` one file as `multipart/form-data`, the only shape the attachments endpoint takes.

        Hand-rolled because this repository's scripts depend on nothing but the standard library, and the
        body is read whole rather than streamed: a release archive is tens of megabytes, which is a
        reasonable thing to hold and an unreasonable thing to add a dependency for.
        """
        boundary = f"----slipwai{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        body = b"".join(
            [
                f'--{boundary}\r\nContent-Disposition: form-data; name="attachment"; '
                f'filename="{file.name}"\r\nContent-Type: {content_type}\r\n\r\n'.encode(),
                file.read_bytes(),
                f"\r\n--{boundary}--\r\n".encode(),
            ]
        )
        request = urllib.request.Request(f"{self.api_url}{path}", data=body, method="POST")
        request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        self.open(request, f"POST {path}")


def notes(repository: Path, version: str) -> str:
    """The changelog's entry for this version: everything under its heading, up to the next one.

    Empty when there is no such entry, which is not refused here. `tag-release.py` is where a release
    without an entry is stopped, and it is stopped before the tag exists; by the time this runs the tag is
    pushed and the archives are built, and failing now would leave a release nobody can download over a file
    somebody can still edit.
    """
    changelog = repository / "CHANGELOG.md"
    if not changelog.is_file():
        return ""
    text = changelog.read_text()
    headings = list(ENTRY.finditer(text))
    for index, heading in enumerate(headings):
        if heading.group(1) != version:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        return text[heading.end() : end].strip()
    return ""


def release_for(forge: Forge, repository: str, tag: str, body: str) -> dict:
    """The release for this tag, made if the forge has not got one — never the tag itself.

    A release the forge already has is left exactly as it is, including its notes: a rerun exists to finish
    an upload, and rewriting the description of a release somebody may have already edited is not part of
    that.
    """
    existing = forge.found(f"/repos/{repository}/releases/tags/{urllib.parse.quote(tag)}")
    if existing is not None:
        print(f"release exists: {tag}")
        return existing
    if forge.found(f"/repos/{repository}/tags/{urllib.parse.quote(tag)}") is None:
        raise ReleaseError(
            f"{repository} has no tag {tag}, and this will not make one: the releases API would create it "
            f"pointing at the default branch, which is a tag invented by CI naming a commit nobody "
            f"released. Push the tag first (`make release`)"
        )
    created = forge.json(
        "POST", f"/repos/{repository}/releases", {"tag_name": tag, "name": tag, "body": body}
    )
    if not isinstance(created, dict):
        raise ReleaseError(f"the forge answered a release creation for {tag} with {type(created).__name__}")
    print(f"release created: {tag}")
    return created


def snapshot_release(forge: Forge, repository: str, version: str, commit: str) -> dict:
    """The `snapshot` pre-release remade at `commit`: the old release and its tag gone, a new one in their place.

    Remade rather than edited because a release's tag is where it points, and a tag cannot be pointed
    elsewhere through the releases API — only deleted and made again. Gitea's `POST /releases` makes the tag
    at `target_commitish` when it does not exist, which is the behaviour refused for a `v*` tag above and
    relied on here for the one tag that is not a release.
    """
    quoted = urllib.parse.quote(SNAPSHOT_TAG)
    existing = forge.found(f"/repos/{repository}/releases/tags/{quoted}")
    if existing is not None and isinstance(existing.get("id"), int):
        forge.json("DELETE", f"/repos/{repository}/releases/{existing['id']}")
        print(f"removed the previous snapshot release ({existing.get('name', SNAPSHOT_TAG)})")
    if forge.found(f"/repos/{repository}/tags/{quoted}") is not None:
        forge.json("DELETE", f"/repos/{repository}/tags/{quoted}")
        print(f"removed the previous {SNAPSHOT_TAG} tag")
    created = forge.json(
        "POST", f"/repos/{repository}/releases",
        {
            "tag_name": SNAPSHOT_TAG,
            "target_commitish": commit,
            "name": f"slipwai {version} (snapshot of main)",
            "prerelease": True,
            "body": (
                f"The executable built from `main` at {commit}, published because every verify job passed "
                f"there. Replaced on the next green push; not a release, and not what `slipwai upgrade` "
                f"offers unless asked with `--pre`. The releases are the `v*` tags."
            ),
        },
    )
    if not isinstance(created, dict):
        raise ReleaseError(f"the forge answered the snapshot release creation with {type(created).__name__}")
    print(f"snapshot release created: {version} at {commit[:12]}")
    return created


def attach(forge: Forge, repository: str, release: dict, files: list[Path]) -> None:
    """Every file uploaded to the release, replacing one already there under the same name."""
    identifier = release.get("id")
    if not isinstance(identifier, int):
        raise ReleaseError(f"the forge's release for this tag has no id: {release!r}")
    assets = release.get("assets")
    held = {
        asset["name"]: asset["id"]
        for asset in (assets if isinstance(assets, list) else [])
        if isinstance(asset, dict) and isinstance(asset.get("name"), str)
    }
    for file in files:
        if file.name in held:
            forge.json("DELETE", f"/repos/{repository}/releases/{identifier}/assets/{held[file.name]}")
            print(f"replacing: {file.name}")
        forge.upload(
            f"/repos/{repository}/releases/{identifier}/assets?name={urllib.parse.quote(file.name)}", file
        )
        print(f"attached: {file.name} ({file.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--api", required=True, help="the forge's API root: <forge>/api/v1")
    parser.add_argument("--repository", required=True, help="OWNER/NAME on that forge")
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--tag", help="the release tag to attach them to, which must already exist")
    what.add_argument(
        "--snapshot", metavar="VERSION",
        help=f"replace the rolling `{SNAPSHOT_TAG}` pre-release with this snapshot of main (needs --commit)",
    )
    parser.add_argument("--commit", help="the commit of main a --snapshot was built from")
    parser.add_argument(
        "--changelog-from", type=Path, default=FACTORY,
        help="the checkout whose CHANGELOG.md the notes are read from (default: this one)",
    )
    parser.add_argument("files", nargs="+", type=Path, help="the archives and checksums to attach")
    args = parser.parse_args()
    if args.snapshot and not args.commit:
        parser.error("--snapshot needs --commit: the snapshot tag is made at the commit the archives were built from")

    token = os.environ.get("GITEA_TOKEN")
    if not token:
        raise ReleaseError("GITEA_TOKEN must be set in the environment, not passed on the command line")
    missing = [str(file) for file in args.files if not file.is_file()]
    if missing:
        raise ReleaseError(f"nothing to attach at: {', '.join(missing)}")
    # Sorted so a release lists its archives in the same order every time, whatever order the shell's glob or
    # the artifact download happened to hand over.
    files = sorted(args.files, key=lambda file: file.name)

    forge = Forge(args.api, token)
    repository = args.repository.strip("/")
    if args.snapshot:
        release = snapshot_release(forge, repository, args.snapshot, args.commit)
        named = f"the {SNAPSHOT_TAG} of main, {args.snapshot},"
    else:
        release = release_for(forge, repository, args.tag, notes(args.changelog_from, args.tag.lstrip("v")))
        named = args.tag
    attach(forge, repository, release, files)
    url = release.get("html_url")
    print(f"\n{named} is downloadable: {url}" if isinstance(url, str) else f"\n{named} is complete")


if __name__ == "__main__":
    try:
        main()
    except (ReleaseError, OSError) as error:
        print(f"publish-release: {error}", file=sys.stderr)
        # The message above is the whole diagnosis; a traceback would bury it.
        raise SystemExit(1) from None
