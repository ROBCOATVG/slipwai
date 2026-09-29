"""`slipwai adopt`: the verb's flags, and what it does with the answers however they arrive.

Experimental (`AGENTS.md` says what the word means here). Run at the root of a repository the factory
did not make. Bare, in a terminal, it surveys the tree, shows every directory that builds as a candidate, asks
the one thing a terminal can answer — where CI runs — and leaves which candidate is an application to `/ground`,
which asks with the code in front of it (ADR 0003; `cli_interview.shape`). With `--yes` nothing is asked and
every proposal is wrapped as `detected`, unlooked-at, and flags override single answers, always `overridden`.
Outside a terminal without `--yes` it refuses rather than guessing.

Two readings of an adoption that has already happened share the verb, because they are the same record read
again rather than a second thing to learn: `--refresh` reconciles a fresh survey with what was recorded, and
`--next` says where the repository stands in the sequence the adoption report named.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import confirm as confirming
from . import next_steps, resurvey
from .adopt import Answers, adopt, candidates_of, check_repository, proposed, report
from .catalog import CATALOG
from .cli_confirm import confirmations
from .cli_init import (
    add_setup_arguments,
    agent_line,
    install_tools,
    installing,
    projection_line,
    prompt_agent,
    reproject,
    run_init,
    tools_for,
)
from .cli_interview import NOTHING_TO_ASK, shape, with_override
from .cli_prompts import validate_project_name
from .ecosystems import EXTRA, TARGETS
from .errors import GenerationError
from .harness import Agent, chosen, detect, keys
from .layout import layout_of
from .manifest import apps_from_manifest, read_manifest
from .origin import FORGES, HOMES, RELEASE_PATHS, WRAPPED_KINDS, adoption_of
from .survey import survey

NOTHING_FOUND = (
    "nothing here starts a build the survey can read — a package.json, pyproject.toml or requirements.txt, go.mod, "
    "pom.xml, build.gradle, build.xml, a .sln or .csproj, composer.json or Gemfile, at the root or up to three "
    "directories down — so there is no application to wrap, and adoption installs the method around applications. "
    "A build this repository does have and the survey cannot read is a gap in the factory: raise it, naming the file."
)
NOTHING_LEFT = "every application the survey found was skipped or left unwrapped; nothing is left to install around"
# What `--confirm` and `--decline` have no use for: every flag that describes the adoption itself rather than
# the candidate being settled. Passed alongside one, each was read, ignored and never mentioned — `adopt
# --confirm shop --integration cursor` looked like it recorded a harness and recorded nothing. A flag that
# silently does nothing is worse than one that is refused, which is the rule the intro already
# applies to the flags that describe an application.
SETTLING_IGNORES = (
    "yes", "refresh", "next_steps", "experimental_intro", "integration", "run_init", "install", "name", "profile",
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


def next_report(root: Path) -> str:
    """`--next` in a repository the method was installed around: the sequence, as the tree has it now."""
    document = read_manifest(root, "slipwai adopt --next")
    adoption = adoption_of(document)
    if adoption is None:
        raise GenerationError(
            "this project was generated, not adopted, so there is no adoption sequence to stand in: a generated "
            "project's next steps are its README, and every row of its map is at the top by construction"
        )
    return next_steps.report(root, layout_of(document), adoption, apps_from_manifest(document, True))


def adopt_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="slipwai adopt",
        description="EXPERIMENTAL: install the delivery method around the repository in the current directory",
        epilog="Bare, in a terminal, it asks with the survey's findings as defaults; `--yes` takes them all as "
        "found. Experimental: its shape may change in a MINOR; what it gets wrong belongs on the public issue tracker.",
    )
    parser.add_argument("--yes", action="store_true", help="accept everything the survey found without asking")
    parser.add_argument(
        "--refresh", action="store_true",
        help="in an adopted repository: survey again, refresh what was only detected, report what disagrees with "
        "what a person decided, and regenerate what the record drives (what /survey runs)",
    )
    parser.add_argument(
        "--next", action="store_true", dest="next_steps",
        help="in an adopted repository: say where it stands in the sequence adopt started — what is done, what is "
        "next, and why — read off the tree rather than remembered from the report",
    )
    # The switch the candidate intro arrived behind, before it was the only one: accepted and ignored for one
    # release, so a script or a habit that still passes it keeps working. Hidden, because it now chooses nothing.
    parser.add_argument("--experimental-intro", action="store_true", dest="experimental_intro",
                        help=argparse.SUPPRESS)
    parser.add_argument(
        "--confirm", action="append", default=[], metavar="NAME",
        help="in an adopted repository: a candidate the survey found that is an application, recorded as one "
        "with `confirmed` provenance; the describing flags below apply to it, and everything the record "
        "drives is regenerated. Repeatable (what /ground calls once it has read the directory)",
    )
    parser.add_argument(
        "--decline", action="append", default=[], metavar="NAME",
        help="in an adopted repository: a candidate that is not an application. It is dropped, and nothing is "
        "recorded in its place. Repeatable",
    )
    parser.add_argument(
        "--as", action="append", default=[], dest="renamed", metavar="NAME=NEW",
        help="confirm a candidate under a name of your own, rather than the directory's",
    )
    add_setup_arguments(parser, "./<delivery>/init")
    parser.add_argument("--name", default=None, help="the project's name (default: the directory's)")
    parser.add_argument("--profile", choices=CATALOG["profiles"], default="standard")
    parser.add_argument(
        "--target", choices=("existing", "none"), default=None,
        help="where this deploys: existing infrastructure it does not own, or nowhere (default: existing unless the "
        "infrastructure is none)",
    )
    parser.add_argument(
        "--delivery", default="delivery", metavar="DIR", help="where the method's files go (default: %(default)s)"
    )
    parser.add_argument("--why", default=None, metavar="TEXT", help="the business trigger behind this work")
    parser.add_argument("--skip", action="append", default=[], metavar="NAME", help="a found application not to wrap")
    parser.add_argument(
        "--language", action="append", default=[], metavar="NAME=LANGUAGE", help="override a found language"
    )
    parser.add_argument("--purpose", action="append", default=[], metavar="NAME=TEXT", help="what an application owns")
    parser.add_argument(
        "--kind", action="append", default=[], metavar="NAME=KIND",
        help=f"what a found application is: {', '.join(WRAPPED_KINDS)} (application: not established)",
    )
    parser.add_argument(
        "--command", action="append", default=[], metavar="NAME:TARGET=COMMAND",
        help=f"override one recorded command; `-` records none. Targets: {', '.join(TARGETS)}; test-full "
        "for a suite too slow for verify; smoke for the command that starts the application and proves it answers",
    )
    parser.add_argument(
        "--hexagonal", action="append", default=[], metavar="NAME",
        help="an application that keeps the hexagonal layers, so the import gate holds it to them",
    )
    parser.add_argument("--database", choices=HOMES, default=None, help="where the schema is versioned")
    parser.add_argument("--database-repository", default=None, metavar="URL")
    parser.add_argument("--infrastructure", choices=HOMES, default=None, help="where the infrastructure is described")
    parser.add_argument("--infrastructure-repository", default=None, metavar="URL")
    parser.add_argument(
        "--forge", choices=FORGES, default=None,
        help="where CI runs, which decides the gate's CI configuration (default: what the tree or the remote says)",
    )
    parser.add_argument(
        "--release", choices=RELEASE_PATHS, default=None,
        help="how a change reaches production today (default: what the tree says, or unknown, recorded as such)",
    )
    args = parser.parse_args(argv)
    root = Path.cwd()
    if args.next_steps:
        try:
            print(next_report(root))
        except GenerationError as error:
            parser.error(str(error))
        return
    if args.confirm or args.decline:
        stray = ignored_by_settling(args, parser)
        if stray:
            parser.error(
                f"{', '.join(stray)} describe(s) the adoption itself, and this run settles a candidate that "
                "was already recorded — it would be read and thrown away. `slipwai adopt` takes them when "
                "the method is installed; `--integration` afterwards belongs to `./init`."
            )
        try:
            settled = confirming.confirm(root, confirmations(args), args.decline)
        except GenerationError as error:
            parser.error(str(error))
        print(confirming.report(settled))
        # Confirming changes which languages the record names, which rewrites the skills the harness copies.
        where = layout_of(read_manifest(root)).delivery
        print(projection_line(reproject(root, where), where), end="")
        return
    if args.refresh:
        try:
            refreshed = resurvey.refresh(root)
        except GenerationError as error:
            parser.error(str(error))
        print(resurvey.report(refreshed))
        where = layout_of(read_manifest(root)).delivery
        print(projection_line(reproject(root, where), where), end="")
        return
    try:
        name = args.name or root.name.lower()
        validate_project_name(name)
        # Before the survey and before a single question: this refuses a directory that is not a Git
        # repository, one already holding a `project.json`, and one with uncommitted changes. `adopt` checks
        # again when it writes, because it is a library function and its contract is its own — but finding
        # out afterwards meant surveying twelve thousand files and answering the interview first, and then
        # being told none of it could be kept. A refusal belongs before the work it refuses, not after.
        check_repository(root)
        found = survey(root)
        apps = proposed(found, name)
        if not apps:
            raise GenerationError(NOTHING_FOUND)
        proposal: dict[str, str | None] = {
            "schema": found.schema_home, "home": found.infrastructure_home, "forge": found.forge[0],
            "release": found.release_path,
        }
        database: dict = {}
        infrastructure: dict = {}
        ci: dict = {}
        release: dict = {}
        why = args.why
        # Nothing is wrapped by this command: the directories the survey found are
        # recorded as candidates, and what each of them is stays a question until somebody with the code in
        # front of them answers it (ADR 0003). `--yes` is the exception it has always been — it confirms every
        # one of them unlooked-at, which is what an unattended run is for, and the report says so out loud.
        candidates: list[dict] = []
        if not args.yes:
            if not sys.stdin.isatty():
                raise GenerationError(NOTHING_TO_ASK)
            candidates = candidates_of(found, name)
            ci = shape(candidates, proposal)
            apps = []
        apps = [app for app in apps if app.name not in args.skip]
        candidates = [row for row in candidates if row["name"] not in args.skip]
        if not apps and not candidates:
            raise GenerationError(NOTHING_LEFT)
        known = {app.name for app in apps} or {row["name"] for row in candidates}
        # A flag that describes an application has nothing to describe while every directory is a candidate:
        # it would be read, validated against the candidate names, and then quietly do nothing, because the
        # loops below walk `apps`. Refused by name instead, pointing at the command that does take them.
        if candidates:
            describing = [
                flag for flag, given in
                (("--language", args.language), ("--purpose", args.purpose), ("--kind", args.kind),
                 ("--command", args.command), ("--hexagonal", args.hexagonal))
                if given
            ]
            if describing:
                raise GenerationError(
                    f"{', '.join(describing)} describe(s) an application, and this "
                    "command records what the survey found as candidates rather than wrapping any of them. "
                    "`slipwai adopt --confirm <name>` takes the same flags and makes a candidate an "
                    "application; `--yes` here confirms every candidate as found."
                )
        given_names = (
            *(("language", g) for g in args.language), *(("purpose", g) for g in args.purpose),
            *(("command", g) for g in args.command), *(("hexagonal", g) for g in args.hexagonal),
            *(("skip", g) for g in args.skip), *(("kind", g) for g in args.kind),
        )
        for flag, given in given_names:
            named = given.partition("=")[0].partition(":")[0]
            if named not in known and not (flag == "skip" and named in {a.name for a in proposed(found, name)}):
                raise GenerationError(
                    f"--{flag} names `{named}`, and no application by that name was found; "
                    f"found: {', '.join(sorted(known)) or 'none'}"
                )
        for flag, field in (("language", "language"), ("purpose", "purpose"), ("kind", "kind")):
            for given in getattr(args, flag):
                target, separator, value = given.partition("=")
                if not separator:
                    raise GenerationError(f"--{flag} takes NAME={field.upper()}, not {given!r}")
                if field == "kind" and value not in WRAPPED_KINDS:
                    raise GenerationError(f"--kind takes one of {', '.join(WRAPPED_KINDS)}, not {value!r}")
                apps = [with_override(root, app, **{field: value}) if app.name == target else app for app in apps]
        for given in args.command:
            named, separator, command = given.partition("=")
            app_name, colon, target = named.partition(":")
            if not separator or not colon or target not in (*TARGETS, *EXTRA):
                raise GenerationError(
                    f"--command takes NAME:TARGET=COMMAND with a target among {', '.join((*TARGETS, *EXTRA))}"
                )
            apps = [
                with_override(root, app, commands={**(app.commands or {}), target: None if command == "-" else command})
                if app.name == app_name else app
                for app in apps
            ]
        for declared in args.hexagonal:
            apps = [with_override(root, app, structure="hexagonal") if app.name == declared else app for app in apps]
        if args.database:
            database = {"schema": args.database, "provenance": "overridden"}
        if args.database_repository:
            database = database or {"schema": "elsewhere", "provenance": "overridden"}
            database = {**database, "repository": args.database_repository}
        if args.infrastructure:
            infrastructure = {"home": args.infrastructure, "provenance": "overridden"}
        if args.infrastructure_repository:
            infrastructure = {
                **(infrastructure or {"home": "elsewhere", "provenance": "overridden"}),
                "repository": args.infrastructure_repository,
            }
        if args.forge:
            ci = {"forge": args.forge, "provenance": "overridden"}
        if args.release:
            release = {"path": args.release, "provenance": "overridden" if args.release != "unknown" else "unrecorded"}
        home = (infrastructure or {}).get("home", proposal["home"])
        target = args.target or ("none" if home == "none" else "existing")
        if args.integration is not None and args.integration not in keys():
            raise GenerationError(
                f"--integration names `{args.integration}`, and the agent registry has no such harness; "
                f"`python3 {args.delivery}/scripts/agents/project.py --list` lists them once the method is here"
            )
        agent = chosen(args.integration) if args.integration else detect(root)
        # Somebody at the terminal, about to have `./init` set the agent up, is asked which one where nothing
        # settled it — with no answer preselected, and before the commit, so the adoption records it.
        attended = not args.yes and sys.stdin.isatty()
        running_init = args.run_init if args.run_init is not None else attended
        install = installing(args.install, attended)
        if agent.harness is None and running_init and attended:
            key = prompt_agent(agent.candidates)
            agent = Agent(key, "answered at `slipwai adopt`'s question", "confirmed")
        answers = Answers(
            name, args.profile, target, args.delivery, why, apps, database, infrastructure, ci, release,
            agent=agent.record(), candidates=candidates,
        )
        done = adopt(root, answers, found)
    except GenerationError as error:
        parser.error(str(error))
    # `./init` reaches Spec Kit's source, so it is the one step that needs the network, and it leaves files for
    # the person to commit. By default only where somebody is at the terminal, decided above, before the report
    # is printed, because the report says something different when it is about to happen.
    print(report(done, running_init))
    print(agent_line(agent))
    if install:
        languages = [str(row.get("language")) for row in candidates] + [str(app.language) for app in apps]
        install_tools(tools_for(languages), install)
    if running_init:
        run_init(root, args.delivery, agent, install)
