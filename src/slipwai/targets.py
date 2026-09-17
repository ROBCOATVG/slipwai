"""Where a project goes to production, and what that takes off its menus.

A **target** is the place a generated project is deployed to. `none` means local only: `make verify` is the
end of the road. It is asked right after the foundation because it decides the menus that follow — an option
declares the targets it is offered under beside the backends it is implemented for, and the same filter that
keeps `fastify` off a Go project's menu keeps a file-bound store off a cloud one. A backend declares its
targets too, so a target can be limited to the backends that can be built into an image for it.

Three rows ship: `none`, `aws` and `existing`. A target the factory *manages* (`"managed": true`) arrives with
its infrastructure and never before it — a catalog entry with nothing behind it would generate projects
claiming a destination they cannot reach, which is the half-ported shape this factory refuses everywhere else
— so `aws` arrived together with `infra/`, the image builds, the deploy pipeline and the per-target
provisioning of the options it carries. `existing` is the other kind: the project deploys somewhere the
factory does not own — a repository the method was installed around (brownfield adoption; experimental) has
its infrastructure already, described elsewhere or nowhere — so it offers what `none` offers, provisions
nothing, and turns on the documentation of where it goes and the release-constraint rung of `/drive` instead.
The second cloud is meant to be a fourth row in these same tables, not a second set of branches.

A target may `require` an axis: `aws` deploys an HTTP service, and `/health` is what proves a deploy, so
`--http none` cannot be taken there. The axis's no-infrastructure answer stays *offered* (an absent answer is
offered everywhere, so a menu never comes up empty) and is refused when chosen, naming both ways out.

A target may also `reserve` words a project's name cannot contain. A cloud names what it creates after the
project, and some of its services refuse their own brand inside those names — a Cognito hosted-login domain
is `<project>-<environment>-staff` and rejects any prefix containing `aws`, `amazon` or `cognito`. The name
is checked the moment the target is known, where it is still a choice, rather than partway through an apply
that has already created half a stack in somebody's account.

A cloud does not always refuse a word the same way, so `reserved` is a mapping from *how* to the words
refused that way rather than one flat list. Azure is why: it publishes three classes at once — `microsoft`
and `windows` are refused anywhere inside a name, about forty more (`azure`, `office`, `xbox`, `app_code`,
`web.config`, …) only as whole words, and `login` only at the start — and a list that means one of those
cannot express the other two. The classes are `anywhere` (a substring, which is what `aws`'s three words
always were), `word` (delimited by `.`, `_`, `-` or an end of the name, since those are the separators a
project name may contain) and `prefix`. A target declares the classes it needs and omits the rest.

Where an option is provisioned differently per target, that lives on the option under the target's key —
`postgres` says `"aws": {"provisions": "rds"}` — so the infrastructure generator reads a declaration rather
than a product name, exactly as the traits in `features.py` are read.
"""
from __future__ import annotations

import re

from .assets import PRUNER, ROOT
from .errors import GenerationError

TARGET_ROOT = ROOT / "assets/targets"

# How a cloud refuses a word it has reserved. `anywhere` is a substring anywhere in the name, `word` is the
# whole word between the separators a project name may contain, and `prefix` is the start of the name only.
# Ordered as they are checked and as a message lists them: widest refusal first.
RESERVED_CLASSES = ("anywhere", "word", "prefix")
# A project name is `[a-z0-9][a-z0-9._-]*`, so a word it could carry is alphanumeric runs joined by one
# separator. `web.config` and `app_code` are reserved words with a separator inside them.
RESERVED_WORD = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")
SEPARATORS = "._-"

# Per target: the command-line tools `./init` and `make bootstrap` run, each with why and where to get it.
# Here rather than in `preflight.py` because two things read it — that check before a project is written,
# and the generated `./init`'s own check on the machine that runs it — and they must name the same list or
# a project is refused for a tool its own script never looks for. `preflight` is the edge tier, which the
# generated parts may not import, so the fact lives with the target it is a fact about.
TOOLS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "aws": (
        ("tofu", "OpenTofu 1.12 — what applies the stacks in infra/", "https://opentofu.org/docs/intro/install/"),
        ("aws", "the AWS CLI — signs in to the account and configures the pipeline", "https://aws.amazon.com/cli/"),
    ),
    "azure": (
        ("tofu", "OpenTofu 1.12 — what applies the stacks in infra/", "https://opentofu.org/docs/intro/install/"),
        ("az", "the Azure CLI — signs in to the subscription and configures the pipeline", "https://learn.microsoft.com/cli/azure/install-azure-cli"),
    ),
}


