"""The public configuration contract, and everything that reads or checks it.

`catalog.json` is what a caller is allowed to ask for: the profiles, the languages, the frontends, and one
question per infrastructure role. The validation here runs before every generation, so a catalog that
cannot produce a working project is refused at the top of `main` rather than half-emitted.
"""
from __future__ import annotations

import json

from .assets import ROOT, this_command
from .axes import catalog_axis_default
from .catalog_merge import merge
from .errors import GenerationError
from .extension_directory import read as read_extensions
from .extensions import merge_packages
from .language_directory import directory, read
from .target_directory import merge_targets
from .target_directory import read as read_targets
from .targets import required_axes

# The keel's own file: the backends it still carries, each with an `order`, and the schema version a language
# package's `core` range is held to.
CORE = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
SCHEMA_VERSION = "9.0"
# The targets first, and before the languages for one reason: a backend declares the targets it is offered
# under, and a backend naming a cloud can only be read once that cloud's row is in the tables. The keel's own
# file carries `none` and `existing`; every other row, and every answer that is a cloud's, arrives here.
TARGETS, _TARGET_REFUSALS = read_targets(directory(), CORE["schemaVersion"], installed=True)
_TARGET_MERGE_REFUSALS = merge_targets(CORE, TARGETS)
TARGETS = [one for one in TARGETS if one.name in CORE["targets"]]
# Phase 1 of the package directory: the fragments this keel can load, then the merge, which refuses a
# fragment alone. `PACKAGES` are the ones that merged; `REFUSALS` say, a line each, why the others did not.
_FOUND, _FRAGMENT_REFUSALS = read(directory(), CORE["schemaVersion"], installed=True)
CATALOG, _MERGE_REFUSALS, UNREACHABLE = merge(CORE, _FOUND, installed=True)
# What a loaded package answers that this installation cannot reach, as the line `slipwai list` prints under
# it. Not a refusal and never printed as one: the package works and the rest of its answers are offered. It
# is said at all because the alternative is silence — a person who installed a language to deploy to a cloud,
# and has not installed that cloud, would otherwise find the target missing from the menu with nothing
# anywhere saying why. `catalog_merge.reachable` is what took them out, and says why there.
UNREACHABLE_NOTES = {
    name: f"\n      not reachable here: {', '.join(gone)}"
          f"\n      no installed target offers them: {this_command()} target list"
    for name, gone in UNREACHABLE.items()
}
PACKAGES = [package for package in _FOUND if package.name not in _MERGE_REFUSALS]
# The same directory's other kind of package. An extension adds a catalogue entry and a directory of files
# `./init` runs; it merges nothing into the backends, so it is folded in after the language merge rather
# than through it.
EXTENSIONS, _EXTENSION_REFUSALS = read_extensions(directory(), CORE["schemaVersion"], installed=True)
_COLLISIONS = merge_packages(CATALOG, EXTENSIONS)
EXTENSIONS = [one for one in EXTENSIONS if CATALOG["extensions"].get(one.name) == one.entry]
REFUSALS: list[str] = [*_TARGET_REFUSALS, *_TARGET_MERGE_REFUSALS, *_FRAGMENT_REFUSALS,
                       *_MERGE_REFUSALS.values(), *_EXTENSION_REFUSALS, *_COLLISIONS]


def catalog_families(catalog: dict) -> dict[str, list[str]]:
    """Each language family, and its backends in catalog order."""
    grouped: dict[str, list[str]] = {}
    for name, backend in catalog["backends"].items():
        grouped.setdefault(backend["family"], []).append(name)
    return grouped


def families() -> dict[str, list[str]]:
    return catalog_families(CATALOG)


def default_backend(catalog: dict | None = None) -> str | None:
    """The backend a project gets when it names none: the first of the merged catalog, which the merge orders by
    `(order, declared position)`, so it is the first menu entry too. None where no language is loaded."""
    return next(iter((CATALOG if catalog is None else catalog)["backends"]), None)


def default_language(catalog: dict | None = None) -> str:
    """The default backend's family, or the one line that says there is none to default to."""
    backend = default_backend(catalog)
    if backend is None:
        raise GenerationError("no language is loaded, so there is no default backend: name one with --backend")
    return (CATALOG if catalog is None else catalog)["backends"][backend]["family"]


def family_of(backend: str) -> str:
    """The language a backend is written in, which is not always the backend's own name."""
    return CATALOG["backends"][backend]["family"]


