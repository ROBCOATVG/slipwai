"""The registry as the running process has it: the built-in languages and every package the directory holds.

`registry.registry()` delegates here by name, at call time, so the catalog — which a package's Python imports
through the keel — is built before any package is imported. `catalog.py` read the fragments and merged them
(phase 1); `build` imports each package (phase 2), refuses alone the ones that cannot load, takes a refused
package's backends back out of the catalog, and orders what is left the way the catalog does.

A fault in a built-in language is not a package's to refuse: `load` raises for it and every verb stops. A fault
in a package is one line, `language <name> (<directory>): <fault>`, and the others load.
"""
from __future__ import annotations

import copy
import posixpath
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import registry as registry_module
from .assets import inside, located
from .catalog import CATALOG, PACKAGES, REFUSALS
from .catalog_checks import outside, validate_catalog
from .catalog_merge import family_missing, is_framework, retract
from .errors import blame, said
from .language_directory import Package, Refused, forget, import_package, module_name, refusal, reinstall
from .npm_workspace import FRONTENDS_DIRECTORY, BrowserApp
from .registry import (
    BROWSER_APPS,
    FLAG_READER,
    FLAG_RESOURCE,
    NPM_WORKSPACE,
    READ_SIDE_FILES,
    SHARED_CODE,
    WRITE_SIDE_FILES,
    Language,
    Registry,
    load,
)
from .rungs import every_rung

# What phase 2 refused the last time the registry was built, for `refusals()`.
PHASE_TWO: list[str] = []


def reaches(language: Language, registry: Registry, declared: Mapping[str, Any] | None = None) -> list[str]:
    """Every source a package's backends read that is not a file (or, for a tree, a directory) inside the package's
    root or, for a framework, its family's, and every destination they write that is not a path inside the service:
    one fault each."""
    faults: list[str] = []
    for backend in language.backends:
        key, roots = backend.key, registry.sources(backend.key)
        for member in (WRITE_SIDE_FILES, READ_SIDE_FILES):
            for files in every_rung(registry.answer(key, member)).values():
                for destination, source in files.items():
                    faults += placed(key, destination)
                    faults += found(roots, f"backing-services/{key}/{source}", key, source)
        for resource in registry.answer(key, FLAG_RESOURCE).values():
            faults += placed(key, resource.destination)
            faults += found(roots, f"backing-services/{key}/{resource.source}", key, resource.source)
        reader = registry.answer(key, FLAG_READER)
        faults += placed(key, reader.source) + placed(key, reader.tests)
        faults += found(roots, f"languages/{reader.tree}", key, reader.tree, tree=True)
    for family in language.families:
        if NPM_WORKSPACE in family.answers:
            faults += held(family.name, registry.root(family.name), family.answers[NPM_WORKSPACE])
        if BROWSER_APPS in family.answers or declared:
            faults += writes(family.name, registry.root(family.name), family.answers.get(BROWSER_APPS, {}),
                             NPM_WORKSPACE in family.answers, declared)
            # What a project asks of the family its browser app is written in, beyond the two answers above:
            # the architecture page's paragraph on shared code (`formatter` may be None). A family of services
            # is held to it through each backend; one shipping browser apps alone has no backend to hold it.
            if family.answers.get(BROWSER_APPS) and not isinstance(family.answers.get(SHARED_CODE), str):
                faults.append(f"family {family.name} ships a browser app and answers no shared_code, which the "
                              f"architecture page of a project with that browser app reads")
    return list(dict.fromkeys(faults))


# A conservative image reference: one run of letters, digits and `. _ - / : @ +`, not starting with a separator. It
# admits a registry host and port, a path, a tag and a digest, and no whitespace, quote or `#`: one YAML scalar.
IMAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:@+-]*")


def held(family: str, root: Path, answer: Any) -> list[str]:
    """A fault for an `npm_workspace` answer that is not one, for an image that is not a single-line reference, for a
    lock answer that cannot be called, and for each path it gives that is not a file (`biome` a directory) inside the
    package's root. The locks are asked of a selection at generation, and held there (`npm_workspace.held_lock`)."""
    if not isinstance(answer, NPM_WORKSPACE.kind):
        return [f"family {family} answers npm_workspace with {type(answer).__name__}, where an NpmWorkspace is wanted"]
    faults = [
        f"family {family} answers {field} with {type(getattr(answer, field)).__name__}, where a callable is wanted"
        for field in ("member_lock", "workspace_lock")
        if not callable(getattr(answer, field))
    ]
    if not isinstance(answer.image, str) or not IMAGE.fullmatch(answer.image):
        shown = f"{answer.image!r}, which is not a single-line image reference"
        faults.append(f"family {family} answers image with {shown}")
    pins = {f"biome_pins[{index}]": (pin, False) for index, pin in enumerate(answer.biome_pins)}
    paths: dict[str, tuple[Any, bool]] = {"biome": (answer.biome, True), **pins}
    for field, (value, tree) in paths.items():
        if not isinstance(value, Path):
            faults.append(f"family {family} answers {field} with {type(value).__name__}, where a Path is wanted")
        elif not value.resolve().is_relative_to(root.resolve()):
            faults.append(f"family {family} reaches outside its directory for {field}")
        elif not (value.is_dir() if tree else value.is_file()):
            kind = "directory" if tree else "file"
            faults.append(f"family {family} reaches for {field}, which is not a {kind} in its directory")
    return faults


