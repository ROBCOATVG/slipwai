"""What a project can do, and what that earns it.

A capability is what an answer *gives* a project, named for the thing rather than for the answer that
brought it: `frontend`, `react`, `typescript`, `event-sourcing`, `auth-keycloak`. `catalog.json` declares
them per profile, per frontend and per axis option; `project.json` records them per deployable, and the
union across the deployables is what the whole project can do.

That union is the one question a skill has to be able to ask. `assets/toolkit/skills/` holds the whole
delivery catalogue, and most of it applies to any project — `tdd`, `refactoring`, `specification` — but
some of it is about a capability a given project does not have. `bff-entry-points` is eleven thousand words
about a backend for a frontend, in a project with no browser app; `secure-oauth-oidc` is eleven thousand
more about a login, in a project with no identity provider. A skill says which capabilities it serves in
its `SKILL.md` frontmatter, and a skill that says nothing serves every project.

This is not the same question as *which language a skill's examples are written in*. A language-shaped
skill still ships, with a pseudocode disclaimer (`examples.py`), because the guidance is
language-independent even where the snippet is not. A skill about a capability the project does not have
has no such reading: there is nothing for it to be about.
"""
from __future__ import annotations

from .catalog import CATALOG
from .services import App

# The frontmatter key, and what a declaration is: one line, comma-separated, each entry a capability or a
# `prefix-*` that matches every capability beginning with it — `auth-*` is every identity provider the
# staff axis can be answered with, present and future, which a list of names would have to be edited for.
DECLARATION = "capabilities:"
WILDCARD = "*"


def app_capabilities(profile: str, app: App) -> list[str]:
    """What one application gives the project, as `project.json` records it.

    A service: what the profile gives every project, the language it is written in, and what each axis
    answer gives. A browser app: what its framework gives. An application the factory did not make claims
    nothing — an adopted repository's own code is not graded, and no capability is inferred from it.
    """
    if not app.generated:
        return []
    if not app.is_service:
        return list(CATALOG["frontends"][app.framework or "none"]["capabilities"])
    # The language, because a skill can be about a language the way `typescript-strict` is, and a service
    # is the only thing that says which languages a project is written in. The family rather than the
    # backend key: `typescript-strict` is as true of a project on Nest as on Fastify.
    return [*CATALOG["profiles"][profile]["capabilities"], app.language, *app.selection.capabilities]


def project_capabilities(profile: str, apps: list[App]) -> set[str]:
    """Everything any of this project's applications can do — the union a skill's declaration is read against."""
    return {capability for app in apps for capability in app_capabilities(profile, app)}


def pruning_capabilities(profile: str, apps: list[App]) -> set[str] | None:
    """What to hold the catalogue to, or None for "hold it to nothing and ship all of it".

    None where nothing here was generated — an adopted repository (experimental), whose applications claim
    no capability because nobody answered an axis for them. Withholding a skill then would be pruning on
    ignorance rather than on a fact: a repository the factory did not make may well have a React frontend
    and a login, and the survey records what it is built from without claiming to have decided it. The
    moment such a repository gains an application the factory made, its answers decide as they do anywhere.
    """
    return project_capabilities(profile, apps) if any(app.generated for app in apps) else None


def declared_for(text: str) -> tuple[str, ...] | None:
    """The capabilities a `SKILL.md` declares, or None where it declares none and so serves every project.

    Read off the frontmatter by hand rather than with a YAML parser: this factory has no runtime
    dependencies, and the generated project's own gate reads the same line with the same rule, so the
    format is deliberately one a line-at-a-time reader cannot get wrong.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith(DECLARATION):
            named = tuple(part.strip() for part in line[len(DECLARATION):].split(",") if part.strip())
            return named or None
    return None


def serves(declared: tuple[str, ...] | None, capabilities: set[str]) -> bool:
    """Whether a skill declaring these belongs in a project that can do those.

    No declaration is "every project". Otherwise one match is enough: a skill about the browser edge is
    worth having as soon as there is a browser app, whatever else the project does or does not have.
    """
    if declared is None:
        return True
    for pattern in declared:
        if pattern.endswith(WILDCARD):
            prefix = pattern[: -len(WILDCARD)]
            if any(capability.startswith(prefix) for capability in capabilities):
                return True
        elif pattern in capabilities:
            return True
    return False
