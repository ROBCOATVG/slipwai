"""`slipwai adopt`: the questions, asked with the survey's answers as their defaults, or taken from flags.

Experimental (`AGENTS.md` says what the word means here). Run at the root of a repository the factory
did not make. Bare, in a terminal, it surveys the tree and asks about each thing it found with the found
value as the default — Enter confirms it (`confirmed`), another answer overrides it (`overridden`). With
`--yes` nothing is asked and every proposal stands as `detected`; flags override single answers either way,
and a flag is always `overridden`. Outside a terminal without `--yes` it refuses rather than guessing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import resurvey
from .adopt import Answers, adopt, proposed, report
from .catalog import CATALOG
from .cli_prompts import prompt_choice, prompt_yes_no, validate_project_name
from .ecosystems import EXTRA, TARGETS
from .errors import GenerationError
from .layout import Layout
from .origin import FORGES, HOMES, RELEASE_PATHS, WRAPPED_KINDS
from .services import App
from .survey import survey
from .wrappers import WRAPPERS, missing_wrapper

NOTHING_TO_ASK = "nothing to ask on; pass --yes to accept the survey, with flags for what to change"
NOTHING_FOUND = (
    "nothing here starts a build the survey can read — a package.json, pyproject.toml or requirements.txt, go.mod, "
    "pom.xml, build.gradle, build.xml, a .sln or .csproj, composer.json or Gemfile, at the root or up to three "
    "directories down — so there is no application to wrap, and adoption installs the method around applications. "
    "A build this repository does have and the survey cannot read is a gap in the factory: raise it, naming the file."
)
NOTHING_LEFT = "every application the survey found was skipped or left unwrapped; nothing is left to install around"
HOME_DESCRIPTIONS = {
    "here": "versioned in this repository",
    "elsewhere": "owned by another repository, which you name",
    "unmanaged": "applied by hand, a DBA or a console — versioned nowhere",
    "none": "not part of this system",
}
HOME_QUESTIONS = {
    "schema": "Where is the database schema versioned? (the tables and migrations the code expects)",
    "home": "Where is the deployment infrastructure described? (Terraform, CDK, Compose, Kubernetes — whatever "
    "puts this system on a machine)",
}
KIND_DESCRIPTIONS = {
    "service": "runs somewhere and serves requests or jobs",
    "library": "code other applications import; ships as a package, not a process",
    "tool": "run by hand or in CI — a CLI, a build helper, a migration runner",
    "tests": "a test suite of its own, against something else here",
    "application": "not established — leave it open rather than guess; the record says so",
}
FORGE_DESCRIPTIONS = {
    "github": "GitHub — the gate is an Actions workflow under .github/workflows",
    "gitea": "Gitea or Forgejo — the same Actions workflow, which they run too",
    "gitlab": "GitLab — the gate is a job to include from .gitlab-ci.yml",
    "other": "Jenkins, Azure, Bitbucket, CircleCI or another — nothing is written; your CI runs the gate's command",
    "none": "no CI runs this repository — nothing is written until one does",
}
RELEASE_DESCRIPTIONS = {
    "pipeline": "a CI job deploys it, on some trigger",
    "scripted": "somebody runs a script that deploys it",
    "manual": "by hand: files copied, a console clicked, a package installed",
    "unknown": "not established — recorded as such, and /drive asks before the first slice",
}


def where(path: str) -> str:
    """A directory as the interview names it: the repository root is `.` to the survey and nothing to a reader."""
    return "the repository root (.)" if path == "." else f"`{path}`"


def ask(question: str, default: str | None = None) -> str | None:
    """One free-text question; Enter keeps the default (None for a blank one)."""
    try:
        answer = input(f"{question}{f' [{default}]' if default else ''}: ").strip()
    except EOFError as error:
        raise GenerationError(NOTHING_TO_ASK) from error
    return answer or default


def with_override(app: App, **changes: object) -> App:
    """The application with some fields changed, and those fields' provenance saying so."""
    provenance = {**app.provenance, **{name: "overridden" for name in changes}}
    return App(
        app.name, app.path, str(changes.get("kind", app.kind)), str(changes.get("language", app.language)), None, 0,
        generated=False, commands=changes.get("commands", app.commands),  # type: ignore[arg-type]
        toolchain=app.toolchain, purpose=changes.get("purpose", app.purpose),  # type: ignore[arg-type]
        structure=changes.get("structure", app.structure),  # type: ignore[arg-type]
        provenance=provenance,
    )


def confirmed(app: App, *fields: str) -> App:
    return App(
        app.name, app.path, app.kind, app.language, None, 0, generated=False, commands=app.commands,
        toolchain=app.toolchain, purpose=app.purpose, structure=app.structure,
        provenance={**app.provenance, **{name: "confirmed" for name in fields if name in app.provenance}},
    )


