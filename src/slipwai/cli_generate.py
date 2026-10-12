"""The interview: what `slipwai generate` asks when it is run with nothing to go on, in the order it asks.

Split out of `cli.py` when the quickstart flag arrived and that module reached its budget — which is what
the budget is for, and the same seam `cli_prompts` was cut along: that module holds *one question*, this
one holds *the order they are asked in*, and `cli.py` keeps the flags and the assembly. The order is the
part with opinions in it — the target before the languages because it decides the menus, the name before
the target because a cloud that will not take it should say so before another nine questions — and it was
buried in the middle of a function that also built a parser and wrote a repository.

Every answer here is also a flag `cli.py` declares, which is what makes the interview and a scripted
`generate` the same command: the interview writes its answers onto the same namespace the flags parse into,
and nothing downstream can tell which of the two put them there.
"""
from __future__ import annotations

from typing import Any

from .assets import DEFAULT_OUTPUT
from .browser_app import frontend_menu
from .catalog import CATALOG, axis_applies, default_language, families
from .cli_language import not_installed_frameworks, not_installed_languages, nothing_loaded
from .cli_prompts import (
    prompt_application_name,
    prompt_axis,
    prompt_choice,
    prompt_context,
    prompt_framework,
    prompt_output,
    prompt_profile,
    prompt_project_name,
    prompt_purpose,
    prompt_target,
)
from .errors import GenerationError
from .preflight import check as check_requirements
from .services import FIRST_SERVICE, FIRST_WEB
from .targets import check_project_name, offered_backends


def interview(args: Any, named: dict[str, str | None]) -> None:
    """Ask every question, in order, writing each answer onto `args` and `named` as the flag it stands for."""
    if not families():
        raise GenerationError(nothing_loaded())
    print("Create a new product monorepo. Press Enter to accept a shown default.")
    args.name = prompt_project_name()
    args.profile = prompt_profile()
    args.target = prompt_target()
    # Asked before the target and checked against it: a name the target's cloud will not take is
    # said here, not after another nine questions.
    check_project_name(CATALOG, args.target, args.name)
    check_requirements(args.target, args.skip_checks)
    args.backend = ask_language(args)
    args.service_name = prompt_application_name("Service name", FIRST_SERVICE, set())
    args.purpose = prompt_purpose(args.service_name)
    args.context = prompt_context(args.service_name)
    frontends, default, unavailable = frontend_menu()
    args.frontend = prompt_choice("Frontend", frontends, default, unavailable=unavailable, status="unavailable")
    if args.frontend != "none":
        args.frontend_name = prompt_application_name("Browser app name", FIRST_WEB, {args.service_name})
    # One question per axis, asked separately, because they are separate questions: where events are stored
    # has nothing to do with who issues identities. An axis is asked only when this profile and backend can
    # actually be given a choice, so the prompt never offers a combination `resolve_selection` would refuse.
    for axis in CATALOG["axes"]:
        if axis_applies(axis, args.profile, args.backend, args.target):
            named[axis] = prompt_axis(axis, args.profile, args.backend, args.target)
    args.output = prompt_output(DEFAULT_OUTPUT)


def ask_language(args: Any) -> str:
    """Which language, then — where the family has more than one — which framework, as one backend key."""
    # Only the languages with a backend offered under the target: the target decides the menus.
    offered = offered_backends(CATALOG, args.target)
    languages = [family for family, members in families().items() if set(members) & set(offered)]
    preferred = default_language()
    # What the index offers that is not installed is named under the menu, with the line that installs it.
    uninstalled, unreachable = not_installed_languages()
    if unreachable is not None:
        print(unreachable)
    language = prompt_choice(
        "Language", languages, preferred if preferred in languages else languages[0], unavailable=uninstalled
    )
    return prompt_framework(language, args.target, not_installed_frameworks(language))
