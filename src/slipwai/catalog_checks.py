"""What makes a catalogue valid, and the one boundary where a fault in it becomes a refusal.

`catalog.py` is what the catalogue *is* and how to read it. This is what it has to be true of, which is a
different job with a different reader: nothing here is called while a project is being written, and
everything here is called before one starts.

Three things are checked at once, because a catalogue is wrong in three ways. Against its own schema —
every axis carries its question, every option its label. Against `assets/backing-services/prune.py`, the
file a generated project prunes itself with, because two implementations of one prune would be two sets
of bugs. And against the registry, because a backend listed here with no object behind it is a menu entry
that generates nothing.

The split from `catalog.py` was forced by the structure gate: that module was at its 350-line budget
exactly, and the refusal boundary did not fit. The budget was right — the two halves have no reader in
common.
"""
from __future__ import annotations

import json
from types import ModuleType

from .assets import PRUNER, this_command
from .axes import validate_axes
from .catalog import PACKAGES, SCHEMA_VERSION, TARGETS, catalog_families
from .errors import Fault, Refusal
from .extensions import validate_extensions
from .features import known_features
from .registry import PRUNE_ROWS, Registry, check_catalog, registry
from .targets import validate_targets


def validate_catalog(catalog: dict, loaded: Registry | None = None) -> None:
    """Refuse a catalogue that cannot produce a working project, in one line ending on what to run.

    `loaded` is the registry it is held against: the process's own, unless the loader is checking one
    package beside the ones already kept, where the registry is not built yet and asking for it would
    build it again.

    This is the boundary where a schema fault becomes a refusal a person reads, and the only place in the
    keel that knows enough to name a fix. The validators underneath say what is wrong — `axes.py` knows
    an option is missing a label, not whether the reader should edit a file or remove a package — so they
    raise `ValueError` and this turns it into a `Refusal`. Where packages are loaded, the catalogue is
    theirs as much as the keel's, and `list` is what shows whose; where none is, a wrong catalogue is a
    bug in this keel and there is no command that fixes it, so the refusal ends without one rather than
    sending the reader somewhere useless.
    """
    try:
        _check_catalog(catalog, loaded)
    except ValueError as wrong:
        fix = f"{this_command()} list" if PACKAGES else None
        raise Refusal(Fault(str(wrong), fix)) from wrong


def _check_catalog(catalog: dict, loaded: Registry | None = None) -> None:
    """Every rule the catalogue is held to, raising `ValueError` at the first that fails."""
    registered = registry() if loaded is None else loaded
    if catalog.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f'catalog schemaVersion must be "{SCHEMA_VERSION}"')
    check_catalog(catalog, registered)
    validate_backends(catalog)
    # The pruner runs inside a generated project and reads each family's rows, which the registry supplies;
    # rows it cannot read would fail at the first prune, inside generation, naming nothing a reader would
    # connect to the language that wrote them. So they are held to the script up front.
    check_prune_rows(registered, PRUNER, catalog)
    check_frontends(catalog)
    default = catalog["default"]
    # `.get` because `validate_axes` is what reports a malformed axis block, further down: a missing one
    # should reach its message rather than raise a KeyError here.
    # No backend: the default is the first of the merged catalog (`default_backend`), which no language names.
    if set(default) != {"profile", "target", "framework", "frontend", *catalog.get("axes", {})}:
        raise ValueError("default must answer the profile, target, framework, frontend and every axis")
    if default["profile"] != "event-modelling":
        raise ValueError("default must be the event-modelling profile")
    if default["frontend"] not in catalog["frontends"]:
        raise ValueError(f"default frontend {default['frontend']} is not one the catalog offers")
    profiles = catalog["profiles"]
    event = profiles["event-modelling"]
    if event.get("extends") != "standard":
        raise ValueError("event-modelling must extend the standard profile")
    check_rung(catalog)
    for name, profile in profiles.items():
        # The same rule the axis options are held to, for the question that matters most: an answer nobody
        # can read is not a choice being offered. Which foundation a project is born on is the one decision
        # a generated project cannot revisit later, so the prompt has to say what each one costs.
        if not profile.get("label"):
            raise ValueError(f"profile {name} must carry the label the prompt shows")
    packaged = [package.name for package in TARGETS]
    validate_targets(catalog, packaged)
    validate_axes(catalog, packaged)
    validate_extensions(catalog)


def check_frontends(catalog: dict) -> None:
    """The keel's `none` and every frontend a package brought, each with the capabilities it gives a project.

    The keel declares `none` and nothing else; a frontend named after a framework is a family's, folded in by
    `catalog_options.declare_frontends` with the family that ships it, and its shape held at load
    (`language_shape.frontend_shape_fault`). What is held here is what every reader assumes of the merge.
    """
    frontends = catalog.get("frontends", {})
    if not isinstance(frontends.get("none"), dict):
        raise ValueError("catalog must define the none frontend")
    for name, entry in frontends.items():
        if not isinstance(entry.get("capabilities"), list):
            raise ValueError(f"frontend {name} must list its capabilities")
        if name != "none" and not isinstance(entry.get("family"), str):
            raise ValueError(f"frontend {name} must name the family that ships it")


