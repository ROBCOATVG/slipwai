"""Resolving `--language`, `--framework` and `--backend` to the one backend key everything is keyed by, and
the two menus that say what a person could have asked for instead.

It lives here rather than in `cli_add`, which owns it upstream, because `cli_add` needs `add_service`
and `converge` and those are slices 4.3 and 4.2. Its refusals are the chandlery's now: a language that
is not installed is refused with the command that installs it, not with a list of what happens to be
here, which is what the whole of slice 4.5 was for.
"""
from __future__ import annotations

import argparse

from .catalog import CATALOG, default_language, families, framework_of, resolve_backend
from .cli_language import (
    backends_of,
    missing_backend,
    missing_framework,
    missing_language,
    no_framework,
    reach,
    snapshots,
)
from .errors import GenerationError
from .language_directory import directory
from .language_install import builtin, installed, this_command
from .registry import registry


def resolve_requested_backend(args: argparse.Namespace) -> str:
    """One backend key, from either the two-step form or `--backend`.

    Both spellings are offered and mixing them is refused rather than silently resolved: `--backend
    java-spring --framework quarkus` has no reading that is not a mistake, and picking one would be
    guessing which half the caller meant.
    """
    if args.backend is not None:
        if args.language is not None or args.framework is not None:
            raise GenerationError(
                "--backend already names the language and the framework; pass either --backend, or "
                "--language with --framework"
            )
        if args.backend not in CATALOG["backends"]:
            raise GenerationError(missing_backend(args.backend))
        return args.backend
    # A family installed with no backend of its own — its frameworks absent or refused — is installed:
    # what it lacks is a framework, and `missing_framework` names that one's install line.
    if args.language is not None and args.language not in families() and args.language not in registry().families:
        raise GenerationError(missing_language(args.language))
    language = args.language or default_language()
    if language not in families():
        said = missing_framework(language, args.framework) if args.framework is not None else None
        raise GenerationError(said or no_framework(language))
    offered = [framework_of(backend) for backend in families().get(language, [])]
    if args.framework is not None and args.framework not in offered:
        said = missing_framework(language, args.framework)
        if said is not None:
            raise GenerationError(said)
        raise GenerationError(
            f"--framework {args.framework} is not one {language} offers; it offers "
            f"{', '.join(name for name in offered if name) or 'none'}"
        )
    return resolve_backend(language, args.framework)


def not_installed_languages() -> tuple[dict[str, str], str | None]:
    """For the interview's language menu: each language the index offers that is not installed, with the line that
    installs it, and the line saying the index could not be read (None where it could)."""
    found, offer, unreachable = reach(snapshots())
    if found is None:
        return {}, f"{unreachable[0].strip()}; {this_command()} list shows what is installed"
    have = {*families(), *installed(directory())}
    return {name: f"{this_command()} language install {name}" for name, release in offer.items()
            if release.fragment.get("family", name) == name and name not in have}, None


def not_installed_frameworks(family: str) -> dict[str, str]:
    """For the interview's framework question: each framework of `family` the index offers that is not installed, by
    its `framework`, with the line that installs it. Nothing where the index cannot be read: the language question
    already said so."""
    found, offer, _ = reach(snapshots())
    have = {*installed(directory()), *builtin()}
    rows: dict[str, str] = {}
    for name, release in offer.items():
        if release.fragment.get("family") != family or name == family or name in have:
            continue
        for row in backends_of(release).values():
            if isinstance(row, dict) and isinstance(row.get("framework"), str):
                rows[row["framework"]] = f"{this_command()} language install {name}"
    return rows if found is not None else {}
