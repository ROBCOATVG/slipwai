"""What a language package may add to the catalogue, and what it may not.

The keel declares the axes and the answers that are infrastructure: a Postgres event store is Postgres
whichever language talks to it, and Keycloak is Keycloak. An answer named after a library — `fastapi`,
`spring-web`, `fastify` — is not infrastructure, it is a language's framework, and a keel that declared
one would be a keel a new language has to be edited into. Those belong to the package that implements
them, and this is where a package's `axes` block is folded in.

Everything about an option travels with it: its label, its capabilities, the feature that owns its
files, which targets it is offered under, whether it puts the app into Compose, and what it owns at the
repository root and inside a browser app. The keel's copy of the pruner carries none of it, and a
generated project's copy carries exactly the options that project was offered.
"""
from __future__ import annotations

import copy
from typing import Any

from .language_directory import Package, refusal


def declare_options(merged: dict[str, Any], packages: list[Package]) -> dict[str, str]:
    """Fold each package's own axis options into the catalogue, and refuse the ones that cannot be.

    The keel declares the axes and the answers that are infrastructure — a Postgres event store is
    Postgres whichever language talks to it. An answer that is a language's framework is the package's
    to declare: `fastapi` belongs to Python's package, and a keel that named it would be a keel a new
    language has to be edited into.

    Two rules, both the same rule the registry already has for a backend. An option belongs to one
    package: two declaring `fastapi` is the collision that `one setter per mark` exists to stop, and
    neither is silently preferred. And an option may not be declared over one the keel already has,
    because the keel's are the ones every package was built against.
    """
    refused: dict[str, str] = {}
    by_option: dict[tuple[str, str], list[Package]] = {}
    for package in packages:
        for axis, options in package.fragment.get("axes", {}).items():
            for name in options:
                by_option.setdefault((axis, name), []).append(package)
    for (axis, name), claimants in sorted(by_option.items()):
        if axis not in merged["axes"]:
            for package in claimants:
                refused.setdefault(package.name, refusal(
                    package.name, package.root,
                    f"declares {axis} option {name}, and the keel declares no {axis} axis"))
            continue
        if name in merged["axes"][axis]["options"]:
            for package in claimants:
                refused.setdefault(package.name, refusal(
                    package.name, package.root,
                    f"declares {axis} option {name}, which the keel already declares"))
            continue
        if len(claimants) > 1:
            named = ", ".join(sorted(package.name for package in claimants))
            for package in claimants:
                others = ", ".join(sorted(p.name for p in claimants if p is not package))
                refused.setdefault(package.name, refusal(
                    package.name, package.root,
                    f"declares {axis} option {name}, which {others} also declares; an option belongs to "
                    f"one package, and nothing here chooses between {named}"))
            continue
        package = claimants[0]
        option = copy.deepcopy(package.fragment["axes"][axis][name])
        option["backends"] = []
        # Where the option says it is offered, narrowed to the targets this installation has. A package
        # writes the clouds it has answers for; a person installs the clouds they deploy to, usually none
        # of them. `catalog_merge.reachable` prunes the same way one level up, and the two have to agree
        # or the catalogue refuses itself: an option offered under a target the tables do not carry is
        # exactly what `targets.check_targets` refuses.
        option["targets"] = [one for one in option.get("targets", []) if one in merged["targets"]]
        merged["axes"][axis]["options"][name] = option
    return refused


def declare_frontends(merged: dict[str, Any], packages: list[Package]) -> dict[str, str]:
    """Fold each package's `frontends` block into the catalogue, and refuse the ones that cannot be.

    A browser app is a family's, the way an axis option is a package's: the keel carries `none` and no other,
    and a frontend, named after its framework, belongs to the family that ships its files and
    the lock that resolves them (`docs/frontend-protocol.md`). The two rules are `declare_options`' own: a
    name belongs to one package, and none may be declared over the keel's. A framework package adds a backend
    to a family and is refused one, because `browser_apps` is a family's answer and a framework has none.

    The default follows: where the keel's default is `none` and a package brings a browser app, the default
    is the first such app in package order — the order the catalogue lists backends in — so a person who
    installs a language that ships one is offered it first, and a person who installs none is offered `none`.
    """
    refused: dict[str, str] = {}
    by_name: dict[str, list[Package]] = {}
    for package in packages:
        for name in package.fragment.get("frontends", {}):
            by_name.setdefault(name, []).append(package)
    for name, claimants in sorted(by_name.items()):
        for package in claimants:
            if "requires" in package.fragment:
                refused.setdefault(package.name, refusal(
                    package.name, package.root,
                    f"declares frontend {name}, and a package that requires its family adds backends: a "
                    f"browser app is its family's to ship"))
        claimants = [package for package in claimants if package.name not in refused]
        if name in merged["frontends"]:
            for package in claimants:
                refused.setdefault(package.name, refusal(
                    package.name, package.root, f"declares frontend {name}, which the keel already declares"))
        elif len(claimants) > 1:
            named = ", ".join(sorted(package.name for package in claimants))
            for package in claimants:
                refused.setdefault(package.name, refusal(
                    package.name, package.root,
                    f"declares frontend {name}, which {named} declare between them; a frontend belongs to one "
                    f"package, and nothing here chooses between them"))
    kept = sorted((package for package in packages if package.name not in refused),
                  key=lambda package: package.fragment.get("order", 0))
    brought = [name for package in kept for name in package.fragment.get("frontends", {})]
    for package in kept:
        for name, entry in package.fragment.get("frontends", {}).items():
            merged["frontends"][name] = {**copy.deepcopy(entry), "family": package.fragment["family"]}
    if merged["default"].get("frontend") == "none" and brought:
        merged["default"]["frontend"] = brought[0]
    return refused


def retract_frontends(catalog: dict[str, Any], package: Package) -> None:
    """Take a refused package's browser apps back out of a merged catalogue, and the default with them where it
    was one: a default pointing at a frontend nothing ships is a choice nobody can take. The next brought one, or
    `none`, takes its place."""
    for name in package.fragment.get("frontends", {}):
        catalog["frontends"].pop(name, None)
        if catalog["default"].get("frontend") == name:
            catalog["default"]["frontend"] = next((one for one in catalog["frontends"] if one != "none"), "none")