def writes(
    family: str, root: Path, answer: Any, workspace: bool, declared: Mapping[str, Any] | None = None
) -> list[str]:
    """A fault for each way a family's `browser_apps` answer could not be read, all of them at once.

    `declared` is the package's `frontends` block, where it is known: the catalogue's half of the same answer.
    The two name the same browser apps, because `--frontend` offers the block's names and generation copies
    the answer's material, and a name in one and not the other is a menu entry with nothing behind it or a
    tree nobody can ask for. And each root is `assets/frontends/<name>` exactly, the one place a reviewer of
    a package that ships services, browser apps or both looks for a browser app.

    Four things are held, and each is a project somebody would otherwise only find out about at generation.
    The answer is a mapping of name to `BrowserApp`, because that is what `npm_workspace.frontends` iterates.
    Each record's `name` is the key it is listed under, because the name is what `--frontend` is typed as and
    a record disagreeing with its key would be reachable under one name and refuse under the other. Each
    `root` is a directory inside the package, for the reason every other source is: a browser app is copied
    into somebody's repository verbatim, and one assembled from outside the package is one nobody reviewed.

    And the family answers `npm_workspace` too. A browser app is an npm package in the project's one
    workspace; a family offering one without saying it has a workspace has no lock to resolve it with, and
    the refusal belongs at load, where it names the package, rather than at `npm ci` in a generated project.
    """
    if not isinstance(answer, BROWSER_APPS.kind):
        return [f"family {family} answers browser_apps with {type(answer).__name__}, where a mapping of "
                f"frontend name to BrowserApp is wanted"]
    faults: list[str] = []
    if answer and not workspace:
        faults.append(f"family {family} answers browser_apps without answering npm_workspace, and a browser "
                      f"app is an npm package in the workspace that answer declares")
    for name, app in answer.items():
        if not isinstance(app, BrowserApp):
            faults.append(f"family {family} answers browser_apps[{name}] with {type(app).__name__}, where a "
                          f"BrowserApp is wanted")
            continue
        if app.name != name:
            faults.append(f"family {family} lists a browser app called {app.name} under {name}, and the name "
                          f"is what `--frontend` is typed as")
        if not app.root.resolve().is_relative_to(root.resolve()):
            faults.append(f"family {family} reaches outside its directory for browser app {name}")
        elif not app.root.is_dir():
            faults.append(f"family {family} reaches for browser app {name}, which is not a directory in its "
                          f"directory")
        elif declared is not None and app.root.resolve() != (root / FRONTENDS_DIRECTORY / name).resolve():
            faults.append(f"family {family} keeps browser app {name} outside {FRONTENDS_DIRECTORY}/{name}, where "
                          f"a package keeps each browser app it ships")
    if declared is not None:
        answered = set(answer) if isinstance(answer, dict) else set()
        for name in sorted(set(declared) - answered):
            faults.append(f"language.json declares frontend {name}, and family {family} answers no browser_apps "
                          f"for it")
        for name in sorted(answered - set(declared)):
            faults.append(f"family {family} answers browser_apps[{name}], and language.json's frontends block "
                          f"does not declare it, so `--frontend` could never offer it")
    return faults


def placed(key: str, destination: str) -> list[str]:
    """A fault where a path a backend writes is not inside the service it is written to."""
    if isinstance(destination, str) and not outside(destination):
        return []
    return [f"backend {key} writes {destination!r}, which is not a path inside the service"]


def found(roots: tuple[Path, ...], relative: str, key: str, shown: str, tree: bool = False) -> list[str]:
    """A fault where a source leaves every root's `assets/` (or an `assets/` leaves its package), or is in none of
    them as a file (a directory for a tree). `roots` is the backend's own, then its family's."""
    if located(roots, relative, tree) is not None:
        return []
    for root in roots:
        try:
            inside(root / "assets", posixpath.normpath(relative), root)
        except ValueError:
            continue
        where = "its directory" if len(roots) == 1 else "its directory or its family's"
        return [f"backend {key} reaches for {shown}, which is not a {'directory' if tree else 'file'} in {where}"]
    return [f"backend {key} reaches outside its directory for {shown}"]


def roots_of(package: Package, language: Language) -> dict[str, Path]:
    """The package's own directory for each family and backend it declares."""
    return {key: package.root for key in (*(b.key for b in language.backends), *(f.name for f in language.families))}


