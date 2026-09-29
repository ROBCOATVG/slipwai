"""The command line: one question per answer, asked or passed, and the refusals in between."""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from .assets import DEFAULT_OUTPUT, VERSION
from .catalog import CATALOG, axis_applies, families, family_of, validate_catalog
from .cli_add import (
    add_frontend_main,
    add_service_main,
    converge_main,
    describe_service_main,
    migrate_main,
    replay_main,
    resolve_requested_backend,
)
from .cli_adopt import adopt_main
from .cli_init import add_setup_arguments, agent_for_setup, install_tools, installing, run_generated_init, tools_for
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
    valid_project_name,
    validate_project_name,
)
from .errors import GenerationError
from .harness import keys
from .preflight import check as check_requirements
from .scaffold import write_project
from .selection import resolve_selection
from .services import FIRST_SERVICE, FIRST_WEB, default_apps
from .targets import check_project_name, offered_backends
from .upgrade import main as upgrade_main

VERBS = ("generate", "add-service", "add-frontend", "describe-service", "migrate", "replay", "upgrade", "adopt",
         "converge")


def main() -> None:
    """`slipwai <verb>`: `generate` from anywhere, naming a project that does not exist yet; `add-service`,
    `add-frontend`, `describe-service`, `migrate` and `replay` from inside one that does; `upgrade` from
    anywhere, about the command itself rather than about any project. Each verb owns its parser, so
    `slipwai generate --help` is the generator's flags and nothing else's."""
    # What slipwai prints — its questions' arrows and dashes — is UTF-8. Windows gives a redirected stream (a pipe,
    # a CI log) its ANSI code page, cp1252, and a print there raised UnicodeEncodeError; a console was fine.
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if encoding != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    validate_catalog(CATALOG)
    argv = sys.argv[1:]
    if argv[:1] == ["generate"]:
        generate_main(argv[1:])
        return
    if argv[:1] == ["add-service"]:
        add_service_main(argv[1:])
        return
    if argv[:1] == ["add-frontend"]:
        add_frontend_main(argv[1:])
        return
    if argv[:1] == ["describe-service"]:
        describe_service_main(argv[1:])
        return
    if argv[:1] == ["migrate"]:
        migrate_main(argv[1:])
        return
    if argv[:1] == ["replay"]:
        replay_main(argv[1:])
        return
    if argv[:1] == ["upgrade"]:
        upgrade_main(argv[1:])
        return
    if argv[:1] == ["adopt"]:
        adopt_main(argv[1:])
        return
    # "Where am I?" asked the ways people ask it — `slipwai status`, `slipwai --next` — is `adopt --next`.
    if argv[:1] in (["status"], ["next"], ["--status"], ["--next"]):
        adopt_main(["--next", *argv[1:]])
        return
    if argv[:1] == ["converge"]:
        converge_main(argv[1:])
        return
    parser = argparse.ArgumentParser(
        prog="slipwai",
        description="Scaffold a new product monorepo from a delivery foundation, and grow one afterwards",
        epilog="`%(prog)s generate` asks one question at a time; `%(prog)s generate <name> [flags]` is the form "
        "for scripts and CI. Inside a generated project, `%(prog)s add-service <name>` adds a service and "
        "`%(prog)s add-frontend <name>` a browser app, and `%(prog)s migrate` brings the project up to this "
        "version of the factory as one merge, leaving the catch-up notes for `/catch-up` to work through "
        "(`%(prog)s replay` writes the same beside it, to look at first). "
        "`%(prog)s upgrade` replaces this command with the newest version the forge has. `%(prog)s adopt`, run in "
        "a repository this factory did not make, installs the method around it, and `%(prog)s converge` ends that "
        "adoption once every row of its map reads as generated (both experimental); `%(prog)s status` says where an "
        "adopted repository stands. `%(prog)s <verb> --help` lists a verb's flags.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument(
        "verb", nargs="?", choices=VERBS,
        help="generate, add-service, add-frontend, migrate, replay, upgrade, adopt or converge",
    )
    parser.parse_args(argv)
    # Every verb returned above, so reaching here means none was given.
    parser.error("a verb is required: generate, add-service, add-frontend, migrate, replay, upgrade, adopt or converge")


