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

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import quickstart
from .assets import DEFAULT_OUTPUT
from .browser_app import frontend_menu
from .catalog import CATALOG, axis_applies, default_language, families, resolve_backend
from .cli_language import nothing_loaded
from .cli_offered import not_installed_frameworks, not_installed_languages
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
from .cli_quickstart import fetches, files_with_record, missing
from .errors import GenerationError
from .loaded_targets import answer
from .preflight import check as check_requirements
from .services import FIRST_SERVICE, FIRST_WEB
from .target_protocol import DEPLOYMENT_SHAPES
from .targets import check_project_name, managed, offered_backends

#: The row that declines, which is the first one and the default. There is deliberately no default
#: quickstart: a quickstart elects third-party extensions, and nobody asked this keel to choose those.
DECLINE = "none"
DECLINED = "ask me every question — the interview as it has always been"


def quickstart_menu() -> tuple[list[str], Callable[[str], str]]:
    """The rows the offer shows: declining first, then every saved quickstart this machine can carry out.

    A row is the quickstart's own sentence about *the product it suits*, never the packages it names. The
    person this slice exists for does not know what `uipro` is, and a menu of package names is addressed to
    somebody who already does.
    """
    usable = [name for name in quickstart.saved_names() if name not in unavailable_quickstarts()]
    suits = {name: quickstart.find(name).suits for name in usable}

    def describe(name: str) -> str:
        return DECLINED if name == DECLINE else suits[name]

    return [DECLINE, *usable], describe


def unavailable_quickstarts() -> dict[str, str]:
    """Each saved quickstart that cannot be carried out here, with the line that would fix it.

    Said under the menu rather than left out of it: somebody who wrote that quickstart should see it is
    still theirs and be told the one command that makes it work, not conclude it was lost.
    """
    absent = {}
    for name in quickstart.saved_names():
        try:
            one = quickstart.find(name)
        except GenerationError as fault:  # a file somebody edited by hand, said and not offered
            absent[name] = str(fault)
            continue
        if missing(one):
            absent[name] = "; ".join(f"`{line}`" for line in fetches(one)) + " installs what it names"
    return absent


def offer_quickstart(args: Any, named: dict[str, str | None]) -> dict[str, str]:
    """Ask, once, whether to start from a saved quickstart, and return the answers the chosen one gives.

    `{}` where it was declined — and where none is saved, in which case nothing is asked at all, because an
    interview that gained a question for people who have no quickstarts would have made the common path
    worse to serve the uncommon one.
    """
    choices, describe = quickstart_menu()
    if len(choices) == 1:
        return {}
    chosen = prompt_choice(
        "Start from", choices, DECLINE, describe, unavailable=unavailable_quickstarts(),
        status="not ready",
        question="Start from a quickstart? Each one is a set of answers somebody already settled — which "
                 "languages, how the project is laid out, and which optional tooling it switches on.",
    )
    if chosen == DECLINE:
        return {}
    one = quickstart.find(chosen)
    given = quickstart.answered(one)
    print(f"\nFrom the {one.name} quickstart — {one.suits}")
    for flag, value in given.items():
        if flag in named:
            named[flag] = value
        else:
            setattr(args, flag.replace("-", "_"), value)
        print(f"  --{flag} {value}")
    for each in one.extensions:
        print(f"  --extension {each.name}" + (f"  (may refuse: {', '.join(each.guards)})" if each.guards else ""))
    args.quickstart = one.name
    print("Each of these is a flag you could have given, and `./init` can change any of them later.\n")
    return given