def interview(
    root: Path, apps: list[App], proposal: dict[str, str | None], delivery: str
) -> tuple[list[App], dict, dict, dict, dict, str | None]:
    """The questions, in order, each with the survey's answer as its default, every one saying what its answer
    does; `delivery` is where the method's files will go, so the gate is spelled the way the report will."""
    # `make` where adopt will write the root Makefile, `make -f` where the repository has one of its own — the
    # rule `adopt.report` applies afterwards, applied here so the interview and the report agree.
    verify = "make" if not (root / "Makefile").is_file() else Layout(delivery).make
    print(
        "Adopt the delivery method here (experimental). Each question shows what the survey found as its default:\n"
        "Enter accepts it, another answer replaces it, and project.json records which. In a list, ↑/↓ move and\n"
        "Enter chooses."
    )
    kept: list[App] = []
    for app in apps:
        ecosystem = app.toolchain.get("ecosystem") if app.toolchain else None
        print(f"\nFound a {ecosystem or 'buildable'} build at {where(app.path)}: {app.language}.")
        if not prompt_yes_no(
            f"Wrap it as the application `{app.name}`? (its build joins the gate; n leaves it out entirely)", True
        ):
            continue
        language = ask("Language", app.language)
        app = confirmed(app, "language") if language == app.language else with_override(app, language=language)
        kind = prompt_choice(
            "Kind", list(WRAPPED_KINDS), app.kind, lambda k: KIND_DESCRIPTIONS[k],
            question=f"What is `{app.name}`? (the survey "
            + (f"says {app.kind}" if app.provenance.get("kind") == "detected" else "could not tell")
            + "; Enter keeps that)",
        )
        # Keeping `application` confirms only that nobody knows, so the record stays `unrecorded`, not `confirmed`.
        if kind != app.kind:
            app = with_override(app, kind=kind)
        elif app.provenance.get("kind") == "detected":
            app = confirmed(app, "kind")
        print(f"`{verify} verify` would run these for `{app.name}`, one per Make target:")
        for target, command in (app.commands or {}).items():
            print(f"  {target:<12} {command or '(none recorded)'}")
        if not all((app.commands or {}).values()):
            print("  A target with none recorded is a written no: verify passes it with a line saying so.")
        missing = missing_wrapper(root, app)
        if missing:
            tool, script, _ = WRAPPERS[missing]
            print(
                f"  (there is no {script} here: adopt writes the {tool} Wrapper beside the build file, so these run "
                f"with a JDK and no {tool} installed)"
            )
        if prompt_yes_no("Keep these commands? (n asks about each target in turn)", True):
            app = confirmed(app, "commands")
        else:
            commands = {}
            for target in TARGETS:
                current = (app.commands or {}).get(target) or None
                answer = ask(f"  {target} command (Enter keeps what is shown, `-` records none)", current)
                commands[target] = None if answer in (None, "-") else answer
            app = with_override(app, commands=commands)
        purpose = ask(
            f"What does `{app.name}` own? (a sentence or two, for the docs and the agent; Enter leaves it blank)"
        )
        if purpose:
            app = with_override(app, purpose=purpose)
        kept.append(app)
    print()
    database: dict = {}
    infrastructure: dict = {}
    homes = (("Database schema", "schema", database), ("Deployment infrastructure", "home", infrastructure))
    for label, key, record in homes:
        chosen = prompt_choice(
            label, list(HOMES), str(proposal[key]), lambda home: HOME_DESCRIPTIONS[home], question=HOME_QUESTIONS[key]
        )
        record[key] = chosen
        record["provenance"] = "confirmed" if chosen == proposal[key] else "overridden"
        if chosen == "elsewhere":
            record["repository"] = ask("Which repository owns it? (URL or path)")
    forge = prompt_choice(
        "CI forge", list(FORGES), str(proposal["forge"]), lambda f: FORGE_DESCRIPTIONS[f],
        question="Where does this repository's CI run? (decides what shape the gate's CI configuration can take)",
    )
    ci = {"forge": forge, "provenance": "confirmed" if forge == proposal["forge"] else "overridden"}
    release = prompt_choice(
        "Release path", list(RELEASE_PATHS), proposal["release"] or "unknown", lambda r: RELEASE_DESCRIPTIONS[r],
        question="How does a change reach production today? (the survey "
        + (f"says {proposal['release']}" if proposal["release"] else "found nothing that says") + ")",
    )
    if release == "unknown":
        release_record = {"path": "unknown", "provenance": "unrecorded"}
    else:
        provenance = "confirmed" if release == proposal["release"] else "overridden"
        release_record = {"path": release, "provenance": provenance}
    why = ask("Why is this work happening? (the business trigger, recorded in docs/adoption.md; Enter to skip)")
    return kept, database, infrastructure, ci, release_record, why


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
            apps, database, infrastructure, ci, release, asked_why = interview(root, apps, proposal, args.delivery)
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
        answers = Answers(name, args.profile, target, args.delivery, why, apps, database, infrastructure, ci, release)
        done = adopt(root, answers, found)
    except GenerationError as error:
        parser.error(str(error))
    print(report(done))
