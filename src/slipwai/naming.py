"""What a name has to satisfy here, and what this project's name becomes inside each ecosystem's namespace.

Two halves of one question. The first is what any name here may be at all: a service's and a context's,
each of which is a directory, a package, a module segment and a Compose service at once, so each takes the
intersection of what all four accept. Those rules came out of `services.py` when it reached its budget, and
they belong here rather than there because they are about a *name* and nothing about a list of
applications — `check_name` is given the names already taken, not the applications that hold them.

The second is one function per ecosystem that has a namespace of its own and rules about what may be in it.
Split out of `backends.py`, which had outgrown its budget: these answer a question about a *name*, not about
a backend's toolchain, and everything that needs them — the Makefile's run target, a service's package
directory, the imports inside it, the event model's documented paths — needs the same answer as the
directory on disk.

Node needs no entry here: an npm package name is the project's name and a hyphen is legal in it, so
`tooling.package_name` spells that where the rest of a service's build is spelled. Go needs none either:
a module path is a URL-shaped string that takes the name as it is.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from .errors import GenerationError

# A service name is a directory under `apps/`, an npm package suffix, a Go module segment and a Compose
# service name at once, so it takes the intersection of what all four accept.
SERVICE_NAME = re.compile(r"[a-z][a-z0-9-]*[a-z0-9]|[a-z]")
# A bounded context's name is also a directory (`src/<context>/` inside a service) and a heading, so it
# takes the same shape.
CONTEXT_NAME = SERVICE_NAME


def check_name(taken: Iterable[str], name: str) -> None:
    """A name that can be a directory, an npm package, a Go module segment and a Compose
    service at once, and that nothing on this project already has."""
    if not SERVICE_NAME.fullmatch(name):
        raise GenerationError(
            f"'{name}' cannot name an application: use lowercase letters, digits and hyphens, starting with a "
            "letter — it has to be a directory, an npm package, a Go module segment and a Compose service"
        )
    if name in set(taken):
        raise GenerationError(f"this project already has an application named '{name}'")


def check_context(name: str) -> None:
    if not CONTEXT_NAME.fullmatch(name):
        raise GenerationError(
            f"'{name}' cannot name a bounded context: use lowercase letters, digits and hyphens, starting "
            "with a letter — it is a directory inside a service and a heading in the model"
        )


def checked_contexts(names: Sequence[str] | None) -> tuple[str, ...]:
    """The contexts a service was given, each a legal name, once each and in the order given."""
    for name in names or ():
        check_context(name)
    return tuple(dict.fromkeys(names or ()))


def java_package_segment(project_name: str) -> str:
    """The final package segment a Java project's service code lives in.

    Separators are dropped rather than replaced, because that is what the ecosystem does with a hyphenated
    artifact name: `delivery-starter` is `deliverystarter`, not `delivery_starter`. A package segment may
    not begin with a digit, so one that would is prefixed the same way the Python package is.
    """
    segment = re.sub(r"[^a-z0-9]", "", project_name.lower())
    return f"p{segment}" if not segment or segment[0].isdigit() else segment


def python_package_name(project_name: str) -> str:
    """The importable package a Python project's service code lives in.

    A function rather than an expression inside `language_files`, because the Makefile needs the same
    answer: `python3 -m <package>.main` is how the service is run, and a Makefile that guessed the name
    differently would be a run target that cannot find the application it was generated for.
    """
    package = re.sub(r"[^a-z0-9_]", "_", project_name)
    return f"project_{package}" if package[0].isdigit() else package
