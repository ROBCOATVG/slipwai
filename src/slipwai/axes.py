"""What an axis is, and what the catalog has to say about one before anything reads it.

An **axis** is one role asked as one question — how a service decides and records a write, how it keeps its
data, what accepts inbound HTTP, who authenticates the people who run the product, who authenticates the
people it is for. `validate_axes`
is the whole of what
`catalog.json` promises about them: the set is fixed, every option says which backends and targets it is
implemented for and which feature owns its files, and a default never resolves to nothing for a backend that
could have been given something. It lives beside `catalog.py` rather than inside it because the axis rules
are most of that module's length and none of its lookups.
"""
from __future__ import annotations

import copy
import itertools
from collections.abc import Collection
from typing import Any

from .assets import PRUNER
from .features import known_features, validate_traits
from .rungs import EVENTS, WRITE_MODEL
from .targets import validate_axis_targets

# An axis this keel has renamed, and the name it had. One table, read in three places: a `project.json`
# written before the rename (`manifest.reading`), a `language.json` written before it
# (`language_directory`), and `docs/rename.json`, which is the same row for the files `migrate` rewrites.
# Only the axis is renamed — `postgres` is still `postgres` — which is why a map of names is the whole of
# it. A row stays here for as long as anything that old could still be read, because a package silently
# dropping off the menu is worse than a refusal.
RENAMED = {"event-store": "persistence"}


def named_axes(answers: dict) -> dict:
    """A mapping keyed by axis, read under the names this keel now uses."""
    return {RENAMED.get(axis, axis): answer for axis, answer in answers.items()}


def under_current_names(fragment: dict[str, Any]) -> dict[str, Any]:
    """A `language.json` with every axis it names read under the name this keel now uses.

    A package answers axes by name in three places: the options each backend implements, the defaults it
    recommends, and the options the package declares itself. The keel is the one that renamed the axis, so
    a package built before the rename is read rather than dropped off the menu — the same courtesy a
    `project.json` written before it gets. Nothing else in the fragment moves: an option is still
    spelled `postgres`.
    """
    if not any(axis in RENAMED for axis in fragment_axes(fragment)):
        return fragment
    read = copy.deepcopy(fragment)
    if "axes" in read:
        read["axes"] = named_axes(read["axes"])
    for row in read["backends"].values():
        for key in ("options", "defaults"):
            if key in row:
                row[key] = named_axes(row[key])
        # A package that declared `event-store` was written when the store was the only place events could
        # live, so every project it generated was event-sourced. Renaming the axis alone would leave it
        # answering no `write-model` at all, and an axis no backend answers falls to its `absent` — which is
        # `state`. The package would not drop off the menu; it would quietly change the rung of every
        # project generated with it, which is the one answer this keel says cannot be walked back. So it is
        # read as answering the rung it was built for, and only that rung: the state-stored rows are what a
        # package adds when it is rebuilt on the protocol that has them.
        row.setdefault("options", {}).setdefault(WRITE_MODEL, [EVENTS])
    return read


def fragment_axes(fragment: dict[str, Any]) -> set[str]:
    """Every axis name a fragment uses, wherever it uses one."""
    rows = fragment.get("backends", {})
    return {
        *fragment.get("axes", {}),
        *(axis for row in rows.values() for key in ("options", "defaults") for axis in row.get(key, {})),
    }


