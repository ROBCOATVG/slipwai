"""What the tree says about how a repository is delivered: which forge runs its CI, how a change reaches
production, and what each buildable directory is for.

Three facts brownfield adoption (experimental as `AGENTS.md` defines the word) used to assume — a GitHub
workflow for every repository, a service in every directory, nothing about the release path — and the first
real adoptions showed each assumption wrong. Read here the way `survey.py` reads everything else: proposed
only from a file that says so, with the file, and None where nothing does, which the record then carries as
`unrecorded` rather than as a default that looks like an answer. `survey.py` calls these; nothing else does.
"""
from __future__ import annotations

import json
import re
from fnmatch import fnmatch
from pathlib import Path

from .ecosystems import Detected, read

# Which forge a CI file belongs to, for the one question the gate's shape turns on. GitHub Actions workflows
# are run by Gitea and Forgejo too, so `.github/workflows` proposes `github` and the person can say `gitea`;
# everything the factory cannot write a workflow for is `other`, and the gate is then a command to add by hand.
CI_FORGES = {
    ".github/workflows": "github", ".gitea/workflows": "gitea", ".gitlab-ci.yml": "gitlab", "Jenkinsfile": "other",
    "azure-pipelines.yml": "other", "bitbucket-pipelines.yml": "other", ".circleci/config.yml": "other",
    ".woodpecker.yml": "other", ".drone.yml": "other", ".travis.yml": "other",
}


# What the remote's host says about the forge, where the tree carries no CI configuration.
HOST_FORGES = (("github.com", "github"), ("gitlab", "gitlab"), ("codeberg.org", "gitea"), ("gitea", "gitea"),
               ("bitbucket.org", "other"), ("dev.azure.com", "other"), ("visualstudio.com", "other"))


# Evidence of how a change reaches production: a CI job that deploys, or a script somebody runs.
DEPLOYS = re.compile(r"\b(deploy|deployment|release|publish|rollout|helm upgrade|kubectl apply)\b", re.IGNORECASE)


DEPLOY_SCRIPTS = ("deploy", "deploy.sh", "deploy.py", "release.sh", "release.py", "Capfile", "fabfile.py")


# A directory whose name says it holds a test suite rather than something that ships.
TEST_DIRECTORIES = {"test", "tests", "e2e", "spec", "specs", "integration", "integration-tests", "acceptance"}


def remote_host(url: str) -> str:
    """The host in a remote URL, whichever way Git spells it: `git@host:o/r`, `ssh://git@host/o/r`, `https://host/o/r`."""
    match = re.match(r"^(?:[a-z+]+://)?(?:[^@/]+@)?([^:/]+)", url.strip())
    return match.group(1).lower() if match else ""


def default_branch(root: Path) -> str:
    """The branch the gate's workflow runs on for a push: what `origin`'s HEAD points at where the clone recorded
    it, else the branch checked out, else `main` — read from `.git`, so the survey stays a reading. The third real
    adoption was on `master`, and a workflow hardcoded to `main` never ran on a push."""
    for pointer in (root / ".git/refs/remotes/origin/HEAD", root / ".git/HEAD"):
        match = re.match(r"ref:\s*refs/(?:remotes/origin/|heads/)(\S+)", read(pointer).strip())
        if match:
            return match.group(1)
    return "main"


def origin_remote(root: Path) -> str:
    """The `origin` remote's URL, read from `.git/config` rather than asked of Git, so the survey stays a reading."""
    config = read(root / ".git/config")
    section = re.search(r'\[remote "origin"\]((?:\n[^\[]*)*)', config)
    url = re.search(r"^\s*url\s*=\s*(\S+)", section.group(1), re.MULTILINE) if section else None
    return url.group(1) if url else ""


def role_of(root: Path, directory: str, found: Detected) -> tuple[str | None, str]:
    """What a buildable directory is for, where a file says so, with the file: a container file or a start
    script makes a service, a `bin` a tool, a test directory's name a suite; nothing said is None."""
    here = root / directory
    name = directory.rsplit("/", 1)[-1].lower()
    if directory != "." and name in TEST_DIRECTORIES:
        return "tests", f"{directory}/"
    for container in ("Dockerfile", "Containerfile"):
        if (here / container).is_file():
            return "service", prefixed(directory, container)
    if found.packaging == "war":
        return "service", found.evidence
    if found.ecosystem == "node":
        try:
            package = json.loads(read(here / "package.json"))
        except ValueError:
            package = {}
        package = package if isinstance(package, dict) else {}
        if "start" in (package.get("scripts") or {}):
            return "service", found.evidence
        if package.get("bin"):
            return "tool", found.evidence
        if not package.get("private") and (package.get("main") or package.get("exports")):
            return "library", found.evidence
    if found.ecosystem == "go":
        if (here / "main.go").is_file():
            return "service", prefixed(directory, "main.go")
        if (here / "cmd").is_dir():
            return "service", prefixed(directory, "cmd/")
    if found.ecosystem == "dotnet":
        text = read(root / found.evidence)
        if "Microsoft.NET.Sdk.Web" in text:
            return "service", found.evidence
        if "Microsoft.NET.Test.Sdk" in text:
            return "tests", found.evidence
        if re.search(r"<OutputType>\s*Library\s*</OutputType>", text):
            return "library", found.evidence
        if re.search(r"<OutputType>\s*Exe\s*</OutputType>", text):
            return "tool", found.evidence
    if found.ecosystem == "python":
        for manifest in ("pyproject.toml", "requirements.txt", "setup.py"):
            text = read(here / manifest).lower()
            if re.search(r"\b(fastapi|django|flask|starlette|uvicorn|gunicorn)\b", text):
                return "service", prefixed(directory, manifest)
    if found.ecosystem in ("maven", "gradle"):
        text = read(root / found.evidence).lower()
        if "spring-boot" in text or "quarkus" in text or "micronaut" in text:
            return "service", found.evidence
    return None, ""


def prefixed(directory: str, path: str) -> str:
    return path if directory == "." else f"{directory}/{path}"


def matching(paths: list[str], patterns: tuple[str, ...]) -> list[str]:
    """The paths a pattern names, at the root or anywhere below it."""
    return [
        path for path in paths
        if any(fnmatch(path, pattern) or fnmatch(path, f"*/{pattern}") for pattern in patterns)
    ]


def release_evidence_in(
    root: Path, paths: list[str], ci: tuple[str, ...], makefile: bool
) -> tuple[tuple[str, str], ...]:
    """Every file that says how a change reaches production: a CI configuration whose text deploys, a deploy or
    release script, a root Makefile with a `deploy` or `release` target."""
    found: list[tuple[str, str]] = []
    for path in ci:
        candidates = sorted(p for p in (root / path).glob("*.y*ml")) if (root / path).is_dir() else [root / path]
        for candidate in candidates:
            if DEPLOYS.search(read(candidate)):
                found.append(("pipeline", candidate.relative_to(root).as_posix()))
    found += [("scripted", path) for path in matching(paths, DEPLOY_SCRIPTS)]
    if makefile and re.search(r"^(deploy|release)\s*:", read(root / "Makefile"), re.MULTILINE):
        found.append(("scripted", "Makefile"))
    return tuple(dict.fromkeys(found))