def kept(
    known: Sequence[Language], package: Package, catalog: dict[str, Any] | None = None,
    roots: Mapping[str, Path] | None = None,
) -> Language | str:
    """The package's `LANGUAGE`, or the one line that says why it is refused. `known` is whatever it must load
    beside: the built-ins and every package kept before it. `catalog` is the merged catalog of exactly those and
    this package: the checks `cli.main` runs on the whole are run on it, so a package that would stop every verb
    is refused as itself, and only a built-in's fault is left to stop them."""
    try:
        language = import_package(package)
    except Refused as error:
        return str(error)
    module = module_name(package.name)

    def refused(fault: str) -> str:
        forget(module)  # a refused package is not left importable; what its code did at import is not undone
        return refusal(package.name, package.root, fault)

    try:
        beside = load([*known, language])
        # The roots of the packages kept before it too: a framework's sources are found in its family's (6a).
        registry_ = Registry(beside.families, beside.backends, {**(roots or {}), **roots_of(package, language)})
        faults = reaches(language, registry_, package.fragment.get("frontends", {}))
        if faults:
            return refused("; ".join(faults))
        if catalog is not None:
            validate_catalog(catalog, registry_)
    except ValueError as error:  # `RegistryError` too: the registry's and the catalog's own words
        return refused(said(error) or type(error).__name__)
    except BaseException as error:  # answers that are properties or callables run the package's code here
        return refused(f"{module} failed to load: {blame(error)}")
    return language


def without_later(catalog: dict[str, Any], later: Sequence[Package]) -> dict[str, Any]:
    """A copy of `catalog` with the packages not yet judged taken out, so that it holds what has been kept."""
    view = copy.deepcopy(catalog)
    for package in later:
        retract(view, package)
    return view


def sound(known: Sequence[Language], packages: Sequence[Package], catalog: dict[str, Any]) -> bool:
    """Whether the keel's own catalogue passes its checks before any package is folded in. If it does not
    it is the keel's fault, which stops the verb with its own words, and no package is blamed for it."""
    try:
        validate_catalog(without_later(catalog, packages), load(known))
    except Exception:  # noqa: BLE001 - this is the keel's own; whatever it fails is for `cli.main` to say
        return False
    return True


def build(
    known: Sequence[Language], packages: Sequence[Package], catalog: dict[str, Any], installed: bool = False
) -> tuple[Registry, list[str]]:
    """The registry of `known` and every package that loads, and a line for each package that does not,
    ending on its fix where the packages are the package directory's (`installed`).

    `known` is empty for the process's own registry: the keel has no language of its own. It is what the
    conformance suite passes when it holds one package against a registry built from nothing else.
    """
    load(known)
    languages: list[Language] = list(known)
    roots: dict[str, Path] = {}
    refused: list[str] = []
    # A framework imports its family's Python, so every family is imported before any framework (7b).
    packages = [*(p for p in packages if not is_framework(p)), *(p for p in packages if is_framework(p))]
    checked = sound(known, packages, catalog)
    loaded_names: set[str] = set()
    for index, package in enumerate(packages):
        family = next(iter(package.fragment["requires"])) if is_framework(package) else None
        if family is not None and family not in loaded_names:  # its family was refused at import
            need = f"requires {family} {package.fragment['requires'][family]}"
            ending = family_missing(package, family, str(catalog.get("schemaVersion", "")), installed, imported=True)
            result: Language | str = refusal(package.name, package.root, need + ending)
        else:
            view = without_later(catalog, packages[index + 1 :]) if checked else None
            result = kept(languages, package, view, roots)
            if isinstance(result, str) and installed:
                result += reinstall(package.name)
        if isinstance(result, str):
            refused.append(result)
            retract(catalog, package)
            continue
        languages.append(result)
        loaded_names.add(package.name)
        roots.update(roots_of(package, result))
    loaded = load(languages)
    order = list(catalog["backends"])
    backends = {key: loaded.backends[key] for key in order if key in loaded.backends}
    backends.update({key: backend for key, backend in loaded.backends.items() if key not in backends})
    names = [catalog["backends"][key]["family"] for key in order if key in backends]
    families = {name: loaded.families[name] for name in dict.fromkeys(names) if name in loaded.families}
    families.update({name: family for name, family in loaded.families.items() if name not in families})
    return Registry(families, backends, roots), refused


def registry() -> Registry:
    """The registry of this process: what `registry.registry()` caches.

    Version 1 passed the built-in languages first, from a package the keel named. Version 2 has none —
    every language is a package, and a `slipwai_language_*` import anywhere in `src/` fails the structure
    gate — so the first argument is empty and `build` is given the installed packages alone. It is still
    a parameter, because the conformance suite builds a registry from one package and nothing else.
    """
    built, refused = build((), PACKAGES, CATALOG, installed=True)
    PHASE_TWO[:] = refused
    return built


def refusals() -> list[str]:
    """Every package refused, in either phase, as the lines `cli.main` prints before the verb."""
    registry_module.registry()
    return [*REFUSALS, *PHASE_TWO]