def check_rung(catalog: dict) -> None:
    """Event sourcing is a rung a service stands on, not a foundation a project is born with.

    Three rules where there was one bundle. The profile answered *is there a model?* and the storage
    decision by accident, so a product that wanted the model and not the log could not be generated, and
    neither could one with a context that earned the log beside three that did not. The bundle is now the
    `write-model` axis, asked per service, and these are what hold the catalogue to that: no profile may
    hand out `event-sourcing` (it is not a property of the whole project), the `events` rung must, and
    the modelled profile must carry both axes — the rung and the store it keeps its data in.
    """
    axes = catalog.get("axes", {})
    for name, profile in catalog["profiles"].items():
        if "event-sourcing" in profile["capabilities"]:
            raise ValueError(
                f"profile {name} carries event-sourcing, which is a rung a service stands on rather than a "
                "foundation a project is born with: declare it on the write-model/events option"
            )
    rung = axes.get("write-model", {}).get("options", {}).get("events", {})
    if "event-sourcing" not in rung.get("capabilities", []):
        raise ValueError("write-model/events must give the project the event-sourcing capability")
    for axis in ("write-model", "persistence"):
        if "event-modelling" not in axes.get(axis, {}).get("profiles", []):
            raise ValueError(f"the event-modelling profile must offer the {axis} axis")


ROW_KEYS = ("marked_files", "owned_files", "package_edits", "manifest")


def _paths(value: object) -> bool:
    """A sequence of path strings, which a bare string, though iterable, is not."""
    return isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value)


def outside(path: str) -> bool:
    """A path that is not inside the service: absolute, drive-lettered, climbing with `..`, or the service itself."""
    parts = path.replace("\\", "/").split("/")
    return (
        path[:1] in ("/", "\\")
        or path[1:2] == ":"
        or ".." in parts
        or all(part in ("", ".") for part in parts)
    )


def _escapes(owner: str, key: str, paths: object) -> list[str]:
    if not isinstance(paths, (list, tuple)):
        return []
    return [
        f"{owner}'s {key} names {path!r}, which is not a path inside the service"
        for path in paths
        if isinstance(path, str) and outside(path)
    ]


def row_faults(owner: str, rows: object, pruner: ModuleType, brought: frozenset[str] = frozenset()) -> list[str]:
    """What the pruning script could not read in one family's `prune_rows`, each fault a phrase naming `owner`.

    `brought` is every feature a loaded package's option declared. The shipped pruner's `FEATURES` are the
    keel's own; a transport's — `fastify`, `net-http` — arrives with the option that owns it and is folded
    into the project's copy at generation, so a family's rows may name it as readily as `postgres`.
    """
    if not isinstance(rows, dict) or set(rows) != set(ROW_KEYS):
        keys = sorted(rows) if isinstance(rows, dict) else type(rows).__name__
        return [f"{owner} answers prune_rows with keys {keys}, where the contract fixes {ROW_KEYS}"]
    faults = [] if _paths(rows["marked_files"]) else [f"{owner}'s marked_files is not a sequence of paths"]
    owned, edits, manifest = rows["owned_files"], rows["package_edits"], rows["manifest"]
    if not isinstance(owned, dict) or not all(_paths(paths) for paths in owned.values()):
        faults.append(f"{owner}'s owned_files is not a mapping of feature to a sequence of paths")
        owned = {}
    readable = isinstance(edits, dict) and all(
        isinstance(entry, dict) and set(entry) == {"packages", "scripts"} and all(map(_paths, entry.values()))
        for entry in edits.values()
    )
    if not readable:
        faults.append(f"{owner}'s package_edits is not a mapping of feature to its packages and scripts")
        edits = {}
    faults += _escapes(owner, "marked_files", rows["marked_files"])
    for paths in owned.values():
        faults += _escapes(owner, "owned_files", paths)
    faults += [
        f"{owner}'s prune_rows name {feature}, which is not a feature the pruner knows"
        for feature in sorted({*owned, *edits} - set(pruner.FEATURES) - brought)
    ]
    if manifest is not None and (not isinstance(manifest, str) or manifest not in pruner.UNINSTALLERS):
        faults.append(f"{owner}'s manifest {manifest!r} is not one the pruner can uninstall from")
    faults += [
        f"{owner}'s package_edits for {feature} name packages with no manifest to remove them from"
        for feature, entry in edits.items()
        if manifest is None and (entry["packages"] or entry["scripts"])
    ]
    return faults


def _emitted(rows: object) -> object:
    """Rows as the script will read them, which is their JSON form: a tuple and a list are the same row."""
    try:
        return json.loads(json.dumps(rows))
    except (TypeError, ValueError):
        return repr(rows)


def check_prune_rows(loaded: Registry, pruner: ModuleType, catalog: dict | None = None) -> None:
    """Refuse `prune_rows` the pruning script cannot read, and two backends of one family answering differently.

    The script reads a service's `language`, which is the family, so a family has one set of rows; a backend
    that overrides them would be pruned by its family's regardless.
    """
    faults: list[str] = []
    first: dict[str, tuple[str, object]] = {}
    brought = frozenset(known_features(catalog)) if catalog else frozenset()
    for key, backend in loaded.backends.items():
        rows = loaded.answer(key, PRUNE_ROWS)
        family = backend.family
        if family not in first:
            first[family] = (key, rows)
            faults += row_faults(f"family {family}", rows, pruner, brought)
        elif _emitted(rows) != _emitted(first[family][1]):
            faults.append(
                f"backend {key} answers prune_rows differently from backend {first[family][0]} of "
                f"family {family}, whose projects both record the language {family}"
            )
    if faults:
        raise ValueError("; ".join(dict.fromkeys(faults)))


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
        # No default is an answer (a family package's default no loaded framework answers is left out, D51);
        # a default naming none of the family's frameworks is not.
        if family in default_frameworks and default_frameworks[family] not in frameworks:
            raise ValueError(
                f"the default framework for {family} must be one of {', '.join(frameworks)}"
            )
    if set(default_frameworks) - set(grouped):
        raise ValueError("the framework default names a language family the catalog does not offer")