def validate_axes(catalog: dict, packaged: Collection[str] = ()) -> None:
    """Each axis is one question with one answer, and the gates are data rather than scattered conditionals.

    An axis names the *role* being filled — how a service records a write, how it keeps its data, what
    accepts inbound HTTP, who authenticates internally, who authenticates externally — never a product, and
    never a protocol: every
    `auth` answer is an OIDC issuer, which is exactly why that axis is not called `oidc`. Naming the role is
    what lets `postgres` and `keycloak` stop being alternatives on one menu: they answer unrelated questions,
    so they are asked separately and answered independently. It is also why Keycloak answers two axes: who
    authenticates internally and who authenticates externally are different questions with the same kind of answer.

    Every option declares which backends it is implemented for, which targets it is offered under (see
    `targets.py`), which containers it needs, which marker
    feature owns its files, and — see `features.TRAITS` — whether that feature has migrations to apply and
    a suite the Docker-free gate cannot run. Those declarations are what the generator reads instead of
    naming a product, so a second container-backed store needs no new conditional. Nothing half-ported is
    emitted either: an unsupported combination is refused at the command line, naming the flag that would
    fix it.
    """
    axes = catalog.get("axes")
    if not isinstance(axes, dict) or set(axes) != {"write-model", "persistence", "http", "auth", "users"}:
        raise ValueError(
            "catalog must define exactly the write-model, persistence, http, auth and users axes"
        )
    backends = set(catalog["backends"])
    profiles = set(catalog["profiles"])
    for axis, spec in axes.items():
        options = spec.get("options")
        if not isinstance(options, dict) or not options:
            raise ValueError(f"the {axis} axis must offer at least the answer meaning 'no infrastructure'")
        # One option is a real state, not a broken catalogue: an axis whose answers are a language's —
        # `http` is — offers only `none` until a package brings one, and a keel with no package
        # installed has a short menu rather than an invalid one. The same reasoning as an option no
        # loaded backend answers being kept rather than refused.
        if not spec.get("prompt"):
            raise ValueError(f"the {axis} axis must carry the question the prompt asks")
        # The role, and what every answer to it has in common — the sentence that stops the axis being
        # renamed for a product or a protocol the next time somebody reads only its options.
        if not spec.get("description"):
            raise ValueError(f"the {axis} axis must describe what every answer to it has in common")
        if not set(spec.get("profiles", [])) <= profiles or not spec.get("profiles"):
            raise ValueError(f"the {axis} axis declares a profile the catalog does not offer")
        absent = spec.get("absent")
        if absent not in options:
            raise ValueError(f"the {axis} axis must name an option meaning 'no infrastructure'")
        if options[absent]["containers"]:
            raise ValueError(f"{axis}/{absent} means no infrastructure, so it cannot need a container")
        # An axis whose options are backend-specific cannot have one default: `fastify` is not an answer a
        # Go project can be given. So a default is either one answer for every backend or a map of one per
        # backend, and a backend this axis has nothing for falls back to the no-infrastructure answer — a
        # language can be added before its adapters are. What is refused is a default that *resolves* to
        # nothing for a backend which could have been given something, because that is a recommendation
        # that silently stopped being made.
        default = catalog["default"][axis]
        if not isinstance(default, (str, dict)):
            raise ValueError(f"the {axis} default must be one answer, or one answer per backend")
        for backend in sorted(backends):
            named = default.get(backend) if isinstance(default, dict) else default
            offered = [
                name
                for name, option in options.items()
                if name != absent and backend in option["backends"]
            ]
            if named is not None and named not in options:
                raise ValueError(f"the {axis} default '{named}' is not an option of that axis")
            if not offered:
                continue
            if named is None:
                raise ValueError(
                    f"the {axis} default names no answer for {backend}, which can be given "
                    f"{', '.join(offered)}"
                )
            if named != absent and backend not in options[named]["backends"]:
                raise ValueError(
                    f"the {axis} default '{named}' is not implemented for {backend}, which can be given "
                    f"{', '.join(offered)}"
                )
        for name, option in options.items():
            # An empty list is an option no loaded backend answers: the keel keeps the option, so a keel
            # that loaded no package for it does not offer it, which is not a fault.
            if not set(option["backends"]) <= backends:
                raise ValueError(f"{axis}/{name} declares a backend the catalog does not offer")
            # A feature is named for an option of its axis — `postgres` — or, where another axis already has
            # an option of that name, for the axis and the option together: `users-keycloak`, because a marker
            # named `keycloak` in a project answering both identity questions would say nothing. Any option of
            # the axis, not only this one: a target's own identity answer owns the `keycloak` feature,
            # because the files such a project carries *are* Keycloak's — the local stand-in — and one
            # region cannot have two
            # names.
            names = {f"{axis}-{other}" for other in options} | set(options)
            if set(option.get("features", [])) - names:
                raise ValueError(
                    f"{axis}/{name} declares a feature named neither for an option of its own axis nor "
                    f"{axis}-<option>"
                )
            if len(option.get("features", [])) > 1:
                # A marked region carries one name, and so does every table of prose, commands and pins
                # keyed by the feature that owns it. An option with two would have no single answer to
                # "which feature is this axis answered with", which is what those sites ask.
                raise ValueError(
                    f"{axis}/{name} owns more than one feature, and a marked region carries one name"
                )
            if not option.get("label"):
                raise ValueError(f"{axis}/{name} must carry the label the prompt shows")
            # What the answer gives the project, which is what decides the skills it is handed
            # (`capabilities.py`). Declared by every option, the empty list included, for the reason the
            # traits are: an answer that said nothing would silently give nothing.
            if not isinstance(option.get("capabilities"), list):
                raise ValueError(
                    f"{axis}/{name} must declare what it gives the project, as a list of capabilities"
                )
            validate_traits(axis, name, option, absent)
        validate_axis_targets(catalog, axis, spec, packaged)
        validate_axis_capabilities(axis, spec)
        for required_axis in spec.get("requires", []):
            if required_axis not in axes:
                raise ValueError(f"the {axis} axis requires an axis the catalog does not define")
            # A default that needs another axis answered is a default that generates nothing: the same
            # refusal `resolve_selection` raises for the flag would fire on an answer nobody gave.
            for target, backend in itertools.product(catalog["targets"], sorted(backends)):
                answer = catalog_axis_default(catalog, axis, backend, target)
                if answer == absent:
                    continue
                if catalog_axis_default(catalog, required_axis, backend, target) == axes[required_axis]["absent"]:
                    raise ValueError(
                        f"the {axis} default '{answer}' requires {required_axis}, which defaults to "
                        f"nothing for {backend} under the {target} target"
                    )
    # The in-memory adapter is not an alternative to a real store: it is what the port's contract runs
    # against in `make verify`, which is why it is `always` rather than an option's feature. That
    # distinction is what makes it un-prunable — there is no answer to this axis that drops it, so it is
    # never offered as something to lose, and the gate needs no Docker whichever store was chosen.
    if axes["persistence"]["always"] != ["memory"]:
        raise ValueError("the persistence axis must always ship the in-memory adapter its contract runs against")
    # The rung is the one answer that cannot be walked back, so it is never a flag `./init` offers: a
    # project that could answer it down would be a project that could silently throw its own history away.
    if axes["write-model"].get("prunable") is not False:
        raise ValueError(
            "the write-model axis must declare itself unprunable: a rung cannot be answered down later"
        )
    for axis, spec in axes.items():
        if set(spec.get("always", [])) & {
            feature for option in spec["options"].values() for feature in option["features"]
        }:
            raise ValueError(f"{axis}: a feature cannot be both always shipped and an option's to drop")
    # One feature, one axis: every table of prose, files and pins is keyed by feature, and `axis_of` has to
    # give one answer. Two axes each owning `keycloak` would be one marked region answering two questions.
    owners: dict[str, str] = {}
    for axis, spec in axes.items():
        for option in spec["options"].values():
            for feature in option["features"]:
                if feature in owners and owners[feature] != axis:
                    raise ValueError(
                        f"the {feature} feature is owned by both the {owners[feature]} and {axis} axes"
                    )
                owners[feature] = axis
    # The mirror holds the keel's two copies of one table to each other, and only those. An option a
    # package brought is declared in one place — the package — and travels into a project's pruner from
    # there, so there is no second copy to disagree with. Its own conformance suite is what checks it.
    brought = {feature for feature in known_features(catalog) if feature not in set(PRUNER.FEATURES)}
    missing = set(PRUNER.FEATURES) - known_features(catalog)
    if missing:
        raise ValueError(
            "assets/backing-services/prune.py knows features the catalog does not offer: "
            + ", ".join(sorted(missing))
        )
    del brought



