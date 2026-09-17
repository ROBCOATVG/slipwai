#!/usr/bin/env python3
"""Serve a `pages` branch from every local Gitea repository, GitHub-Pages style.

Gitea has no built-in Pages feature, so this daemon fills the gap for a
single-host Homebrew installation: it reads the bare repositories straight off
disk (no API token, no webhooks), exports the tip of each repository's `pages`
branch, and serves the result at http://localhost:<port>/<owner>/<repo>/.

It speaks plain HTTP and, by default, listens on loopback only. A public
`https://` name for it therefore needs something on the same host terminating
TLS and proxying to this port; point that proxy here, or set GITEA_PAGES_HOST to
bind an address it can reach. A TLS handshake arriving here directly is
answered with a 400, because a ClientHello is not a request line.

CI publishes by force-pushing a rendered site to the `pages` branch — see the
Gitea deploy step in the event-modelling starter's event-model.yml.
"""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPOS = Path(os.environ.get("GITEA_REPOS_DIR", "/opt/homebrew/var/gitea/data/gitea-repositories"))
ROOT = Path(os.environ.get("GITEA_PAGES_ROOT", "/opt/homebrew/var/gitea-pages"))
# Loopback by default: nothing here authenticates, and a public name for it belongs to a TLS terminator on
# the same host. Set this to what that proxy can reach, or to `0.0.0.0` to answer on every interface.
HOST = os.environ.get("GITEA_PAGES_HOST", "127.0.0.1")
PORT = int(os.environ.get("GITEA_PAGES_PORT", "3301"))
BRANCH = os.environ.get("GITEA_PAGES_BRANCH", "pages")
POLL_SECONDS = float(os.environ.get("GITEA_PAGES_POLL_SECONDS", "15"))

STATE = ROOT / ".state"


def log(message: str) -> None:
    print(message, flush=True)


def pages_branch_sha(bare: Path) -> str | None:
    result = subprocess.run(
        ["git", "--git-dir", str(bare), "rev-parse", "--verify", "--quiet", f"refs/heads/{BRANCH}"],
        capture_output=True,
        text=True,
    )
    sha = result.stdout.strip()
    return sha or None


def export(bare: Path, site: Path, sha: str) -> None:
    staging = Path(tempfile.mkdtemp(dir=ROOT, prefix=".staging-"))
    # Cleared once the staging directory has become the site, so `finally` removes only a half-built one.
    pending: Path | None = staging
    try:
        archive = subprocess.run(
            ["git", "--git-dir", str(bare), "archive", sha], capture_output=True, check=True
        )
        subprocess.run(["tar", "-x", "-C", str(staging)], input=archive.stdout, check=True)
        site.parent.mkdir(parents=True, exist_ok=True)
        retired = None
        if site.exists():
            retired = Path(tempfile.mkdtemp(dir=ROOT, prefix=".retired-")) / "site"
            site.rename(retired)
        staging.rename(site)
        pending = None
        if retired is not None:
            shutil.rmtree(retired.parent, ignore_errors=True)
    finally:
        if pending is not None:
            shutil.rmtree(pending, ignore_errors=True)


def discover() -> dict[str, Path]:
    sites: dict[str, Path] = {}
    if not REPOS.is_dir():
        return sites
    for owner_dir in sorted(REPOS.iterdir()):
        if not owner_dir.is_dir() or owner_dir.name.startswith("."):
            continue
        for bare in sorted(owner_dir.glob("*.git")):
            if bare.name.endswith(".wiki.git"):
                continue
            sites[f"{owner_dir.name}/{bare.name[: -len('.git')]}"] = bare
    return sites


def write_index(published: list[str]) -> None:
    items = "\n".join(
        f'      <li><a href="/{html.escape(name)}/">{html.escape(name)}</a></li>' for name in published
    )
    body = items or "      <li>No repository has published a <code>pages</code> branch yet.</li>"
    (ROOT / "index.html").write_text(
        "<!doctype html>\n<meta charset='utf-8'>\n<title>Gitea pages</title>\n"
        "<style>body{font:16px/1.5 system-ui;max-width:40rem;margin:3rem auto;padding:0 1rem}</style>\n"
        f"<h1>Gitea pages</h1>\n<ul>\n{body}\n</ul>\n"
    )


def sync_forever() -> None:
    while True:
        try:
            sync_once()
        except Exception as error:  # a broken repo must not stop the loop
            log(f"sync error: {error}")
        time.sleep(POLL_SECONDS)


def sync_once() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    sites = discover()
    published: list[str] = []
    for name, bare in sites.items():
        marker = STATE / name.replace("/", "__")
        site = ROOT / name
        sha = pages_branch_sha(bare)
        if sha is None:
            if site.exists():
                log(f"unpublished: {name} (no {BRANCH} branch)")
                shutil.rmtree(site, ignore_errors=True)
                marker.unlink(missing_ok=True)
            continue
        previous = marker.read_text().strip() if marker.exists() else None
        if sha != previous or not site.is_dir():
            export(bare, site, sha)
            marker.write_text(sha + "\n")
            log(f"published: {name} @ {sha[:12]}")
        published.append(name)
    known = {name for name in sites}
    for marker in STATE.iterdir():
        name = marker.name.replace("__", "/")
        if name not in known:
            shutil.rmtree(ROOT / name, ignore_errors=True)
            marker.unlink(missing_ok=True)
            log(f"unpublished: {name} (repository removed)")
    write_index(published)


def fold_site_case(path: str, root: Path) -> str:
    """Return `path` with its owner and repository segments spelled the way they are on disk.

    Gitea lowercases both directories when it stores a repository, while a project's published address
    carries the owner as it was typed — `ROBCOATVG/slipwai/` against a site exported as
    `robcoatvg/slipwai`. The two agree on a case-insensitive filesystem and miss everywhere else, so
    the first two segments are matched without regard to case; everything below them is site content and
    stays exact. A segment with no match is left alone, and the ordinary 404 follows.
    """
    path, separator, rest = path.partition("?")
    if not separator:
        path, separator, rest = path.partition("#")
    segments = path.split("/")
    directory = root
    matched = 0
    for index, segment in enumerate(segments):
        if not segment:
            continue
        if matched == 2:
            break
        if not (directory / segment).is_dir() and directory.is_dir():
            folded = segment.lower()
            candidates = sorted(entry.name for entry in directory.iterdir() if entry.name.lower() == folded)
            if candidates:
                segments[index] = candidates[0]
        directory = directory / segments[index]
        matched += 1
    return "/".join(segments) + separator + rest


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        return super().translate_path(fold_site_case(path, ROOT))

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        # A success is noise for a pages host; anything else is the one trace a failed request leaves, so it
        # goes to the log with the request line as it arrived. That line is what tells a TLS handshake
        # reaching a cleartext port (a 400 with a request line of handshake bytes) from a missing site.
        if isinstance(code, HTTPStatus):
            code = code.value
        if isinstance(code, int) and (200 <= code < 300 or code == HTTPStatus.NOT_MODIFIED):
            return
        self.log_message("%s %r", code, self.requestline)

    def log_message(self, format: str, *arguments: object) -> None:
        log(f"{self.address_string()} - {format % arguments}")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    sync_once()
    threading.Thread(target=sync_forever, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), partial(Handler, directory=str(ROOT)))
    log(f"serving {ROOT} at http://{HOST}:{PORT}/ (branch: {BRANCH}, poll: {POLL_SECONDS:g}s)")
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
