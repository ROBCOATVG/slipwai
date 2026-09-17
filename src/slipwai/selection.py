"""One answer per axis: the whole of what a project was asked to be given."""
from __future__ import annotations

from .assets import PRUNER
from .catalog import CATALOG, axis_applies, axis_default, axis_options, axis_required
from .errors import GenerationError
from .features import axis_of, feature_declaring, known_features


class Selection:
    """One option per axis: the whole of what a project was asked to be given.

    Everything downstream reads this rather than a flat list of service names, because a flat list cannot
    answer the question the generator actually asks — "which event store did they choose?" — without
    guessing from membership.
    """

    def __init__(self, choices: dict[str, str]) -> None:
        self.choices = dict(choices)

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"Selection({self.choices!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Selection) and other.choices == self.choices

    def option(self, axis: str) -> str:
        """The chosen option, or the axis's no-infrastructure answer when the axis was not asked."""
        return self.choices.get(axis, CATALOG["axes"][axis]["absent"])

    def has(self, feature: str) -> bool:
        return feature in self.features

    def feature_of(self, axis: str) -> str | None:
        """The feature this axis's answer owns, or None when the answer owns no files.

        Marked regions are named after a feature, and so is every table of prose, commands and pins that
        belongs to one — so a site that has to name the answer to an axis asks here rather than testing for
        a product. One feature and not a set: a region carries exactly one name, which `validate_axes`
        holds every option to.
        """
        features = CATALOG["axes"][axis]["options"][self.option(axis)]["features"]
        return features[0] if features else None

    def axis_of(self, feature: str) -> str:
        """The role a selected feature fills, for prose that has to name the role rather than the product."""
        return axis_of(CATALOG, feature)

    @property
    def migrating_feature(self) -> str | None:
        """The selected feature whose schema `make migrate` applies, or None when nothing needs migrating.

        Declared by the option in `catalog.json` rather than inferred: an embedded store has a schema too,
        and the difference is who applies it.
        """
        return feature_declaring(CATALOG, self.choices, "migrations")

    @property
    def integration_feature(self) -> str | None:
        """The selected feature whose contract only real infrastructure can prove, or None.

        Its suite is what `make test-integration` runs and what the default gate deliberately excludes,
        which is how `make verify` stays runnable on a machine with no Docker.
        """
        return feature_declaring(CATALOG, self.choices, "integration-suite")

    @property
    def axes(self) -> list[str]:
        return [axis for axis in CATALOG["axes"] if axis in self.choices]

    @property
    def features(self) -> list[str]:
        """Every feature whose files this selection emits.

        Includes each asked axis's `always` features — the in-memory event store, which arrives with any
        answer to the event-store question — as well as the chosen option's own.
        """
        owned = set(self.prunable_features)
        for axis in self.axes:
            owned |= set(CATALOG["axes"][axis]["always"])
        return sorted(owned)

    @property
    def prunable_features(self) -> list[str]:
        """The features a later `./init` could still take away: the chosen options', and nothing always-on.

        This is what the pruner is given. Handing it an always-on feature would ask it to reason about
        something it cannot drop.
        """
        owned = {
            feature
            for axis, chosen in self.choices.items()
            for feature in CATALOG["axes"][axis]["options"][chosen]["features"]
        }
        return [feature for feature in sorted(known_features(CATALOG)) if feature in owned]

    @property
    def containers(self) -> list[str]:
        """Compose services the selection needs. SQLite and the in-memory store need none, which is what
        keeps a project that chose them free of docker-compose.yml entirely."""
        return [
            container
            for axis, chosen in self.choices.items()
            for container in CATALOG["axes"][axis]["options"][chosen]["containers"]
        ]

    @property
    def capabilities(self) -> list[str]:
        return [
            capability
            for axis, chosen in self.choices.items()
            for capability in CATALOG["axes"][axis]["options"][chosen]["capabilities"]
        ]

    @property
    def prunable(self) -> bool:
        """Whether any axis still has an answer that could be taken away.

        An axis sitting at its no-infrastructure answer has nothing left to drop, so a selection made
        entirely of those needs no prune script and no `./init` flags.
        """
        return any(
            self.option(axis) != CATALOG["axes"][axis]["absent"] for axis in self.axes
        )

    @property
    def summary(self) -> dict[str, str]:
        """What project.json records: the answer to every axis that was asked."""
        return {axis: self.choices[axis] for axis in self.axes}


