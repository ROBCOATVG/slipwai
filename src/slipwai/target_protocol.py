"""The target protocol: every answer a place a project is deployed to gives, and which are required.

A language package exports `LANGUAGE` and answers the backend protocol (`registry.py`). A target package
exports `TARGET` and answers this one. Every member is a thing the keel asks a cloud, and each was read
from exactly one place in the keel before this existed — a table keyed by a cloud's name — so a package
answering them replaces a branch rather than adding one:

- `shapes` — the stacks, as committed HCL, under the two names a managed target always has. `project/infra`
  copies them.
- `scripts` — what a project gets under `scripts/` to bootstrap the account and deploy into it.
- `docs_pages` — the production ADR and the deployment diagram, which were a module per cloud.
- `tools` — the command-line tools `./init` and `make bootstrap` need, each with why and where to get it;
  the list `preflight` checks before a project is written *and* the generated `./init` checks on the
  machine that runs it, so there is one list and not two.
- `image_registry` — where a built image is pushed, what the registry is called, one of its addresses as an
  example, and what `infra/` runs a service as; the four words `scripts/deploy.py` is written round.
- `pipeline` — the parts of the deploy workflow that are this cloud's: the CLI a runner may not ship, how a
  job becomes the deploy identity, how it signs in to the registry, and what the stacks read out of the
  environment. The job's *shape* stays the keel's, so a target supplies parts and never rewrites the promise.
- `readme_words` — the nouns the README's *Production* section is written round.
- `agent_rules` — the paragraph an agent is held to about how this project reaches production.
- `add_commands` — what `add-service` and `add-frontend` say afterwards about the destination.

**Required means required of a managed target.** `managed` is the catalog's own word for "the keel
provisions and deploys this": its stacks, its images, its pipeline. A target that is not managed — a
project deploying somewhere the keel does not own — answers none of this, and that is the whole difference
between the two rows. Holding an unmanaged target to stacks it has no business shipping would make the one
honest unmanaged row impossible to write.

**Two shapes, named here.** Every managed target has an account stack applied once and a service stack
applied per environment. Naming the pair here rather than letting each package choose means
`make bootstrap` and `make deploy` mean the same thing on every cloud.

This module imports nothing but the foundation and the name rule, so a package's answer can be held to its
shape without the catalog, the selection or any part of a project being read.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from .language_shape import name_fault

T = TypeVar("T")

#: The stacks every managed target has: the account's, applied once by `make bootstrap`, and the service's,
#: applied per environment by `make deploy`. Declared here so the two verbs mean one thing on every cloud.
BOTH_SHAPES = ("bootstrap", "service")


@dataclass(frozen=True)
class TargetMember(Generic[T]):
    """One answer a target gives: its name, whether a managed target owes it, and the shape it must have."""

    name: str
    required: bool
    kind: Any
    shape: str


M = TargetMember
SHAPES: TargetMember[Any] = M("shapes", True, dict, "shape -> the package's files that stack is made of")
SCRIPTS: TargetMember[Any] = M("scripts", True, dict, "path in the project -> the package file it comes from")
DOCS_PAGES: TargetMember[Any] = M("docs_pages", True, dict, "path in the project -> (project, apps) -> its text")
TOOLS: TargetMember[Any] = M("tools", True, tuple, "(command, why, where to get it) per tool")
IMAGE_REGISTRY: TargetMember[Any] = M("image_registry", True, dict, "where an image is pushed and what runs it")
PIPELINE: TargetMember[Any] = M("pipeline", True, dict, "the deploy workflow's parts that are this cloud's")
README_WORDS: TargetMember[Any] = M("readme_words", True, dict, "the nouns the Production section is written round")
AGENT_RULES: TargetMember[Any] = M("agent_rules", True, str, "the production paragraph an agent is held to")
ADD_COMMANDS: TargetMember[Any] = M("add_commands", True, dict, "what adding a service or a frontend means here")
#: Never required: absence is the answer "this place has no ambient region", which is true of at least one
#: of them — every resource carries its own location and there is nothing for `preflight` to read.
REGION: TargetMember[Any] = M("region", False, tuple, "(variable, how to read it, what to say when it is unset)")
#: What a person needs before `make bootstrap` — an account, a signed-in CLI — as the docs page lists them.
PREREQUISITES: TargetMember[Any] = M("prerequisites", False, tuple, "a line per prerequisite")
#: Never required either: absence is the answer "this cloud has no flag store", and a project on it reads
#: its flags the one way every project can — out of the environment the platform resolved them into.
FLAG_TRANSPORTS: TargetMember[Any] = M("flag_transports", False, dict, "the default transport, and the opt-in one")

PROTOCOL: tuple[TargetMember[Any], ...] = (
    SHAPES, SCRIPTS, DOCS_PAGES, TOOLS, IMAGE_REGISTRY, PIPELINE, README_WORDS, AGENT_RULES, ADD_COMMANDS,
    REGION, PREREQUISITES, FLAG_TRANSPORTS,
)

#: What each dict-shaped member has to have in it, because the keel reads each of these by name. A member
#: whose keys were a package's to choose would be one the keel could only read by guessing.
KEYS: dict[str, tuple[str, ...]] = {
    # The deploy workflow's own parts. The shape around them — `verify` on `main`, one apply at a time,
    # apply then smoke, production behind `AUTO_PROMOTE`, a rollback that re-applies the release before —
    # is the promise and not the cloud, so a target supplies the parts and never the job.
    PIPELINE.name: ("cli", "credentials", "build_cli", "registry_login", "environment"),
    # The cloud a person signs in to, what the registry is called, one of its addresses as an example, and
    # what `infra/` runs a service as. Four words `scripts/deploy.py`'s comment block is written round.
    IMAGE_REGISTRY.name: ("cloud", "registry", "example", "runtime"),
    # `runtime` is what `infra/` runs a service as in one phrase; `site` is what a browser app is served
    # from; `credentials` is what `make bootstrap` looks for. Everything around them — the pipeline,
    # `AUTO_PROMOTE`, the rollback workflow — is the same promise whatever the cloud is.
    README_WORDS.name: ("runtime", "site", "credentials"),
    # What `add-service` and `add-frontend` say afterwards about the destination.
    ADD_COMMANDS.name: ("service", "web"),
    # The transport every project on this target has, and — where the target offers a second one — its name.
    FLAG_TRANSPORTS.name: ("default",),
}


def required() -> tuple[TargetMember[Any], ...]:
    """The members a managed target owes, in the protocol's order."""
    return tuple(member for member in PROTOCOL if member.required)


