"""The public configuration contract, and everything that reads or checks it.

`catalog.json` is what a caller is allowed to ask for: the profiles, the languages, the frontends, and one
question per infrastructure role. The validation here runs before every generation, so a catalog that
cannot produce a working project is refused at the top of `main` rather than half-emitted.
"""
from __future__ import annotations

import json

from .assets import PRUNER, ROOT
from .axes import catalog_axis_default, validate_axes
from .errors import GenerationError
from .extensions import validate_extensions
from .targets import required_axes, validate_targets

CATALOG = json.loads((ROOT / "catalog.json").read_text())


def validate_catalog(catalog: dict) -> None:
    if catalog.get("schemaVersion") != 8:
        raise ValueError("catalog schemaVersion must be 8")
    expected_backends = {"typescript", "python", "go", "java-quarkus", "java-spring"}
    if set(catalog["backends"]) != expected_backends:
        raise ValueError("catalog must define exactly the five supported backends")
    validate_backends(catalog)
    # The pruner runs inside a generated project and reads `project.json`'s `language` — which is the
    # family, not the backend — so its own list has to be the catalog's families rather than its backends.
    # A family missing from it does not degrade into a smaller prune: `project_language` refuses outright,
    # and generation calls the pruner for any selection with a prunable feature, so the whole backend
    # fails at "project.json names an unsupported backend language" the first time it is asked for one.
    if set(PRUNER.LANGUAGES) != set(catalog_families(catalog)):
        raise ValueError(
            "catalog and assets/backing-services/prune.py disagree about the language families"
        )
    if set(catalog.get("frontends", {})) != {"none", "react-vite"}:
        raise ValueError("catalog must define the none and react-vite frontend capabilities")
    default = catalog["default"]
    # `.get` because `validate_axes` is what reports a malformed axis block, further down: a missing one
    # should reach its message rather than raise a KeyError here.
    if set(default) != {"profile", "target", "backend", "framework", "frontend", *catalog.get("axes", {})}:
        raise ValueError(
            "default must answer the profile, target, backend, framework, frontend and every axis"
        )
    if (default["profile"], default["backend"], default["frontend"]) != (
        "event-modelling",
        "typescript",
        "react-vite",
    ):
        raise ValueError("default must be event-modelling/typescript with the react-vite frontend")
    profiles = catalog["profiles"]
    event = profiles["event-modelling"]
    if event.get("extends") != "standard":
        raise ValueError("event-modelling must extend the standard profile")
    pair = {"event-modelling", "event-sourcing"}
    if set(event.get("indivisible", [])) != pair or not pair <= set(event["capabilities"]):
        raise ValueError("Event Modeling and event sourcing must be one indivisible bundle")
    for name, profile in profiles.items():
        capabilities = set(profile["capabilities"])
        if bool("event-modelling" in capabilities) != bool("event-sourcing" in capabilities):
            raise ValueError(f"{name}: Event Modeling and event sourcing cannot be selected separately")
        # The same rule the axis options are held to, for the question that matters most: an answer nobody
        # can read is not a choice being offered. Which foundation a project is born on is the one decision
        # a generated project cannot revisit later, so the prompt has to say what each one costs.
        if not profile.get("label"):
            raise ValueError(f"profile {name} must carry the label the prompt shows")
    validate_targets(catalog)
    validate_axes(catalog)
    validate_extensions(catalog)