def resolve_selection(
    named: dict[str, str | None], profile: str, backend: str, target: str
) -> Selection:
    """Turn the axis flags into one validated Selection, refusing what cannot be built.

    A refusal always names the flag that would fix it, because the alternative — emitting a project whose
    adapter is missing and whose configuration still demands it — passes every gate and fails at runtime.
    """
    choices: dict[str, str] = {}
    for axis, spec in CATALOG["axes"].items():
        chosen = named.get(axis)
        offered = axis_options(axis, backend, target)
        if chosen is None:
            if axis_applies(axis, profile, backend, target):
                choices[axis] = axis_default(axis, backend, target)
            continue
        if chosen not in spec["options"]:
            raise GenerationError(
                f"unknown --{axis} value '{chosen}'; this factory offers "
                f"{', '.join(offered) or spec['absent']} for the {backend} backend"
            )
        if chosen == spec["absent"]:
            # Asking for no infrastructure is always a legal answer, including on a backend where the axis
            # offers nothing else and is therefore never asked — except under a target that deploys the
            # answer: `aws` runs an HTTP service and proves a deploy by asking it `/health`, so a service
            # with nothing listening cannot be taken there.
            if axis_required(axis, target) and profile in spec["profiles"]:
                usable = [name for name in offered if name != spec["absent"]]
                raise GenerationError(
                    f"--{axis} {chosen} cannot be taken to the {target} target: it deploys {axis} services and "
                    f"proves a deploy by asking one for /health, so a service with none has nothing to deploy. "
                    f"Generate with --{axis} {usable[0] if usable else '<option>'}, or with --target none."
                )
            if axis_applies(axis, profile, backend, target):
                choices[axis] = chosen
            continue
        option = spec["options"][chosen]
        alternative = next((name for name in offered if name != spec["absent"]), spec["absent"])
        if backend not in option["backends"]:
            implemented = "/".join(option["backends"])
            raise GenerationError(
                f"--{axis} {chosen} is implemented for the {implemented} backend only, and this project's "
                f"backend is {backend}: a half-ported version is deliberately not emitted. Generate with "
                f"--{axis} {alternative}, or with --backend {option['backends'][0]}."
            )
        if target not in option["targets"]:
            # Same voice as the refusal above, for the other dimension an option is offered along: an
            # answer the target cannot carry would generate a project claiming a destination it cannot reach.
            offered_under = "/".join(option["targets"])
            raise GenerationError(
                f"--{axis} {chosen} is offered under the {offered_under} target only, and this project's "
                f"target is {target}: a project that cannot take its {axis} where it is going is deliberately "
                f"not emitted. Generate with --{axis} {alternative}, or with --target {option['targets'][0]}."
            )
        if profile not in spec["profiles"] and chosen != spec["absent"]:
            reason = (
                "the event store is the driven port behind event sourcing, and the standard "
                "profile has no such port"
                if axis == "event-store"
                else f"the {axis} axis is only wired for the {'/'.join(spec['profiles'])} profile"
            )
            raise GenerationError(
                f"--{axis} {chosen} cannot be added to the {profile} profile: {reason}. Generate with "
                f"--profile {spec['profiles'][0]}, or with --{axis} {spec['absent']}."
            )
        if profile not in spec["profiles"]:
            continue
        choices[axis] = chosen

    selection = Selection(choices)
    for axis, spec in CATALOG["axes"].items():
        chosen = selection.option(axis)
        if chosen == spec["absent"]:
            continue
        for required_axis in spec.get("requires", []):
            required = CATALOG["axes"][required_axis]
            if selection.option(required_axis) != required["absent"]:
                continue
            # Named for this backend, not for the first option in the catalog: telling a Python project to
            # choose Fastify is a refusal that cannot be acted on.
            usable = [
                name
                for name in axis_options(required_axis, backend, target)
                if name != required["absent"]
            ]
            fix = (
                f"--{required_axis} {usable[0]}"
                if usable
                else f"--{axis} {spec['absent']}, since this backend has no {required_axis} option yet"
            )
            raise GenerationError(
                f"--{axis} {chosen} needs an inbound HTTP entry point, and this project has "
                f"--{required_axis} {selection.option(required_axis)}: {PRUNER.REQUIRES_BECAUSE[axis]} "
                f"Generate with {fix}, or with --{axis} {spec['absent']}."
            )
    return selection


def transport_feature(selection: Selection) -> str | None:
    """The selected transport's feature name, or None when the project has no inbound HTTP.

    Marker regions are named after a feature, and the transports are one per backend — so the
    prose and the environment keys they own are written once and stamped with whichever transport
    this project was given, rather than triplicated per framework.
    """
    return selection.feature_of("http")
