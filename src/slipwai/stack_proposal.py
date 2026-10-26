"""The stack a new home is proposed on, read from what the survey found, and what this machine can generate it in.

Two strategies build a new home — a strangler fig `beside` the old code, and a rewrite — and its stack is the
person's decision. What the board can do is make the first answer the sensible one: the language the code is
already in, a browser app where the old one served pages, Postgres where there is a database. A rewrite may be a
completely new setup, so this is a proposal the form shows preselected, never a choice it makes. A proposed
language this machine has no package for is said, with the command that installs it, rather than dropped for one it
does have.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .catalog import CATALOG, families

#: The language package for each ecosystem the survey reads. An ecosystem with no package here has no proposal.
FAMILY_OF = {"java": "java", "kotlin": "java", "maven": "java", "gradle": "java", "ant": "java",
             "node": "typescript", "typescript": "typescript", "javascript": "typescript", "npm": "typescript",
             "python": "python", "go": "go"}
#: The framework a Java proposal takes, from a word found in the old build's files.
JAVA_FRAMEWORKS = (("spring", "java-spring"), ("quarkus", "java-quarkus"))
#: What says the old app serves pages to a browser rather than only an API.
PAGES = ("*.jsp", "*.jspx", "*.erb", "*.cshtml", "*.vm", "*.ftl", "templates/*.html", "views/*.html")


@dataclass(frozen=True)
class Proposal:
    """The stack proposed for a new home, why, and what this machine is missing to generate it."""

    backend: str | None
    frontend: str
    persistence: str
    because: tuple[str, ...]
    #: Language packages the proposal needs and this machine has not installed.
    missing: tuple[str, ...] = field(default_factory=tuple)


def ecosystems(document: dict) -> list[tuple[str, str]]:
    """Each wrapped deployable's path and the ecosystem the survey read for it, services first: the new home replaces
    what serves actors, not a library it happens to build beside."""
    found = []
    for record in (document.get("deployables") or {}).values():
        if not isinstance(record, dict) or record.get("generated"):
            continue
        toolchain = record.get("toolchain") or {}
        found.append((record.get("kind") != "service", str(record.get("path") or "."),
                      str(toolchain.get("kind") or toolchain.get("ecosystem") or "")))
    return [(path, ecosystem) for _, path, ecosystem in sorted(found, key=lambda one: one[0])]


def java_framework(root: Path, path: str) -> str:
    """`java-spring` or `java-quarkus` where the old build names one, otherwise the family's first framework."""
    here = root / path
    # Committed jars are named for what they are, wherever under the app they were dropped.
    names = " ".join(item.relative_to(here).as_posix().lower() for item in here.rglob("*.jar"))
    for build in ("pom.xml", "build.gradle", "build.gradle.kts", "build.xml"):
        if (here / build).is_file():
            names += (here / build).read_text(errors="replace", encoding="utf-8").lower()
    chosen = next((framework for word, framework in JAVA_FRAMEWORKS if word in names), None)
    return chosen or (families().get("java") or ["java-spring"])[0]


def serves_pages(root: Path, paths: list[str]) -> bool:
    for path in paths:
        here = root / path
        if any(next(here.rglob(pattern), None) for pattern in PAGES):
            return True
    return False


def proposed(root: Path, document: dict) -> Proposal:
    """The stack a new home would be generated on, read from the tree and the record."""
    found = ecosystems(document)
    because: list[str] = []
    backend = None
    for path, ecosystem in found:
        family = FAMILY_OF.get(ecosystem.lower())
        if family is None:
            continue
        backend = java_framework(root, path) if family == "java" else family
        because.append(f"`{path}` is {ecosystem}, so the new home stays in {family}")
        break
    if backend is None and found:
        because.append(f"no language package matches {', '.join(sorted({e for _, e in found if e}))}: pick one")
    pages = serves_pages(root, [path for path, _ in found])
    # The first browser app the catalogue offers: which one is the frontend packages' to say, never the keel's.
    browser = next((name for name in CATALOG["frontends"] if name != "none"), None)
    frontend = browser if pages and browser else "none"
    because.append("the old app serves pages, so the new home has a browser app" if pages else
                   "the old app serves no pages, so the new home has none")
    database = document.get("database") or {}
    relational = bool(database.get("drivers") or database.get("tools")) or database.get("schema") not in (None, "none")
    persistence = "postgres" if relational else "memory"
    because.append("there is a database, so the new home keeps its data in Postgres" if relational else
                   "nothing here keeps data, so the new home starts in memory")
    family = next((name for name, frameworks in families().items() if backend in frameworks), None)
    needed = FAMILY_OF.get(backend or "") or (backend.split("-")[0] if backend else None)
    missing = () if backend is None or family else (needed or backend,)
    return Proposal(backend, frontend, persistence, tuple(because), missing)


def installed_backends() -> list[str]:
    """Every backend this machine can generate, in the catalogue's order."""
    return list(CATALOG["backends"])


def installed_frontends() -> list[str]:
    """Every browser app this machine can generate, `none` first."""
    return ["none", *(name for name in CATALOG["frontends"] if name != "none")]