def tools_for(target: str) -> list[str]:
    """Just the command names this target needs on the PATH, in the order a message lists them."""
    return [tool for tool, _why, _where in TOOLS.get(target, ())]


def managed(catalog: dict, target: str) -> bool:
    """Whether the factory provisions and deploys this target — `infra/`, the images, the pipeline. `none`
    and `existing` are not managed: the first goes nowhere, the second goes somewhere the factory does not own."""
    return bool(catalog["targets"][target].get("managed"))


def validate_targets(catalog: dict) -> None:
    """The targets block, the default, and every backend's declaration of where it is offered."""
    targets = catalog.get("targets")
    if not isinstance(targets, dict) or not targets:
        raise ValueError("catalog must define at least one production target")
    if "none" not in targets:
        raise ValueError("the targets must include none: local only is always an answer")
    for name, target in targets.items():
        if not target.get("label"):
            raise ValueError(f"target {name} must carry the label the prompt shows")
        required = target.get("requires", [])
        if not isinstance(required, list) or not set(required) <= set(catalog.get("axes", {})):
            raise ValueError(f"target {name} requires an axis the catalog does not define")
        if name == "none" and required:
            raise ValueError("the none target deploys nothing, so it cannot require an axis")
        reserved = target.get("reserved", {})
        if not isinstance(reserved, dict) or not set(reserved) <= set(RESERVED_CLASSES):
            raise ValueError(
                f"target {name}'s reserved words must be a mapping from how a word is refused "
                f"({', '.join(RESERVED_CLASSES)}) to the words refused that way"
            )
        for how, words in reserved.items():
            if not isinstance(words, list) or not words:
                raise ValueError(
                    f"target {name}'s reserved {how} words must be a non-empty list, or the class left out"
                )
            if not all(isinstance(word, str) and RESERVED_WORD.fullmatch(word) for word in words):
                raise ValueError(
                    f"target {name}'s reserved {how} words must be lowercase alphanumeric words, "
                    f"separated by '.', '_' or '-' as a project name may be, each one a name may not carry"
                )
        if reserved and not target.get("managed"):
            raise ValueError(
                f"target {name} provisions nothing, so it names nothing after the project and reserves no words"
            )
        if bool(target.get("managed")) != (TARGET_ROOT / name).is_dir():
            raise ValueError(
                f"target {name} {'is managed but has no' if target.get('managed') else 'is not managed yet has'} "
                f"assets/targets/{name}: a managed target arrives with its infrastructure, and only one"
            )
    if {name: tuple(target.get("requires", [])) for name, target in targets.items()} != {
        name: tuple(PRUNER.TARGET_REQUIRES.get(name, ())) for name in targets
    }:
        raise ValueError(
            "catalog and assets/backing-services/prune.py disagree about which axes a target requires"
        )
    default = catalog["default"].get("target")
    if default not in targets:
        raise ValueError(f"the default target '{default}' is not one this catalog defines")
    for name, backend in catalog["backends"].items():
        check_targets(f"backend {name}", backend, targets)


def check_targets(what: str, entry: dict, targets: dict) -> None:
    """An option or a backend says where it is offered: a non-empty subset of the catalog's targets."""
    declared = entry.get("targets")
    if not isinstance(declared, list) or not declared:
        raise ValueError(f"{what} must declare the targets it is offered under")
    if not set(declared) <= set(targets):
        raise ValueError(f"{what} declares a target the catalog does not offer")
    # What the option is provisioned as under a target, keyed by the target's name. Only under a target the
    # option is offered under: a provisioning nothing can select is a claim nothing checks.
    for target in targets:
        provisioning = entry.get(target)
        if provisioning is None:
            continue
        if target not in declared:
            raise ValueError(f"{what} says how it is provisioned under {target}, where it is not offered")
        if not isinstance(provisioning, dict) or not provisioning.get("provisions"):
            raise ValueError(f"{what}'s {target} entry must say what it provisions")


