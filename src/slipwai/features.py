"""What a feature is, and what an option may declare about the one it owns.

An **option** is one answer to an axis; a **feature** is the marker name that owns its files and its marked
regions. What the generator actually asks about a selection is never "is this Postgres" — it is "does
anything here need migrating", "does anything here bring a suite the Docker-free gate cannot run". Those
are properties of the answer, so an option declares them here as **traits**, `validate_axes` refuses an
option that leaves one unstated, and every site reads the trait through `Selection` instead of testing for
a product name.

That is the whole point of this module: the second container-backed store is a catalog entry plus its
assets, and no new conditional anywhere in this package.
"""
from __future__ import annotations

from .errors import GenerationError

# What an option declares about the feature it owns, and what each declaration buys:
#
# - `migrations` — this option's schema is applied by a step of its own, so the project gets a `make
#   migrate` target inside the feature's marked region and the extended CI gate runs it before the
#   integration suite. An embedded store whose adapter carries its own schema declares `false`: there is
#   nothing to apply, and a target that ran nothing would be worse than its absence.
# - `integration-suite` — this option's contract can only be proved against real infrastructure, so its
#   tests live outside `make verify` — which must stay runnable with no Docker — and `make
#   test-integration` is what runs them.
#
# Both are declared by every option, `false` included, rather than defaulted: a trait left unstated is a
# `make migrate` the project needed and silently never got.
TRAITS = ("migrations", "integration-suite")


def validate_traits(axis: str, name: str, option: dict, absent: str) -> None:
    """Refuse an option whose traits are unstated, or that cannot carry the ones it claims.

    A trait is carried by one marked region and read out of tables keyed on the feature that owns it, so an
    option claiming one has to own exactly that: one feature. The axis's no-infrastructure answer can claim
    neither — there is nothing there to migrate and nothing to prove against.
    """
    for trait in TRAITS:
        if not isinstance(option.get(trait), bool):
            raise ValueError(f"{axis}/{name} must declare whether it needs {trait}: true or false")
        if not option[trait]:
            continue
        if name == absent:
            raise ValueError(f"{axis}/{absent} means no infrastructure, so nothing there needs {trait}")
        if len(option["features"]) != 1:
            raise ValueError(
                f"{axis}/{name} declares {trait}, so it must own exactly one feature: that is the name "
                "the marked region carrying it is written under"
            )


def known_features(catalog: dict) -> set[str]:
    """Every *prunable* marker feature, across all axes.

    An axis's `always` features are deliberately excluded: nothing can drop them, so the pruner has no
    business knowing how. This is the set the pruner's own feature list is checked against.
    """
    return {
        feature
        for spec in catalog["axes"].values()
        for option in spec["options"].values()
        for feature in option["features"]
    }


def axis_of(catalog: dict, feature: str) -> str:
    """The axis whose answer owns this feature — the *role* it fills, for prose that has to name the role.

    "Apply the event-store migrations" is a true sentence about whichever store was chosen, and stays true
    for the next one; "apply the Postgres migrations" is a sentence that has to be rewritten.
    """
    for axis, spec in catalog["axes"].items():
        for option in spec["options"].values():
            if feature in option["features"]:
                return axis
    raise ValueError(f"no axis offers the {feature} feature")


def feature_declaring(catalog: dict, choices: dict[str, str], trait: str) -> str | None:
    """The selected feature that declares this trait, or None when nothing selected does.

    One or none, because a generated project has one `make migrate` target and one integration command. Two
    answers each owning the same trait is a real thing to want one day — a store and a deploy target that
    both migrate — and it needs those targets generalised first, so it is refused here with the reason
    rather than emitted as a Makefile with two definitions of one target.
    """
    owners = [
        feature
        for axis, chosen in choices.items()
        for feature in catalog["axes"][axis]["options"][chosen]["features"]
        if catalog["axes"][axis]["options"][chosen][trait]
    ]
    if len(owners) > 1:
        raise GenerationError(
            f"{' and '.join(owners)} both declare {trait}, and a generated project has one target for it: "
            "answering two axes with services that each own it needs that target generalised first"
        )
    return owners[0] if owners else None