def interview(args: Any, named: dict[str, str | None]) -> None:
    """Ask every question a quickstart has not already answered, in order, writing each answer onto `args`
    and `named` as the flag it stands for."""
    if not families():
        raise GenerationError(nothing_loaded())
    print("Create a new product monorepo. Press Enter to accept a shown default.")
    args.name = prompt_project_name()
    # Before the delivery foundation, because the foundation is the first thing a quickstart answers.
    given = offer_quickstart(args, named)
    if "profile" not in given:
        args.profile = prompt_profile()
    if "target" not in given:
        args.target = prompt_target()
    if managed(CATALOG, args.target) and answer(args.target, DEPLOYMENT_SHAPES, default={}):
        args.shape = prompt_choice(
            "Deployment size", ["skiff", "liner"], "skiff",
            lambda choice: ("one environment for colleagues; an outage is an inconvenience" if choice == "skiff"
                            else "the full product stack; an outage is an incident"),
            question="Who will use this product, and what happens when it is down?",
        )
    # Asked before the target and checked against it: a name the target's cloud will not take is
    # said here, not after another nine questions.
    check_project_name(CATALOG, args.target, args.name)
    noticed = check_requirements(args.target, args.skip_checks)
    if noticed:
        print(noticed, file=sys.stderr)
    args.backend = resolve_backend(args.language, args.framework or None) if "language" in given \
        else ask_language(args)
    args.service_name = prompt_application_name("Service name", FIRST_SERVICE, set())
    args.purpose = prompt_purpose(args.service_name)
    args.context = prompt_context(args.service_name)
    if "frontend" not in given:
        frontends, default, unavailable = frontend_menu()
        args.frontend = prompt_choice("Frontend", frontends, default, unavailable=unavailable, status="unavailable")
    if args.frontend != "none":
        args.frontend_name = prompt_application_name("Browser app name", FIRST_WEB, {args.service_name})
    # One question per axis, asked separately, because they are separate questions: where events are stored
    # has nothing to do with who issues identities. An axis is asked only when this profile and backend can
    # actually be given a choice, so the prompt never offers a combination `resolve_selection` would refuse.
    for axis in CATALOG["axes"]:
        if named[axis] is None and axis_applies(axis, args.profile, args.backend, args.target):
            named[axis] = prompt_axis(axis, args.profile, args.backend, args.target)
    args.output = prompt_output(DEFAULT_OUTPUT)
    args.prd = prompt_prd()


def prompt_prd() -> Path | None:
    """Ask for a product requirements document, the one input the first specification can be drafted from.

    Blank is the usual answer and is not pressed: a project started without one is specified in the agent,
    with a person, which is what every project did before this question existed. Given one, it is read now
    rather than at the end, so a mistyped path is one more try here and not a refusal after the last
    question.
    """
    while True:
        try:
            answer = input("Product requirements document (a path; Enter for none): ").strip()
        except EOFError as error:
            raise GenerationError("the product requirements document is required in non-interactive use") from error
        if not answer:
            return None
        path = Path(answer).expanduser()
        if path.is_file():
            return path
        print(f"  {path} is not a file")


#: Where the document lands in the project: beside the other pages a person reads first, and where
#: `commands/draft.md` looks when it is given no argument.
PRD = "docs/prd.md"


def prd_files(args: Any, apps: list[Any]) -> dict[str, str] | None:
    """The project's files with the PRD among them, or what `files_with_record` answered where none was given.

    Read here rather than left to the tree: a document that cannot be read, or is not text, is a refusal
    naming the flag before anything is staged, not a traceback from inside `write_project`. The docs index
    is rendered again over the result, because it is built from the pages the project actually ships and
    this is one more of them.
    """
    files = files_with_record(args, apps)
    given = getattr(args, "prd", None)
    if given is None:
        return files
    path = Path(given).expanduser()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise GenerationError(f"--prd {path} cannot be read: {error.strerror or error}") from error
    except UnicodeDecodeError as error:
        raise GenerationError(f"--prd {path} is not UTF-8 text; a PRD is a Markdown or plain-text file") from error
    if not text.strip():
        raise GenerationError(f"--prd {path} is empty")
    if files is None:
        from .scaffold import project_files
        files = project_files(args.name, args.profile, args.target, apps, shape=getattr(args, "shape", None))
    from .project.docs_index import docs_index
    files = {**files, PRD: text}
    files["docs/README.md"] = docs_index(files)
    return files


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