def validate_axis_capabilities(axis: str, spec: dict) -> None:
    """The shipped pruner says what each answer gives, in the catalog's own words and the catalog's order.

    It has to: `./init --auth none` rewrites each deployable's `capabilities` in `project.json` with no
    catalog to hand, swapping the old answer's entries for the new one's in place — so a pruner that
    disagreed would write a manifest naming a capability nothing produces, and the project's own
    `check-agents` would go on justifying a skill by it. Two halves of one fact, checked the way `FEATURES`
    and the option targets are. Order and all, because the manifest's list is written in it.
    """
    # The keel's own options only; a package's is declared once and has nothing to mirror.
    shipped = PRUNER.AXES.get(axis, {}).get("options", {})
    for name, option in spec["options"].items():
        if name in shipped and list(shipped[name]["capabilities"]) != list(option["capabilities"]):
            raise ValueError(
                f"catalog and assets/backing-services/prune.py disagree about what {axis}/{name} gives"
            )


def catalog_axis_default(catalog: dict, axis: str, backend: str, target: str) -> str:
    """The answer an axis takes when nobody gives it one, for one backend going to one target.

    Per backend because the options are: `fastify` is not an answer a Go project can be given. A backend the
    default is not implemented for falls back to the axis's no-infrastructure answer, so a language can be
    added before its adapters are — the recommendation appears when the adapter does. Per target the same
    way, for the same reason.
    """
    spec = catalog["axes"][axis]
    default = catalog["default"][axis]
    absent = spec["absent"]
    chosen = default.get(backend, absent) if isinstance(default, dict) else default
    if chosen not in spec["options"]:
        return chosen  # an unknown answer: validate_axes reports it rather than hiding it here
    option = spec["options"][chosen]
    return chosen if backend in option["backends"] and target in option["targets"] else absent