def validate_axis_targets(catalog: dict, axis: str, spec: dict) -> None:
    """Every option says where it is offered, "nothing" is offered everywhere, and the default still resolves.

    The no-infrastructure answer has to be offered under every target so that an axis always has an answer
    there. And the default is held to the rule it already meets per backend: under a target where the axis
    offers something real, a default that is not offered there would fall back to nothing — a recommendation
    that silently stopped being made — so it is refused instead.

    The shipped pruner carries the same declaration, because a generated project's `./init` filters by it
    without this catalog to hand; the two are the two halves of one fact, checked here the way `FEATURES` is.
    """
    targets = catalog["targets"]
    absent = spec["absent"]
    for name, option in spec["options"].items():
        check_targets(f"{axis}/{name}", option, targets)
    if set(spec["options"][absent]["targets"]) != set(targets):
        raise ValueError(
            f"{axis}/{absent} means no infrastructure, so it must be offered under every target"
        )
    shipped = PRUNER.AXES.get(axis, {}).get("options", {})
    for name, option in spec["options"].items():
        if name not in shipped or set(shipped[name]["targets"]) != set(option["targets"]):
            raise ValueError(
                f"catalog and assets/backing-services/prune.py disagree about where {axis}/{name} is offered"
            )
    default = catalog["default"][axis]
    for target in targets:
        for backend in sorted(catalog["backends"]):
            named = default.get(backend) if isinstance(default, dict) else default
            if named is None or named == absent or named not in spec["options"]:
                continue  # nothing to resolve, or a defect validate_axes reports by name
            if target in spec["options"][named]["targets"]:
                continue
            offered = [
                name
                for name, option in spec["options"].items()
                if name != absent and backend in option["backends"] and target in option["targets"]
            ]
            if offered and backend in spec["options"][named]["backends"]:
                raise ValueError(
                    f"the {axis} default '{named}' is not offered under the {target} target, which can be "
                    f"given {', '.join(offered)}"
                )


def offered_backends(catalog: dict, target: str) -> list[str]:
    """The backends a project going to this target may be written on, in catalog order."""
    return [name for name, backend in catalog["backends"].items() if target in backend["targets"]]


def required_axes(catalog: dict, target: str) -> list[str]:
    """The axes this target cannot take the no-infrastructure answer to."""
    return list(catalog["targets"][target].get("requires", []))


def reserved(catalog: dict, target: str) -> dict[str, list[str]]:
    """The words this target's cloud refuses, keyed by how it refuses them, in `RESERVED_CLASSES` order."""
    declared = catalog["targets"][target].get("reserved", {})
    return {how: list(declared[how]) for how in RESERVED_CLASSES if how in declared}


def reserved_words(catalog: dict, target: str) -> list[str]:
    """Every word a project's name may carry no part of, whichever way the target's cloud refuses it."""
    return [word for words in reserved(catalog, target).values() for word in words]


def carries(how: str, word: str, name: str) -> bool:
    """Whether this name falls foul of that word, refused that way."""
    if how == "anywhere":
        return word in name
    if how == "prefix":
        return name.startswith(word)
    delimiter = f"[{re.escape(SEPARATORS)}]"
    return re.search(rf"(?:^|{delimiter}){re.escape(word)}(?:{delimiter}|$)", name) is not None


# What the refusal says the cloud does with the word, in the sentence the message builds.
REFUSES = {
    "anywhere": "contains '{word}', which the {target} target reserves anywhere in a name",
    "word": (
        "uses '{word}' as a word, which the {target} target reserves: a name carries it as a word when "
        "it stands between the start or end of the name and one of '.', '_' or '-'"
    ),
    "prefix": "starts with '{word}', which the {target} target reserves at the start of a name",
}


def check_project_name(catalog: dict, target: str, name: str) -> None:
    """Refuse a project name the target's cloud will reject, naming the word and both ways out.

    Refused at generation and not at plan: the stack is one `tofu apply` and the resources that carry the
    name are created late in it, so a name the cloud will not take fails after the network, the cluster,
    the balancer and the distributions are already up — leaving somebody a half-built environment to clean
    out before they can try again. The word is in the project's name, which nothing but a rename can fix.
    """
    for how, words in reserved(catalog, target).items():
        for word in words:
            if not carries(how, word, name):
                continue
            raise GenerationError(
                f"project name '{name}' {REFUSES[how].format(word=word, target=target)}: this cloud names "
                f"what it creates after the project, and refuses its own brand inside those names — a stack "
                f"for this project would fail partway through its first apply. Generate with a name that "
                f"does not, or with --target none. The {target} target reserves "
                f"{len(reserved_words(catalog, target))} words in all, listed in docs/{target}-target.md."
            )


def provisioned_as(catalog: dict, axis: str, option: str, target: str) -> str | None:
    """What this option is provisioned as under this target — `rds`, `cognito` — or None where the target
    does nothing for it beyond carrying it."""
    entry = catalog["axes"][axis]["options"][option].get(target)
    return entry["provisions"] if entry else None
