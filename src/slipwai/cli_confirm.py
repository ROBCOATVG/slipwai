"""The flags that turn a candidate into an application, read off the command line.

Brownfield adoption (#74), under ADR 0003. `confirm.py` does the work; this is only the reading of it, split out because
the parser and the flags are the edge and the record is not — and because these are deliberately the same words the
interview used to ask one application at a time, so that confirming a candidate and wrapping one are spelled the same
way.
"""
from __future__ import annotations

import argparse

from .errors import GenerationError
from .rungs import EVENTS, STATE


def paired(given: list[str], flag: str, shape: str) -> dict[str, str]:
    """`NAME=VALUE` flags as a mapping, refusing one that does not say which application it is about."""
    pairs = {}
    for entry in given:
        name, separator, value = entry.partition("=")
        if not separator or not name:
            raise GenerationError(f"--{flag} takes {shape}, not {entry!r}")
        pairs[name] = value
    return pairs


def rungs(given: list[str], confirming: list[str]) -> dict[str, str]:
    """`--write-model` as a mapping from application to rung, in either of the two spellings it takes.

    The plan writes it bare — `slipwai adopt --confirm shop --write-model events` — and the other describing
    flags are all `NAME=VALUE`, because a run can settle several candidates at once. Both are read: bare where
    exactly one candidate is being confirmed, which is the only case where it can only mean one thing, and
    `NAME=VALUE` otherwise. The bare form against two candidates is refused rather than applied to both: a
    rung is the one answer about a service that cannot be walked back, and guessing which service it was
    about is not a guess worth making.
    """
    answers: dict[str, str] = {}
    for entry in given:
        name, separator, value = entry.partition("=")
        if not separator:
            if len(confirming) != 1:
                raise GenerationError(
                    f"--write-model {entry} does not say which application is on that rung, and this run "
                    f"confirms {len(confirming)}: write it as --write-model NAME={entry}"
                )
            name, value = confirming[0], entry
        if value not in (EVENTS, STATE):
            raise GenerationError(
                f"--write-model takes `{EVENTS}` — the service's own log is its truth — or `{STATE}`, where it "
                f"keeps current state and raises the events the model names; not {value!r}"
            )
        answers[name] = value
    return answers


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
    write_models = rungs(args.write_model, args.confirm)
    commands: dict[str, dict[str, str | None]] = {}
    for entry in args.command:
        named, separator, command = entry.partition("=")
        app_name, colon, target = named.partition(":")
        if not separator or not colon:
            raise GenerationError("--command takes NAME:TARGET=COMMAND")
        # `-` and an empty value both mean "record none": `--command app:test=` is what a shell leaves when
        # a variable is unset, and recording the empty string there wrote a command that runs nothing and
        # reads as one somebody chose.
        commands.setdefault(app_name, {})[target] = None if command in ("-", "") else command
    described = {*languages, *purposes, *kinds, *renames, *commands, *write_models, *args.hexagonal}
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
            **({"write_model": write_models[name]} if name in write_models else {}),
        }
        for name in args.confirm
    }


# What `--confirm` and `--decline` have no use for: every flag that describes the adoption itself rather than
# the candidate being settled. Passed alongside one, each was read, ignored and never mentioned — `adopt
# --confirm shop --integration cursor` looked like it recorded a harness and recorded nothing. A flag that
# silently does nothing is worse than one that is refused, which is the rule the intro already
# applies to the flags that describe an application.
SETTLING_IGNORES = (
    "yes", "refresh", "next_steps", "integration", "run_init", "name", "profile",
    "target", "delivery", "why", "skip", "database", "database_repository", "infrastructure",
    "infrastructure_repository", "forge", "release",
)


def ignored_by_settling(args: argparse.Namespace, parser: argparse.ArgumentParser) -> list[str]:
    """The adoption's own flags a `--confirm` or `--decline` run was given and would have thrown away."""
    # The *first* declared default per dest, not the last: two actions can share one (`--init` / `--no-init`),
    # and a later one's default would otherwise decide what "unset" means for both.
    defaults: dict[str, object] = {}
    for action in parser._actions:
        defaults.setdefault(action.dest, action.default)
    given = []
    for dest in SETTLING_IGNORES:
        if not hasattr(args, dest) or getattr(args, dest) == defaults.get(dest):
            continue
        option = next(
            (action.option_strings[0] for action in parser._actions if action.dest == dest),
            f"--{dest.replace('_', '-')}",
        )
        given.append(option)
    return given