def framework_of(backend: str) -> str | None:
    """The framework that owns this backend's startup, or None where nothing does."""
    return CATALOG["backends"][backend].get("framework")


def resolve_backend(language: str, framework: str | None) -> str:
    """The backend key a language plus a framework names.

    The command line and the prompt both ask these as two questions, because "which language" and "which
    framework" are how people actually decide. Everything downstream is keyed by the single backend this
    resolves to.
    """
    members = families().get(language)
    if not members:
        raise GenerationError(
            f"unknown language '{language}'; this factory offers {', '.join(families())}"
        )
    if len(members) == 1:
        only = framework_of(members[0])
        if framework is not None and framework != only:
            # Two different refusals, because a single-member family is now two different situations. A
            # lone backend may have a framework — `java-spring` before Quarkus arrives — and telling its
            # caller that nothing owns startup there would be false.
            if only is None:
                raise GenerationError(
                    f"--framework {framework} is not an answer the {language} backend can be given: "
                    f"nothing owns startup there, so there is no framework to choose"
                )
            raise GenerationError(
                f"--framework {framework} is not implemented for {language}, which this factory offers "
                f"with {only} only"
            )
        return members[0]
    if framework is None:
        framework = CATALOG["default"]["framework"].get(language)
    if framework is None:
        offered = " or ".join(str(framework_of(name)) for name in members)
        raise GenerationError(f"{language} has no default framework loaded; pass --framework {offered}")
    for name in members:
        if framework_of(name) == framework:
            return name
    offered = ", ".join(str(framework_of(name)) for name in members)
    raise GenerationError(
        f"--framework {framework} is not implemented for {language}, which can be given {offered}"
    )


def axis_applies(axis: str, profile: str, backend: str, target: str) -> bool:
    """Whether this axis is a question worth asking of this profile, backend and target.

    Three ways it is not. The profile does not carry the axis. Only the no-infrastructure option is left
    for this backend, so there is nothing to choose between. Or the axis is **inferred**: its answer
    follows from something already decided, and asking would be asking the reader to repeat themselves.

    `http` is the inferred one. A backend answers exactly one transport — its framework's — so the
    question was never "which?", and a generated project's first application is a service, so it was
    never "whether?" either. The answer is the backend's own default. `none` stays an option for the
    backend that offers no transport at all, and for an adopted repository that reports having none.
    """
    spec = CATALOG["axes"][axis]
    if profile not in spec["profiles"] or spec.get("inferred"):
        return False
    return len(axis_options(axis, backend, target)) > 1


def axis_inferred(axis: str) -> bool:
    """Whether this axis is never asked, its answer following from the backend."""
    return bool(CATALOG["axes"][axis].get("inferred"))


def axis_prunable(axis: str) -> bool:
    """Whether a generated project's `./init` may answer this axis down later.

    Every infrastructure axis may: a project that chose Postgres can drop to the in-memory adapter, and
    pruning only ever subtracts. The rung cannot. `--write-model state` on a service that has been keeping
    a log would not take an adapter away, it would declare that the history on disk is no longer the
    truth — which is a migration somebody writes, not a flag. So the axis declares itself unprunable and
    `./init` never offers it.
    """
    return CATALOG["axes"][axis].get("prunable", True) is not False


def axis_required(axis: str, target: str) -> bool:
    """Whether this target refuses the axis's no-infrastructure answer: a target that deploys an HTTP
    service and proves the deploy by asking it for `/health` cannot be given `--http none`."""
    return axis in required_axes(CATALOG, target)


def axis_choices(axis: str) -> list[str]:
    """The options of this axis that can be named at all: the absent one, and any some loaded backend answers.

    The merge leaves an option with no backends where the one language that answered it is not loaded, so
    that option is as unknown as one the catalog never had.
    """
    spec = CATALOG["axes"][axis]
    return [name for name, option in spec["options"].items() if name == spec["absent"] or option["backends"]]


def axis_options(axis: str, backend: str, target: str) -> list[str]:
    """The options of this axis implemented for this backend and offered under this target, in catalog order."""
    return [
        name
        for name, option in CATALOG["axes"][axis]["options"].items()
        if backend in option["backends"] and target in option["targets"]
    ]


def axis_default(axis: str, backend: str, target: str) -> str:
    return catalog_axis_default(CATALOG, axis, backend, target)
