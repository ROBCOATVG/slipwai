"""The flags that turn a candidate into an application, read off the command line.

Brownfield adoption (#74; experimental as `AGENTS.md` defines the word), under ADR 0003. `confirm.py` does
the work; this is only the reading of it, split out because the parser and the flags are the edge and the
record is not — and because these are deliberately the same words the interview used to ask one application
at a time, so that confirming a candidate and wrapping one are spelled the same way.
"""
from __future__ import annotations

import argparse

from .errors import GenerationError


def paired(given: list[str], flag: str, shape: str) -> dict[str, str]:
    """`NAME=VALUE` flags as a mapping, refusing one that does not say which application it is about."""
    pairs = {}
    for entry in given:
        name, separator, value = entry.partition("=")
        if not separator or not name:
            raise GenerationError(f"--{flag} takes {shape}, not {entry!r}")
        pairs[name] = value
    return pairs


def confirmations(args: argparse.Namespace) -> dict[str, dict]:
    """What each `--confirm`ed candidate is to be recorded as: the describing flags, gathered by name.

    The same flags the interview used to ask for one application at a time, read here instead — so that
    confirming a candidate and wrapping one take the same words, and `/ground` has one command to call with
    what it has read off the directory.
    """
    languages = paired(args.language, "language", "NAME=LANGUAGE")
    purposes = paired(args.purpose, "purpose", "NAME=TEXT")
    kinds = paired(args.kind, "kind", "NAME=KIND")
    renames = paired(args.renamed, "as", "NAME=NEW")
    commands: dict[str, dict[str, str | None]] = {}
    for entry in args.command:
        named, separator, command = entry.partition("=")
        app_name, colon, target = named.partition(":")
        if not separator or not colon:
            raise GenerationError("--command takes NAME:TARGET=COMMAND")
        commands.setdefault(app_name, {})[target] = None if command == "-" else command
    described = {*languages, *purposes, *kinds, *renames, *commands, *args.hexagonal}
    stray = sorted(described - set(args.confirm))
    if stray:
        raise GenerationError(
            f"{', '.join(stray)} is described by a flag and not among the candidates being confirmed; "
            "--confirm names which candidate each description belongs to"
        )
    return {
        name: {
            **({"language": languages[name]} if name in languages else {}),
            **({"purpose": purposes[name]} if name in purposes else {}),
            **({"kind": kinds[name]} if name in kinds else {}),
            **({"name": renames[name]} if name in renames else {}),
            **({"commands": commands[name]} if name in commands else {}),
            **({"structure": "hexagonal"} if name in args.hexagonal else {}),
        }
        for name in args.confirm
    }
