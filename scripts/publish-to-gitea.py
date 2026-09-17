#!/usr/bin/env python3
"""Create and push the factory repository to a Gitea namespace.

The language-specific starters are not separate repositories and are not committed anywhere: they are
derived on demand from assets/ by `slipwai generate` (or browsed locally via `make starters`).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FACTORY = Path(__file__).resolve().parents[1]
# Each repository on Gitea, and the checkout it is pushed from. The factory publishes itself from wherever it
# is checked out, so the directory's name on disk need not match the repository's.
REPOSITORIES: dict[str, Path] = {"slipwai": FACTORY}


class PublishError(RuntimeError):
    pass


class Gitea:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.token = token
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, method: str, path: str, payload: dict[str, object] | None = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self.api_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json",
                # Named, because a proxy fronting the forge bans the default `Python-urllib/3.x` agent.
                "User-Agent": "slipwai-publish",
            },
        )
        try:
            with self.opener.open(request, timeout=10) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise PublishError(f"Gitea API {method} {path} failed ({error.code}): {detail}") from error
        except urllib.error.URLError as error:
            raise PublishError(f"cannot reach Gitea at {self.base_url}: {error.reason}") from error
        return json.loads(body) if body else {}

    def optional_repository(self, owner: str, name: str) -> dict | None:
        path = f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}"
        try:
            return self.request("GET", path)
        except PublishError as error:
            if "(404)" in str(error):
                return None
            raise


def git(repo: Path, *arguments: str, capture: bool = False, environment: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        env=environment,
    )
    return result.stdout.strip() if capture else ""


def private_default() -> bool:
    value = os.environ.get("GITEA_PRIVATE", "false").lower()
    if value not in {"true", "false"}:
        raise PublishError("GITEA_PRIVATE must be true or false")
    return value == "true"


def push_environment(username: str, token: str) -> dict[str, str]:
    return os.environ | {
        "GIT_ASKPASS": str(FACTORY / "scripts/gitea-askpass"),
        "GIT_TERMINAL_PROMPT": "0",
        "GITEA_USERNAME": username,
        "GITEA_TOKEN": token,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("GITEA_URL", "http://localhost:3300"))
    # The namespace is the publisher's, not the factory's: read from the environment, or named on the
    # command line, and never defaulted to a person here.
    parser.add_argument(
        "--owner", default=os.environ.get("GITEA_OWNER"),
        help="the Gitea user or organisation to publish under (default: $GITEA_OWNER)",
    )
    parser.add_argument("--list", action="store_true", help="list the exact repository scope and exit")
    args = parser.parse_args()
    if args.list:
        print("\n".join(REPOSITORIES))
        return
    if args.owner is None:
        parser.error("--owner is required (or set GITEA_OWNER): the namespace is yours, not the factory's")

    token = os.environ.get("GITEA_TOKEN")
    if not token:
        raise PublishError("GITEA_TOKEN is required and must not be committed or passed on the command line")

    missing: list[str] = []
    dirty: list[str] = []
    wrong_branch: list[str] = []
    for name, repo in REPOSITORIES.items():
        if not (repo / ".git").is_dir():
            missing.append(name)
            continue
        if git(repo, "status", "--porcelain=v1", capture=True):
            dirty.append(name)
        if git(repo, "branch", "--show-current", capture=True) != "main":
            wrong_branch.append(name)
    if missing or dirty or wrong_branch:
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if dirty:
            details.append("dirty: " + ", ".join(dirty))
        if wrong_branch:
            details.append("not on main: " + ", ".join(wrong_branch))
        raise PublishError("repository preflight failed; " + "; ".join(details))

    gitea = Gitea(args.url, token)
    authenticated = gitea.request("GET", "/user")
    username = authenticated.get("login")
    if not isinstance(username, str) or not username:
        raise PublishError("Gitea did not return the authenticated username")
    owner_is_user = username.casefold() == args.owner.casefold()
    if not owner_is_user:
        organisation = gitea.request("GET", f"/orgs/{urllib.parse.quote(args.owner)}")
        if organisation.get("username", "").casefold() != args.owner.casefold():
            raise PublishError(f'Gitea organisation "{args.owner}" was not found')

    environment = push_environment(username, token)
    existing = {name: gitea.optional_repository(args.owner, name) for name in REPOSITORIES}
    for name, remote_repo in existing.items():
        if remote_repo is not None and not remote_repo.get("empty", False):
            repo = REPOSITORIES[name]
            remote_url = f"{args.url.rstrip('/')}/{args.owner}/{name}.git"
            remote_main = git(
                repo,
                "ls-remote",
                remote_url,
                "refs/heads/main",
                capture=True,
                environment=environment,
            ).partition("\t")[0]
            local_main = git(repo, "rev-parse", "main", capture=True)
            if not remote_main or remote_main != local_main:
                raise PublishError(
                    f"{args.owner}/{name} already contains different commits; refusing an ambiguous push"
                )

    create_path = "/user/repos" if owner_is_user else f"/orgs/{urllib.parse.quote(args.owner)}/repos"
    for name in REPOSITORIES:
        if existing[name] is None:
            gitea.request(
                "POST",
                create_path,
                {
                    "name": name,
                    "private": private_default(),
                    "default_branch": "main",
                    "auto_init": False,
                },
            )
            print(f"created: {args.owner}/{name}")

    for name, repo in REPOSITORIES.items():
        expected = f"{args.url.rstrip('/')}/{args.owner}/{name}.git"
        remotes = git(repo, "remote", capture=True).splitlines()
        if "gitea" in remotes:
            actual = git(repo, "remote", "get-url", "gitea", capture=True)
            if actual != expected:
                raise PublishError(f'{name}: existing "gitea" remote points to {actual}, expected {expected}')
        else:
            git(repo, "remote", "add", "gitea", expected)
        git(repo, "push", "--set-upstream", "gitea", "main", environment=environment)
        print(f"pushed: {args.owner}/{name}")


if __name__ == "__main__":
    try:
        main()
    except (PublishError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"publish failed: {error}", file=sys.stderr)
        # The message above is the whole diagnosis; a traceback would bury it.
        raise SystemExit(1) from None