def generate_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="slipwai generate",
        description="Scaffold a new product monorepo from a delivery foundation",
        epilog="Bare, the questions are asked one at a time; with a name and flags, nothing is asked.",
    )
    parser.add_argument("name", nargs="?", help="new project and repository name")
    parser.add_argument("--profile", choices=CATALOG["profiles"], default=CATALOG["default"]["profile"])
    # Where the project goes to production. Asked second in the interactive form because it decides the
    # menus that follow; a flag whatever the catalog offers, so a script can say `--target none` today and
    # keep saying it the day there is a second answer.
    parser.add_argument(
        "--target",
        choices=CATALOG["targets"],
        default=CATALOG["default"]["target"],
        help="where this project goes to production (default: %(default)s)",
    )
    # Two questions rather than one, because that is how the choice is actually made: which language,
    # then — where the ecosystem has something that owns startup — which framework. They resolve to the
    # single backend key everything downstream is keyed by. `--backend` names that key directly, which is
    # what scripts and CI want.
    frameworks = sorted(
        {backend["framework"] for backend in CATALOG["backends"].values() if backend.get("framework")}
    )
    parser.add_argument("--language", choices=list(families()), default=None)
    parser.add_argument(
        "--framework",
        default=None,
        metavar="|".join(frameworks) or "FRAMEWORK",
        help="the framework that owns startup, for a language that offers more than one",
    )
    parser.add_argument("--backend", choices=CATALOG["backends"], default=None)
    parser.add_argument("--frontend", choices=CATALOG["frontends"], default=CATALOG["default"]["frontend"])
    # What the first service and the first browser app are called: `apps/<name>`, the Compose service, the
    # package. Asked, because a project with several services has no service called "service" — and once
    # `add-service` names every later one, the first one being unnameable would be the odd one out.
    parser.add_argument(
        "--service-name", default=FIRST_SERVICE, metavar="NAME",
        help="the first service's name: apps/<name> (default: %(default)s)",
    )
    parser.add_argument(
        "--frontend-name", default=None, metavar="NAME",
        help=f"the browser app's name: apps/<name> (default: {FIRST_WEB}; needs a frontend)",
    )
    # What the first service is for, and which bounded contexts it holds. Recorded in `project.json` and
    # read by the delivery loop when slices have to be placed — between services once a later one arrives,
    # and between contexts inside one service as soon as it holds two; nothing scaffolded changes with
    # either answer.
    parser.add_argument(
        "--purpose", default=None, metavar="TEXT",
        help="what the first service owns, in a sentence or two (recorded in project.json)",
    )
    parser.add_argument(
        "--context", action="append", default=None, metavar="NAME",
        help="a bounded context the first service holds; repeat for each (default: the service itself)",
    )
    # One flag per axis, named for the role it fills rather than for a product, and mirroring the flags the
    # generated project's own `./init` takes. Deliberately not `choices`: which options are legal depends
    # on the profile and backend chosen alongside them, so `resolve_selection` validates and says why —
    # argparse would only be able to say "invalid choice".
    for axis, spec in CATALOG["axes"].items():
        parser.add_argument(
            f"--{axis}",
            default=None,
            metavar="|".join(spec["options"]),
            help=f"{spec['prompt'].lower()} to scaffold (default: {spec['absent']})",
        )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    # A production target needs tools scaffolding does not, and they are checked the moment the target is
    # known rather than at the end of `./init`. Skipped only when another machine will run that.
    parser.add_argument(
        "--skip-checks", action="store_true",
        help="do not check that this machine has what the target's ./init needs (tofu, the aws CLI, a forge)",
    )
    # What follows the files — the agent, the project's `./init` (the same run `adopt` ends with), and the tools
    # both need — is on by default only where somebody answered the questions at a terminal: the flag form is
    # for scripts and CI, where a step that reaches the network, asks a question or runs sudo is not wanted
    # unless asked for.
    add_setup_arguments(parser, "./init")
    args = parser.parse_args(argv)
    try:
        named = {axis: getattr(args, axis.replace("-", "_")) for axis in CATALOG["axes"]}
        if args.integration is not None and args.integration not in keys():
            raise GenerationError(
                f"--integration names `{args.integration}`, and the agent registry has no such harness; "
                f"one of: {', '.join(sorted(keys()))}"
            )
        # Bare, or bare but for the flags that have nothing to prompt about, is the interactive form.
        interactive = all(argument in RUN_SHAPE for argument in without_integration(argv))
        attended = interactive and sys.stdin.isatty()
        install = installing(args.install, attended)
        running_init = args.run_init if args.run_init is not None else attended
        # Run in an empty folder, the folder is the project: its name is offered, and the project is written into
        # it rather than into a new folder beneath it — so the agent started in the same place finds its commands.
        here = Path.cwd()
        in_place = interactive and not any(here.iterdir())
        if interactive:
            print("Create a new product monorepo. Press Enter to accept a shown default.")
            args.name = prompt_project_name(here.name if in_place and valid_project_name(here.name) else None)
            args.profile = prompt_profile()
            args.target = prompt_target()
            # Asked before the target and checked against it: a name the target's cloud will not take is
            # said here, not after another nine questions.
            check_project_name(CATALOG, args.target, args.name)
            check_requirements(args.target, args.skip_checks, install=install)
            # Only the languages with a backend offered under the target: the target decides the menus.
            offered = offered_backends(CATALOG, args.target)
            languages = [family for family, members in families().items() if set(members) & set(offered)]
            preferred = family_of(CATALOG["default"]["backend"])
            language = prompt_choice("Language", languages, preferred if preferred in languages else languages[0])
            backend = prompt_framework(language, args.target)
            args.service_name = prompt_application_name("Service name", FIRST_SERVICE, set())
            args.purpose = prompt_purpose(args.service_name)
            args.context = prompt_context(args.service_name)
            args.frontend = prompt_choice("Frontend", list(CATALOG["frontends"]), CATALOG["default"]["frontend"])
            if args.frontend != "none":
                args.frontend_name = prompt_application_name("Browser app name", FIRST_WEB, {args.service_name})
            # One question per axis, asked separately, because they are separate questions: where events
            # are stored has nothing to do with who issues identities. An axis is asked only when this
            # profile and backend can actually be given a choice, so the prompt never offers a combination
            # that `resolve_selection` would then refuse.
            for axis in CATALOG["axes"]:
                if not axis_applies(axis, args.profile, backend, args.target):
                    continue
                named[axis] = prompt_axis(axis, args.profile, backend, args.target)
            if running_init:
                args.integration = agent_for_setup(args.integration, asking=True)
            args.output = here.parent if in_place else prompt_output(DEFAULT_OUTPUT)
            args.backend = backend
        elif args.name is None:
            raise GenerationError("project name is required")
        validate_project_name(args.name)
        check_project_name(CATALOG, args.target, args.name)
        if not interactive:
            check_requirements(args.target, args.skip_checks, install=install)
            if running_init:
                args.integration = agent_for_setup(args.integration, asking=False)
        backend = resolve_requested_backend(args)
        if backend not in offered_backends(CATALOG, args.target):
            offered = offered_backends(CATALOG, args.target)
            raise GenerationError(
                f"--backend {backend} is not offered under the {args.target} target, which can be built on "
                f"{'/'.join(offered)}: a project that cannot be built for where it is going is deliberately "
                f"not emitted. Generate with --backend {offered[0]}, or with --target "
                f"{CATALOG['backends'][backend]['targets'][0]}."
            )
        selection = resolve_selection(named, args.profile, backend, args.target)
        if args.frontend_name is not None and args.frontend == "none":
            raise GenerationError("--frontend-name names a browser app, and --frontend none has none to name")
        apps = default_apps(
            backend, args.frontend, selection, args.service_name, args.frontend_name or FIRST_WEB,
            purpose=args.purpose, contexts=args.context,
        )
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        destination = here if in_place else output / args.name
        if destination.exists() and not in_place:
            raise GenerationError(f"refusing to overwrite existing target: {destination}")
        if install:
            install_tools(["git"], install)  # the project is committed as it is written
        with tempfile.TemporaryDirectory(prefix=f".{args.name}-", dir=output) as staging:
            staging_path = Path(staging)
            write_project(staging_path, args.name, args.profile, args.target, apps)
            if in_place:
                # Moved in entry by entry: the folder is where the person is standing, so it is kept, not replaced.
                for entry in staging_path.iterdir():
                    shutil.move(str(entry), str(destination / entry.name))
            else:
                staging_path.rename(destination)
        print(f"created: {destination}")
    except GenerationError as error:
        parser.error(str(error))
    if install:
        # Every language the project builds in, so its `make verify` runs on this machine the day it is made.
        languages = [family_of(backend), *(["typescript"] if args.frontend != "none" else [])]
        install_tools(tools_for(languages), install)
    if running_init:
        run_generated_init(destination, args.integration, install)


# The flags that say how `generate` runs rather than what it makes, so passing one keeps the questions.
RUN_SHAPE = ("--skip-checks", "--init", "--no-init", "--install", "--no-install")


def without_integration(argv: list[str]) -> list[str]:
    """`argv` without `--integration` and its value, which name what `./init` does rather than the project."""
    kept: list[str] = []
    skip = False
    for argument in argv:
        if skip:
            skip = False
        elif argument == "--integration":
            skip = True
        elif not argument.startswith("--integration="):
            kept.append(argument)
    return kept
