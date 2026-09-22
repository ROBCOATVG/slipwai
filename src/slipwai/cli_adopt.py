"""`slipwai adopt`: the verb's flags, and what it does with the answers however they arrive.

Experimental (`AGENTS.md` says what the word means here). Run at the root of a repository the factory
did not make. Bare, in a terminal, it surveys the tree and asks about each thing it found with the found
value as the default — `cli_interview` is those questions — where Enter confirms it (`confirmed`) and another
answer overrides it (`overridden`). With `--yes` nothing is asked and every proposal stands as `detected`;
flags override single answers either way, and a flag is always `overridden`. Outside a terminal without
`--yes` it refuses rather than guessing.

Two readings of an adoption that has already happened share the verb, because they are the same record read
again rather than a second thing to learn: `--refresh` reconciles a fresh survey with what was recorded, and
`--next` says where the repository stands in the sequence the adoption report named.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import next_steps, resurvey
from .adopt import Answers, adopt, proposed, report
from .catalog import CATALOG
from .cli_interview import NOTHING_TO_ASK, interview, with_override
from .cli_prompts import validate_project_name
from .ecosystems import EXTRA, TARGETS
from .errors import GenerationError
from .experimental import FLAG, HELP, reshaped_intro
from .harness import Agent, chosen, detect, keys, name_of
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
def next_report(root: Path) -> str:
    """`--next` in a repository the method was installed around: the sequence, as the tree has it now."""
    document = read_manifest(root, "slipwai adopt --next")
    adoption = adoption_of(document)
    if adoption is None:
        raise GenerationError(
            "this project was generated, not adopted, so there is no adoption sequence to stand in: a generated "
            "project's next steps are its README, and every row of its map is at the top by construction"
        )
    return next_steps.report(root, layout_of(document), adoption, apps_from_manifest(document))


def agent_line(agent: Agent) -> str:
    """What the report says about which coding agent the material is for, and how that was established."""
    if agent.harness:
        established = "named" if agent.provenance == "overridden" else agent.evidence
        return (
            f"Agent: {name_of(agent.harness)} ({established}), recorded in project.json. `./init` projects the "
            f"skills and commands into it without asking; `--integration <agent>` there changes it."
        )
    if agent.candidates:
        named = ", ".join(name_of(key) for key in agent.candidates)
        return (
            f"Agent: not recorded — this tree reads for more than one ({named}), and which of them gets the "
            "material is a decision, not a guess. `./init` asks."
        )
    return (
        "Agent: not recorded — nothing here says which one, and this did not run from inside one. `./init` asks, "
        "or `./init --integration <agent>` names it."
    )


def run_init(root: Path, delivery: str, agent: Agent) -> None:
    """`./<delivery>/init`, run once the adoption is committed.

    Last, and never inside the commit: it is the one step that reaches the network, so a source that is
    unreachable costs the adoption nothing — the commit is already made — and what it writes is left in the
    tree for the person to read and commit, exactly as it is in a project the factory generated.
    """
    script = Path(delivery) / "init" if delivery != "." else Path("init")
    command = [f"./{script.as_posix()}", *(["--integration", agent.harness] if agent.harness else [])]
    print(f"\nRunning {' '.join(command)} — it installs Spec Kit, which needs the network.")
    finished = subprocess.run(command, cwd=root, check=False)
    if finished.returncode == 0:
        print(
            f"`{' '.join(command)}` is done; what it wrote is uncommitted, and yours to read and commit. "
            "`slipwai adopt --next` says what is left."
        )
        return
    print(
        f"`{' '.join(command)}` exited {finished.returncode}, and the adoption is committed and unaffected: it is "
        f"a step of its own, which is why it runs after. Run it again when whatever stopped it is fixed — "
        f"`slipwai adopt --next` will keep saying that it is the step you are on."
    )


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
    parser.add_argument(FLAG, action="store_true", dest="experimental_intro", help=HELP)
    parser.add_argument(
        "--integration", default=None, metavar="AGENT",
        help="which coding agent gets the skills and commands, by its key in the agent registry (default: the "
        "harness this ran from, or the one the tree already reads; neither, and ./init keeps its own question)",
    )
    init = parser.add_mutually_exclusive_group()
    init.add_argument(
        "--init", action="store_true", dest="run_init", default=None,
        help="run ./<delivery>/init once the adoption is committed, rather than leaving it as the next step. "
        "It reaches Spec Kit's source, so it needs the network; what it writes is left for you to commit",
    )
    init.add_argument(
        "--no-init", action="store_false", dest="run_init", help="do not run ./<delivery>/init (default)"
    )
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
    reshaped = reshaped_intro(args.experimental_intro)
    if args.next_steps:
        try:
            print(next_report(root))
        except GenerationError as error:
            parser.error(str(error))
        return
    if args.refresh:
        try:
            refreshed = resurvey.refresh(root)
        except GenerationError as error:
            parser.error(str(error))
        print(resurvey.report(refreshed))
        return
    try:
        name = args.name or root.name.lower()
        validate_project_name(name)
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
        if not args.yes:
            if not sys.stdin.isatty():
                raise GenerationError(NOTHING_TO_ASK)
            apps, database, infrastructure, ci, release, asked_why = interview(
                root, apps, proposal, args.delivery, reshaped
            )
            why = why or asked_why
        apps = [app for app in apps if app.name not in args.skip]
        if not apps:
            raise GenerationError(NOTHING_LEFT)
        known = {app.name for app in apps}
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
                apps = [with_override(app, **{field: value}) if app.name == target else app for app in apps]
        for given in args.command:
            named, separator, command = given.partition("=")
            app_name, colon, target = named.partition(":")
            if not separator or not colon or target not in (*TARGETS, *EXTRA):
                raise GenerationError(
                    f"--command takes NAME:TARGET=COMMAND with a target among {', '.join((*TARGETS, *EXTRA))}"
                )
            apps = [
                with_override(app, commands={**(app.commands or {}), target: None if command == "-" else command})
                if app.name == app_name else app
                for app in apps
            ]
        for declared in args.hexagonal:
            apps = [with_override(app, structure="hexagonal") if app.name == declared else app for app in apps]
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
        answers = Answers(
            name, args.profile, target, args.delivery, why, apps, database, infrastructure, ci, release,
            agent=agent.record(),
        )
        done = adopt(root, answers, found)
    except GenerationError as error:
        parser.error(str(error))
    print(report(done))
    print(agent_line(agent))
    # `./init` reaches Spec Kit's source, so it is the one step that needs the network, and it leaves files for
    # the person to commit. Off unless asked, and asked for by default only where somebody is sitting at the
    # terminal under the reshaped intro — which is the case the wall of `Next:` lines was written for.
    if args.run_init if args.run_init is not None else (reshaped and not args.yes):
        run_init(root, args.delivery, agent)
