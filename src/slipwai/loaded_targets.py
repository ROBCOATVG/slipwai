"""The installed targets, imported, and one way to ask any of them anything.

`loaded.py` is this for languages, and the split is the same: the catalog is built from manifests, which
import nothing, and the Python is imported later — here, the first time something asks a target a question
that only its code can answer. A menu that listed the installed clouds by importing each of them would make
`slipwai list` pay for every package on the machine.

**Every per-target table the keel used to hold is now one call to `answer`.** `TOOLS[target]`,
`REGION[target]`, `PAGES[target]`, `CLOUD_STEPS[target]`, `WORDS[target]` — each was a dict the keel had to
grow a row in for every new cloud, and each is now a member the cloud answers for itself.

**The refusals are the point.** A keel with no cloud installed is the ordinary case, so `--target aws` on a
machine without the package has to end on the command that installs it. A `KeyError` out of the middle of a
page generator was what the old dicts gave, and only because every cloud they could be asked about was in
the same repository as the dict.
"""
from __future__ import annotations

import functools
from typing import Any

from .assets import this_command
from .catalog import TARGETS
from .errors import GenerationError
from .language_directory import Refused
from .target_directory import import_package
from .target_protocol import Target, TargetMember

#: What `answer` returns for a member a target does not answer and is not obliged to. A sentinel rather than
#: `None`, because `None` is a thing a target could in principle answer with.
UNASKED: Any = object()

#: The line each refused target left behind, in install order. Kept beside the loaded ones because a target
#: that would not import has to be *sayable* — `slipwai target list` prints these — and because one that
#: would not import must not stop another from answering.
_REFUSED: list[str] = []


@functools.cache
def loaded() -> dict[str, Target]:
    """Every installed target whose Python imports, by name. Built once, the first time anything asks."""
    found: dict[str, Target] = {}
    _REFUSED.clear()
    for package in TARGETS:
        try:
            found[package.name] = import_package(package)
        except Refused as error:  # one cloud that will not import is not the others' problem
            _REFUSED.append(str(error))
    return found


def refusals() -> list[str]:
    """A line for each installed target whose Python this keel could not read."""
    loaded()
    return list(_REFUSED)


def missing(target: str) -> str:
    """What to say when a project asks for a target that is not here: which, why, and the way past it.

    Two ways past, because there are two reasons to be here. The package is not installed, which an install
    fixes; or it is installed and refused, in which case its own line says why and this one points at it.
    """
    refused = [line for line in refusals() if line.startswith(f"target {target} ")]
    if refused:
        return (f"the {target} target is installed and this keel cannot read it: {refused[0]}. "
                f"`{this_command()} target list` says the same, and reinstalling it is "
                f"`{this_command()} target install {target}`")
    offered = ", ".join(sorted(loaded())) or "none"
    return (f"the {target} target is not installed, so nothing here knows what it is or how to deploy to "
            f"it. `{this_command()} target install {target}` adds it; installed: {offered}")


def target_of(target: str) -> Target:
    """One installed target's `TARGET`, or a refusal naming the install that would fix it."""
    found = loaded().get(target)
    if found is None:
        raise GenerationError(missing(target))
    return found


def answer(target: str, member: TargetMember[Any], default: Any = UNASKED) -> Any:
    """What this target answers for that member.

    A member the protocol does not require comes back as `None`, or as `default` where the caller has a
    better word for absence than that — `region`, `prerequisites` and `flag_transports` are each a thing a
    cloud may honestly not have, so their absence is read as an answer rather than refused. The caller does
    not have to remember which those are: the protocol already says, and a rule a caller has to remember is
    a rule a caller gets wrong.

    A member the protocol *does* require and the target does not answer is a refusal naming it. The loader
    refuses a managed target missing one, so reaching this is the keel asking an unmanaged target something
    only a managed one answers — the keel's own fault, and said as one.
    """
    found = target_of(target)
    if member in found.answers:
        return found.answers[member]
    if default is not UNASKED:
        return default
    if not member.required:
        return None
    raise GenerationError(
        f"the {target} target does not answer {member.name} ({member.shape}), and this project needs it. "
        f"A managed target is refused at install for missing one, so either {target} is not a managed "
        f"target or this is being asked of it where it should not be"
    )