def validate_backends(catalog: dict) -> None:
    """A backend is a language, and — where the ecosystem has one that owns startup — a framework.

    The two are one key rather than two independent axes because they do not combine independently: a
    framework that owns the composition root owns how every adapter behind every other axis is written,
    so `java` x `spring-boot` multiplies rather than crossing. Flattening it into the backend key is what
    keeps every per-backend table two-dimensional.

    The naming rule falls out of that, and it is about the framework rather than about how many siblings
    there are: **the bare language name means nothing owns startup, and a backend that has a framework is
    always suffixed with it** — as its family's only member just as much as beside a sibling. That is
    because `assets/languages/<family>/` holds the material a family shares, and a backend built around a
    framework is not that material even when it is the only one.

    The count-based version of this rule (bare while there is one member, suffixed once there are two) was
    the wrong shape for the ecosystems where a framework is the normal answer. It forced a new Java or C#
    backend to be keyed `java`, spelled as though nothing owned its startup, and then forced a rename the
    day a second framework arrived — the whole expense `.claude/skills/add-framework/` exists to cover, paid
    for a name that was never accurate. Keyed `java-spring` from the start, a sibling is purely additive.
    """
    backends = catalog["backends"]
    for name, backend in backends.items():
        if not backend.get("family"):
            raise ValueError(f"backend {name} must name the language family it belongs to")
        if not backend.get("label"):
            raise ValueError(f"backend {name} must carry the label the framework prompt shows")
    grouped = catalog_families(catalog)
    default_frameworks = catalog["default"]["framework"]
    if catalog["default"]["backend"] not in backends:
        raise ValueError("the default backend is not one this catalog defines")
    for family, members in grouped.items():
        if len(members) == 1:
            # Both directions of the naming rule, for the one case where the member count cannot settle
            # it. A lone backend with a framework is `java-spring`; a lone backend without one is `go`.
            framework = backends[members[0]].get("framework")
            if framework and members[0] == family:
                raise ValueError(
                    f"{members[0]} is built on {framework}, so it must be named for that too, not for "
                    f"the language alone: {family} names the material a family shares"
                )
            if not framework and members[0] != family:
                raise ValueError(
                    f"{family} has one backend and nothing owns its startup, so it must be named for "
                    f"the language itself, not {members[0]}"
                )
            # Still no default to make: one answer is not a choice, however it is spelled.
            if family in default_frameworks:
                raise ValueError(f"{family} has one backend, so it has no framework to default to")
            continue
        if family in members:
            raise ValueError(
                f"{family} has more than one backend, so none of them may be named {family} — that "
                "name belongs to the material they share"
            )
        frameworks = [backends[name].get("framework") for name in members]
        if not all(frameworks) or len(set(frameworks)) != len(frameworks):
            raise ValueError(f"every backend in {family} must name its own distinct framework")
        if default_frameworks.get(family) not in frameworks:
            raise ValueError(
                f"the default framework for {family} must be one of {', '.join(frameworks)}"
            )
    if set(default_frameworks) - set(grouped):
        raise ValueError("the framework default names a language family the catalog does not offer")


def catalog_families(catalog: dict) -> dict[str, list[str]]:
    """Each language family, and its backends in catalog order."""
    grouped: dict[str, list[str]] = {}
    for name, backend in catalog["backends"].items():
        grouped.setdefault(backend["family"], []).append(name)
    return grouped


def families() -> dict[str, list[str]]:
    return catalog_families(CATALOG)


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
        framework = CATALOG["default"]["framework"][language]
    for name in members:
        if framework_of(name) == framework:
            return name
    offered = ", ".join(str(framework_of(name)) for name in members)
    raise GenerationError(
        f"--framework {framework} is not implemented for {language}, which can be given {offered}"
    )


def axis_applies(axis: str, profile: str, backend: str, target: str) -> bool:
    """Whether this axis is a question worth asking of this profile, backend and target.

    An axis with only its no-infrastructure option left for a backend is not a choice, so it is not asked.
    """
    spec = CATALOG["axes"][axis]
    if profile not in spec["profiles"]:
        return False
    return len(axis_options(axis, backend, target)) > 1


def axis_required(axis: str, target: str) -> bool:
    """Whether this target refuses the axis's no-infrastructure answer — `aws` deploys an HTTP service."""
    return axis in required_axes(CATALOG, target)


def axis_options(axis: str, backend: str, target: str) -> list[str]:
    """The options of this axis implemented for this backend and offered under this target, in catalog order."""
    return [
        name
        for name, option in CATALOG["axes"][axis]["options"].items()
        if backend in option["backends"] and target in option["targets"]
    ]


def axis_default(axis: str, backend: str, target: str) -> str:
    return catalog_axis_default(CATALOG, axis, backend, target)
