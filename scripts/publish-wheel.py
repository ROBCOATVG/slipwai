#!/usr/bin/env python3
"""Upload the built package to a PyPI-compatible registry, skipping files it already holds.

twine refuses `--skip-existing` for any repository that is not PyPI itself, and a Gitea registry refuses a
file it already has — so a rerun of the publish workflow for a tag that already published would fail on the
upload it does not need. This reads the registry's simple index first and hands twine only what is missing.
The upload endpoint and simple index may be named separately because PyPI serves them on different hosts.

The same index says which snapshots are now behind what was just uploaded. A snapshot of `main` is published
as `1.3.0.dev<N>` on every green push, and the registry takes a name and version once, so "the snapshot is
replaced" has to mean: upload the new number, then delete every `.dev` version below it. After the upload,
never before, so a publish that fails leaves the previous snapshot installable rather than nothing. A release
retires the snapshots that led to it the same way — and never a release. PyPI has no equivalent package API,
so uniquely numbered development releases remain available there.

usage: PYPI_TOKEN=... publish-wheel.py --url <upload> --index-url <simple> --user <login> [files...]
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

FACTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FACTORY / "src"))

from slipwai.versions import is_snapshot, key  # noqa: E402 — after the path that makes it importable

VERSION = (FACTORY / "VERSION").read_text().strip()
PACKAGE = "slipwai"


def held(index_url: str, user: str, token: str, *, authenticate: bool) -> set[str]:
    """The file names the registry's simple index lists for this package; none when it has no such package."""
    headers = {"User-Agent": "slipwai-publish"}
    if authenticate:
        credentials = base64.b64encode(f"{user}:{token}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    request = urllib.request.Request(index_url, headers=headers)
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=30) as response:
            page = response.read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return set()
        detail = error.read().decode(errors="replace")[:200]
        raise SystemExit(f"publish-wheel: {index_url} answered {error.code}: {detail}") from error
    return {href.rsplit("/", 1)[-1].split("#", 1)[0] for href in re.findall(r'href="([^"]+)"', page)}


def versions_of(filenames: set[str]) -> set[str]:
    """The versions a set of `slipwai-1.6.0-py3-none-any.whl` / `slipwai-1.6.0.tar.gz` names are of."""
    found = set()
    for name in filenames:
        if name.endswith(".whl"):
            found.add(name.split("-")[1])
        elif name.endswith(".tar.gz"):
            found.add(name[: -len(".tar.gz")].split("-")[-1])
    return found


def superseded(held_versions: set[str], published: str) -> list[str]:
    """The snapshots `published` retires: every `.dev` version below it, oldest first. Never a release."""
    return sorted(
        (version for version in held_versions if is_snapshot(version) and key(version) < key(published)),
        key=key,
    )


def retire(url: str, user: str, token: str, versions: list[str]) -> None:
    """Delete package versions through the forge's API: `DELETE /api/v1/packages/<owner>/pypi/<name>/<v>`.

    The registry URL is `<forge>/api/packages/<owner>/pypi`; the packages API is a sibling of it under
    `/api/v1`, and the owner is the same segment. Authenticated the way the index was read, with the token
    the upload used — the same `write:package` scope covers both.
    """
    forge, _, rest = url.partition("/api/packages/")
    owner = rest.split("/", 1)[0]
    if not forge or not owner:
        raise SystemExit(
            f"publish-wheel: cannot tell the forge and owner from {url}; expected <forge>/api/packages/<owner>/pypi"
        )
    credentials = base64.b64encode(f"{user}:{token}".encode()).decode()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for version in versions:
        request = urllib.request.Request(
            f"{forge}/api/v1/packages/{owner}/pypi/{PACKAGE}/{version}", method="DELETE",
            headers={"Authorization": f"Basic {credentials}", "User-Agent": "slipwai-publish"},
        )
        try:
            with opener.open(request, timeout=30):
                pass
        except urllib.error.HTTPError as error:
            if error.code == 404:
                # Gone already — a rerun, or two publishes racing; either way what this wanted is true.
                continue
            detail = error.read().decode(errors="replace")[:200]
            raise SystemExit(f"publish-wheel: deleting {PACKAGE} {version} answered {error.code}: {detail}") from error
        print(f"retired snapshot: {version}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="the repository upload endpoint")
    parser.add_argument(
        "--index-url",
        help="the PEP 503 index root (default: <url>/simple, for Gitea)",
    )
    parser.add_argument("--user", required=True, help="the login the token belongs to")
    parser.add_argument("files", nargs="*", type=Path, help=f"default: dist/{PACKAGE}-{VERSION}*")
    args = parser.parse_args()
    token = os.environ.get("PYPI_TOKEN")
    if not token:
        raise SystemExit("publish-wheel: PYPI_TOKEN must be set in the environment, not passed on the command line")
    files = args.files or sorted(FACTORY.glob(f"dist/{PACKAGE}-{VERSION}*"))
    if not files:
        raise SystemExit(f"publish-wheel: nothing built for {VERSION} under dist/; run `make wheel` first")

    url = args.url.rstrip("/")
    index = args.index_url.rstrip("/") if args.index_url else f"{url}/simple"
    gitea = "/api/packages/" in url
    existing = held(f"{index}/{PACKAGE}/", args.user, token, authenticate=gitea)
    missing = [path for path in files if path.name not in existing]
    for path in files:
        if path.name in existing:
            print(f"already published: {path.name}")
    if missing:
        subprocess.run(
            [sys.executable, "-m", "twine", "upload", "--non-interactive", "--repository-url", url,
             "-u", args.user, "-p", token, *map(str, missing)],
            check=True,
        )
        for path in missing:
            print(f"published: {path.name}")
    # The snapshots this publish supersedes, after it is safely there. On a rerun there are usually none left.
    if gitea:
        retire(url, args.user, token, superseded(versions_of(existing), VERSION))


if __name__ == "__main__":
    main()
