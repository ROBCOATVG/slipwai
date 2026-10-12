"""The target protocol: every answer a place a project is deployed to gives, and which are required.

A language package exports `LANGUAGE` and answers the backend protocol (`registry.py`). A target package
exports `TARGET` and answers this one. The members are the six things the keel asks a cloud today, each
read from exactly one place in the keel before this existed, so a package answering them replaces a branch
rather than adding one:

- `shapes` — the stacks, as committed HCL, under the two names a managed target always has. `project/infra`
  copies them.
- `scripts` — what a project gets under `scripts/` to bootstrap the account and deploy into it.
- `docs_pages` — the production ADR and the deployment diagram, which were a module per cloud.
- `tools` — the command-line tools `./init` and `make bootstrap` need, each with why and where to get it;
  the list `preflight` checks before a project is written *and* the generated `./init` checks on the
  machine that runs it, so there is one list and not two.
- `image_registry` — where a built image is pushed and how the pipeline signs in to push it.
- `deploy_steps` — the workflow steps that take the deploy role, per environment.

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

from collections.abc import Callable, Mapping
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
DOCS_PAGES: TargetMember[Any] = M("docs_pages", True, dict, "path in the project -> (selection) -> its text")
TOOLS: TargetMember[Any] = M("tools", True, tuple, "(command, why, where to get it) per tool")
IMAGE_REGISTRY: TargetMember[Any] = M("image_registry", True, dict, "where an image is pushed and how to sign in")
DEPLOY_STEPS: TargetMember[Any] = M("deploy_steps", True, Callable, "(environment) -> the workflow steps")
#: Never required: absence is the answer "this cloud has no ambient region", which is Azure's, where every
#: resource carries its own `location` and there is nothing for `preflight` to read.
REGION: TargetMember[Any] = M("region", False, tuple, "(variable, how to read it, what to say when it is unset)")
#: What a person needs before `make bootstrap` — an account, a signed-in CLI — as the docs page lists them.
PREREQUISITES: TargetMember[Any] = M("prerequisites", False, tuple, "a line per prerequisite")

PROTOCOL: tuple[TargetMember[Any], ...] = (
    SHAPES, SCRIPTS, DOCS_PAGES, TOOLS, IMAGE_REGISTRY, DEPLOY_STEPS, REGION, PREREQUISITES,
)


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
    """What is wrong inside an answer of the right kind: the two shapes, and a tool that says nothing."""
    if member is SHAPES:
        return shape_faults(said, value)
    if member is TOOLS:
        return tool_faults(said, value)
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
