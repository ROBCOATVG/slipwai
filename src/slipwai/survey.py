"""What an existing repository is made of, read off its tree: what `slipwai adopt` proposes and the person confirms.

Brownfield adoption (experimental as `AGENTS.md` defines the word) starts with a survey rather than a
questionnaire, because most of what the questionnaire would ask is already written in the tree: which
directories build, in what language, with which tools, pinned to which runtime; whether CI, containers and
infrastructure code are here; whether a database schema is versioned here, and with what. Every fact found
carries its evidence — the file that said so — so the person confirming can judge it rather than take it,
and everything here is a proposal: `provenance` in `project.json` records `detected` for what the tree
said, `confirmed` for what the person accepted and `overridden` for what they changed.

Bounded on purpose. The walk stops a few levels down and skips dependency and build output, a directory that
builds is not searched for builds inside it when its manifest says it owns them (npm workspaces, Maven
modules, a Gradle settings file, a .NET solution), and a signal this cannot read is reported as absent, not
guessed. `ecosystems.py` is the table of what can be recognised.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from .delivery_facts import (
    CI_FORGES,
    HOST_FORGES,
    default_branch,
    matching,
    origin_remote,
    release_evidence_in,
    remote_host,
    role_of,
)
from .ecosystems import ECOSYSTEMS, Detected, aggregates, read
from .origin import FORGES, RELEASE_PATHS
from .quick_wins import quick_wins

# Where a survey does not look: what a build writes, what a package manager fetches, and the factory's own.
SKIPPED = {
    ".git", "node_modules", "vendor", "target", "build", "dist", "out", ".venv", "venv", "__pycache__",
    ".tox", "bin", "obj", ".gradle", ".idea", ".vscode", ".next", ".nuxt", "coverage", "delivery",
}
# How far below the root a buildable directory is looked for, and how far files of evidence are.
DEPTH = 3
EVIDENCE_DEPTH = 5

CI_FILES = (
    ".github/workflows", ".gitea/workflows", ".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml",
    "bitbucket-pipelines.yml", ".circleci/config.yml", ".woodpecker.yml", ".drone.yml", ".travis.yml",
)
CONTAINER_FILES = (
    "Dockerfile", "Containerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
)
# Infrastructure as code, by the file that marks it; `*` patterns are matched against every path surveyed.
INFRASTRUCTURE = (
    ("opentofu / terraform", "*.tf"), ("cdk", "cdk.json"), ("cloudformation", "template.y*ml"),
    ("serverless framework", "serverless.y*ml"), ("pulumi", "Pulumi.yaml"), ("kubernetes", "kustomization.y*ml"),
    ("helm", "Chart.yaml"), ("ansible", "ansible.cfg"),
)
# Where a database schema is versioned in this repository, by the tool's footprint.
SCHEMA_TOOLS = (
    ("flyway", ("flyway.conf", "flyway.toml", "*/db/migration/*.sql", "db/migration/*.sql")),
    ("liquibase", ("liquibase.properties", "*changelog*.xml", "*changelog*.yaml")),
    ("alembic", ("alembic.ini",)),
    ("prisma", ("*schema.prisma",)),
    ("knex", ("knexfile.*",)),
    ("entity framework", ("*/Migrations/*.Designer.cs", "Migrations/*.Designer.cs")),
    ("golang-migrate", ("*/migrations/*.up.sql", "migrations/*.up.sql")),
    ("rails", ("db/migrate/*.rb", "db/schema.rb")),
    ("django", ("*/migrations/0001_*.py",)),
    ("dbmate", ("db/migrations/*.sql",)),
)
# A database driver in a dependency manifest: the database is talked to from here, wherever its schema lives.
DRIVERS = (
    "pg", "postgres", "postgresql", "psycopg", "psycopg2", "asyncpg", "mysql", "mysql2", "pymysql", "sqlite3",
    "better-sqlite3", "npgsql", "sqlclient", "mongodb", "pymongo", "mongoose", "oracledb", "jdbc", "sequelize",
    "typeorm", "prisma", "knex", "sqlalchemy", "gorm", "pgx", "hibernate", "dapper", "entityframeworkcore",
    "activerecord", "doctrine",
)
DEPENDENCY_MANIFESTS = (
    "package.json", "requirements.txt", "requirements-dev.txt", "pyproject.toml", "go.mod", "pom.xml",
    "build.gradle", "build.gradle.kts", "composer.json", "Gemfile", "*.csproj", "*.fsproj", "build.xml", "ivy.xml",
)
NAME = re.compile(r"[^a-z0-9-]+")


@dataclass(frozen=True)
class Root:
    """One directory that builds: where, what its files say about it, and — where they say — what it is for:
    `service` (runs somewhere), `library` (imported by others), `tool` (run by hand or in CI), `tests` (a suite
    of its own). None where nothing in the tree says, which is a question and never a default."""

    path: str
    found: Detected
    role: str | None = None
    role_evidence: str = ""

    def name(self, project: str) -> str:
        """What the manifest calls this application: the project's own name at the root, else the directory's."""
        raw = project if self.path == "." else self.path.rsplit("/", 1)[-1]
        name = NAME.sub("-", raw.lower()).strip("-")
        return name or "app"


@dataclass(frozen=True)
class Survey:
    """Everything the tree said, each fact with the file that said it."""

    roots: tuple[Root, ...]
    ci: tuple[str, ...]
    containers: tuple[str, ...]
    infrastructure: tuple[tuple[str, str], ...]
    schema_tools: tuple[tuple[str, str], ...]
    drivers: tuple[tuple[str, str], ...]
    makefile: bool
    readme: bool
    git: bool
    # The `origin` remote's URL as `.git/config` has it, or empty; the host is one more word about the forge.
    remote: str = ""
    # The branch a push lands on — `origin`'s HEAD, else the one checked out — which the gate's workflow runs on.
    default_branch: str = "main"
    # How a change reaches production, as far as the tree says: (`pipeline` | `scripted`, the file that says so).
    release_evidence: tuple[tuple[str, str], ...] = ()
    # Big issues that are quick wins — a secret in the tree, IDE output tracked, an HTTP dependency source, a missing
    # lockfile, an archive tracked — each `{kind, where, what, fix}` (`quick_wins.py`); proposals, never changes.
    quick_wins: tuple[dict, ...] = ()

    @property
    def forge(self) -> tuple[str, str]:
        """Which forge runs this repository's CI, as proposed, with the evidence: a CI file first, the remote's
        host second, and `none` — no CI configuration in the tree — where neither says."""
        for path in self.ci:
            if path in CI_FORGES:
                return CI_FORGES[path], path
        host = remote_host(self.remote)
        for needle, forge in HOST_FORGES:
            if needle in host:
                return forge, f"remote origin at {host}"
        assert "none" in FORGES
        return "none", "no CI configuration in the tree"

    @property
    def release_path(self) -> str | None:
        """How a change reaches production, as proposed: `pipeline` where a CI job deploys, `scripted` where a
        script does, None where the tree says nothing — which stays unrecorded until a person says."""
        kinds = {kind for kind, _ in self.release_evidence}
        for path in RELEASE_PATHS:
            if path in kinds:
                return path
        return None

    @property
    def schema_home(self) -> str:
        """Where the database schema is versioned, as proposed: `here` when a tool's footprint is, `unmanaged`
        when a driver says a database is talked to but nothing versions its schema here, `none` otherwise.
        `elsewhere` is never proposed — only a person knows about another repository."""
        if self.schema_tools:
            return "here"
        return "unmanaged" if self.drivers else "none"

    @property
    def infrastructure_home(self) -> str:
        """Where the deployment infrastructure is described, as proposed: `here` when infrastructure code
        is, else `unmanaged` — something runs this somewhere, and nothing here says how."""
        return "here" if self.infrastructure else "unmanaged"

    @property
    def languages(self) -> list[str]:
        return list(dict.fromkeys(root.found.language for root in self.roots))


def written_by_factory(root: Path) -> tuple[str, set[str]]:
    """What an earlier adoption put here — the delivery directory and every path it listed in `.written` — so
    that a re-survey does not read the factory's own CI workflow or scripts as the repository's."""
    try:
        document = json.loads((root / "project.json").read_text())
        delivery = document.get("layout", {}).get("delivery", ".")
    except (OSError, ValueError, AttributeError):
        return ".", set()
    listing = root / (f"{delivery}/.written" if delivery != "." else ".written")
    written = set(listing.read_text().split()) if listing.is_file() else set()
    return delivery, written


def directories(root: Path, depth: int, skipped: frozenset[str] = frozenset()) -> list[str]:
    """Every directory up to `depth` below `root`, as a relative posix path, `.` first; skipping what is not code."""
    found = ["."]
    frontier = [(root, 0)]
    while frontier:
        here, level = frontier.pop(0)
        if level == depth:
            continue
        try:
            children = sorted(
                child for child in here.iterdir()
                if child.is_dir() and child.name not in SKIPPED and child.relative_to(root).as_posix() not in skipped
            )
        except OSError:
            continue
        for child in children:
            if child.name.startswith(".") and child.name != ".github":
                continue
            found.append(child.relative_to(root).as_posix())
            frontier.append((child, level + 1))
    return found


def files(root: Path, depth: int = EVIDENCE_DEPTH, skipped: frozenset[str] = frozenset()) -> list[str]:
    """Every file up to `depth` below `root`, relative and posix, under the same skips."""
    found = []
    for directory in directories(root, depth, skipped):
        here = root if directory == "." else root / directory
        try:
            found += [
                (f"{directory}/{child.name}" if directory != "." else child.name)
                for child in sorted(here.iterdir()) if child.is_file()
            ]
        except OSError:
            continue
    return found


def buildable(root: Path, skipped: frozenset[str] = frozenset()) -> tuple[Root, ...]:
    """Every directory that builds, by path, each recognised once and none inside a build of its own ecosystem
    that owns it — a Go module under an npm workspace is still a root; a workspace package is not."""
    roots: list[Root] = []
    owners: list[tuple[str, str]] = []
    for directory in directories(root, DEPTH, skipped):
        for detect in ECOSYSTEMS:
            found = detect(root, directory)
            if found is None:
                continue
            owned = any(
                ecosystem == found.ecosystem and (owner == "." or directory.startswith(f"{owner}/"))
                for owner, ecosystem in owners
            )
            if not owned:
                roots.append(Root(directory, found, *role_of(root, directory, found)))
                if aggregates(root, found):
                    owners.append((directory, found.ecosystem))
            break
    return tuple(sorted(roots, key=lambda found: found.path))


def drivers_in(root: Path, paths: list[str]) -> tuple[tuple[str, str], ...]:
    """Every database driver named by a dependency manifest, with the manifest that names it — or by the name of a
    committed jar, which is how an Ant build declares one (`lib/mysql-connector-java-5.1.23-bin.jar`)."""
    found: list[tuple[str, str]] = []
    for path in matching(paths, DEPENDENCY_MANIFESTS):
        text = read(root / path).lower()
        for driver in DRIVERS:
            if re.search(rf"(?<![\w.-]){re.escape(driver)}(?![\w-])", text) and (driver, path) not in found:
                found.append((driver, path))
    for path in paths:
        if path.endswith(".jar"):
            words = set(re.split(r"[-_.]", path.rsplit("/", 1)[-1].lower()))
            found += [(driver, path) for driver in DRIVERS if driver in words and (driver, path) not in found]
    return tuple(found)


def own_makefile(root: Path) -> bool:
    """Whether the repository has a root Makefile of its own — not the one `adopt` writes where there was none,
    which opens with the delivery marker, so that the fact holds still across the adoption it drives."""
    path = root / "Makefile"
    return path.is_file() and not read(path).startswith("# slipwai:delivery:begin")


def survey(root: Path) -> Survey:
    """Read the tree at `root` and say what it is made of, with the evidence for each fact — leaving out what an
    earlier adoption wrote, which is the factory's and not the repository's."""
    delivery, written = written_by_factory(root)
    skipped = frozenset({delivery} if delivery != "." else set())
    paths = [path for path in files(root, skipped=skipped) if path not in written]
    infrastructure = tuple(
        (kind, path) for kind, pattern in INFRASTRUCTURE for path in paths
        if fnmatch(path, pattern) or fnmatch(path, f"*/{pattern}")
        if kind != "cloudformation" or "AWSTemplateFormatVersion" in read(root / path)
    )
    schema_tools = tuple(
        (tool, path) for tool, patterns in SCHEMA_TOOLS for path in matching(paths, patterns)[:1]
    )
    ci = tuple(
        path for path in CI_FILES
        if ((root / path).is_file() and path not in written)
        or ((root / path).is_dir() and any(f"{path}/{p.name}" not in written for p in (root / path).glob("*.y*ml")))
    )
    makefile = own_makefile(root)
    return Survey(
        roots=buildable(root, skipped),
        ci=ci,
        containers=tuple(path for path in paths if path.rsplit("/", 1)[-1] in CONTAINER_FILES),
        infrastructure=infrastructure,
        schema_tools=schema_tools,
        drivers=drivers_in(root, paths),
        makefile=makefile,
        readme=any((root / name).is_file() for name in ("README.md", "README", "README.rst", "README.txt")),
        git=(root / ".git").exists(),
        remote=origin_remote(root),
        default_branch=default_branch(root),
        release_evidence=release_evidence_in(root, paths, ci, makefile),
        quick_wins=tuple(finding.record() for finding in quick_wins(root, paths, written, delivery)),
    )