@dataclass(frozen=True)
class Target:
    """What one target module exports as `TARGET`: the name it is listed under, and its answers."""

    name: str
    answers: Mapping[TargetMember[Any], object] = field(default_factory=dict)


def kind_name(kind: Any) -> str:
    """What a member's kind is called in a refusal: `dict`, or `tuple or NoneType` for a tuple of kinds."""
    return " or ".join(one.__name__ for one in kind) if isinstance(kind, tuple) else str(kind.__name__)


def faults(target: Target, managed: bool) -> list[str]:
    """Everything wrong with this `TARGET`, each one line, all of them at once rather than the first.

    All at once for the reason `registry.load` gives: a publisher fixing one fault per run is a publisher
    running the suite six times to find out what their package owes.
    """
    found: list[str] = []
    said = f"target {target.name}"
    if (fault := name_fault("target", target.name)) is not None:
        found.append(fault)
    answers = target.answers
    found += [f"{said} answers a key that is not a protocol member: {key!r}"
              for key in answers if not isinstance(key, TargetMember)]
    for member in PROTOCOL:
        if member not in answers:
            if member.required and managed:
                found.append(f"{said} is missing {member.name}")
            continue
        value = answers[member]
        if not isinstance(value, member.kind):
            found.append(f"{said} answers {member.name} with {type(value).__name__}, where the protocol "
                         f"wants {kind_name(member.kind)}")
            continue
        found += content_faults(said, member, value)
    return found


def content_faults(said: str, member: TargetMember[Any], value: object) -> list[str]:
    """What is wrong inside an answer of the right kind: the two shapes, a tool that says nothing, and a
    dict-shaped member short a key the keel reads by name."""
    if member is SHAPES:
        return shape_faults(said, value)
    if member is TOOLS:
        return tool_faults(said, value)
    return key_faults(said, member, value)


def key_faults(said: str, member: TargetMember[Any], value: object) -> list[str]:
    """A dict member short what the keel reads out of it, all the missing keys at once.

    By name rather than by shape, because every one of these is read somewhere specific — the workflow asks
    for `credentials`, the README asks for `runtime` — and a member whose keys were a package's to choose
    would be one the keel could only read by guessing.
    """
    wanted = KEYS.get(member.name)
    if wanted is None or not isinstance(value, dict):
        return []
    if missing := [key for key in wanted if key not in value]:
        return [f"{said} answers {member.name} without {', '.join(missing)}, which the keel reads by name: "
                f"it holds {', '.join(wanted)}"]
    return []


def shape_faults(said: str, value: object) -> list[str]:
    """A managed target's stacks: both of them, each made of files the package actually ships."""
    shapes = value if isinstance(value, dict) else {}
    if extra := sorted(set(shapes) - set(BOTH_SHAPES)):
        return [f"{said} answers shapes with {', '.join(extra)}, and a target has two stacks: "
                f"{' and '.join(BOTH_SHAPES)}. `make bootstrap` applies the first and `make deploy` the second"]
    if missing := [shape for shape in BOTH_SHAPES if shape not in shapes]:
        return [f"{said} answers shapes without {', '.join(missing)}, and a managed target has both: the "
                f"account's stack, applied once, and the service's, applied per environment"]
    return [f"{said}'s {shape} shape is made of no files, so applying it would create nothing"
            for shape in BOTH_SHAPES if not shapes[shape]]


def tool_faults(said: str, value: object) -> list[str]:
    """Every tool says what it is and where to get it, because a refusal that names neither costs a search."""
    rows = value if isinstance(value, tuple) else ()
    return [f"{said}'s tools row {row!r} is not a command, why it is needed and where to get it: a person "
            f"told a tool is missing and not told where it comes from is a person left searching"
            for row in rows
            if not (isinstance(row, tuple) and len(row) == 3 and all(isinstance(part, str) and part for part in row))]
