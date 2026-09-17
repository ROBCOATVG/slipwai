"""What this project's name becomes inside each ecosystem's namespace.

One function per ecosystem that has a namespace of its own and rules about what may be in it. Split out of
`backends.py`, which had outgrown its budget: these answer a question about a *name*, not about a backend's
toolchain, and everything that needs them — the Makefile's run target, a service's package directory, the
imports inside it, the event model's documented paths — needs the same answer as the directory on disk.

Node needs no entry here: an npm package name is the project's name and a hyphen is legal in it, so
`tooling.package_name` spells that where the rest of a service's build is spelled. Go needs none either:
a module path is a URL-shaped string that takes the name as it is.
"""
from __future__ import annotations

import re


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
