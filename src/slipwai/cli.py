"""The command line: one question per answer, asked or passed, and the refusals in between."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .assets import DEFAULT_OUTPUT, VERSION
from .browser_app import frontend_menu, no_browser
from .catalog import (
    CATALOG,
    PACKAGES,
    axis_applies,
    axis_choices,
    default_language,
    families,
)
from .catalog_checks import validate_catalog
from .cli_add import (
    add_frontend_main,
    add_service_main,
    converge_main,
    describe_service_main,
    migrate_main,
    replay_main,
)
from .cli_adopt import adopt_main
from .cli_bridge import bridge_main
from .cli_channel import channel_main
from .cli_extension import extension_main, hooks_main
from .cli_fleet import fleet_main
from .cli_language import (
    braced,
    language_main,
    list_main,
    not_installed_frameworks,
    not_installed_languages,
    nothing_loaded,
    undeclared_target,
)
from .cli_offered import resolve_requested_backend
from .cli_package import package_main
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
    validate_project_name,
)
from .cli_search import search_main, show_main
from .cli_target import target_main
from .cli_telegraph import telegraph_main
from .cli_trust import trust_main
from .errors import GenerationError, failure, refuse
from .language_directory import Package, refusal
from .language_upkeep import after_core
from .loaded import refusals
from .preflight import check as check_requirements
from .registry import RegistryError
from .scaffold import write_project
from .selection import resolve_selection
from .services import FIRST_SERVICE, FIRST_WEB, default_apps
from .targets import check_project_name, offered_backends
from .upgrade import main as upgrade_main

# One verb so far. Each of the others is registered here by the slice that brings its module
# back, so an unknown argument is argparse's refusal rather than a stub that half-answers.
VERBS = ("generate", "add-service", "add-frontend", "describe-service", "migrate", "replay",
         "adopt", "converge", "upgrade", "list", "search", "show", "install", "language", "extension",
         "hooks", "package", "target", "trust", "channel", "telegraph", "fleet", "bridge")


def main() -> None:
    """`slipwai <verb>`: `generate` from anywhere, naming a project that does not exist yet; `add-service`,
    `add-frontend`, `describe-service`, `migrate` and `replay` from inside one that does; `upgrade` from
    anywhere, about the command itself rather than about any project. Each verb owns its parser, so
    `slipwai generate --help` is the generator's flags and nothing else's."""
    try:
        validate_catalog(CATALOG)
    except RegistryError as error:
        # A language that does not fit the protocol is a fault in the installation, not in the request: one
        # line and a non-zero exit, before any verb has written a file.
        sys.exit(f"slipwai: {error}")
    # A language package that could not load is one line here, once, and the verb runs without it.
    for refused in refusals():
        print(f"slipwai: {refused}", file=sys.stderr)
    try:
        dispatch(sys.argv[1:])
    except KeyboardInterrupt:
        raise
    except BaseException as error:
        # A package's answer that exits ends itself, not the verb, and one that raises is one line naming it
        # rather than a traceback naming no package.
        owner = package_that_raised(error)
        if owner is None:
            raise
        sys.exit(f"slipwai: {refusal(owner.name, owner.root, package_fault(error))}")


def package_that_raised(error: BaseException) -> Package | None:
    """The language package whose code `error` was raised from: the innermost frame of its traceback
    that is a file inside a package's directory. None where no frame is, so the keel's own exceptions
    are never reported under a package's name."""
    roots = [(package, package.root.resolve()) for package in PACKAGES]
    owner = None
    frame = error.__traceback__
    while frame is not None:
        file = frame.tb_frame.f_code.co_filename
        if Path(file).is_absolute():
            owner = next((package for package, root in roots if Path(file).resolve().is_relative_to(root)), owner)
        frame = frame.tb_next
    return owner


def package_fault(error: BaseException) -> str:
    """What a package's code did, as its refusal says it: an exit, or the exception it raised."""
    if not isinstance(error, SystemExit):
        return failure(error)
    return f"tried to exit ({failure(error)}); a package ends itself, not the verb"


def dispatch(argv: list[str]) -> None:
    """Run the verb `argv` names, or say that none was given."""
    if argv[:1] == ["generate"]:
        generate_main(argv[1:])
        return
    if argv[:1] == ["list"]:
        list_main(argv[1:])
        return
    # `hooks` is a verb of its own rather than `extension hooks`: the question it answers — "why did that
    # not run?" — is asked about the loop, by someone who may not know an extension is what to look for.
    for verb, run in (("add-service", add_service_main), ("add-frontend", add_frontend_main),
                      ("describe-service", describe_service_main), ("migrate", migrate_main),
                      ("replay", replay_main), ("adopt", adopt_main), ("converge", converge_main),
                      ("extension", extension_main), ("hooks", hooks_main), ("package", package_main),
                      ("target", target_main),
                      ("trust", trust_main), ("channel", channel_main), ("telegraph", telegraph_main),
                      ("fleet", fleet_main), ("bridge", bridge_main)):
        if argv[:1] == [verb]:
            run(argv[1:])
            return
    # `upgrade` replaces this command with the newest the index has, and `after_core` moves any
    # installed package the new keel would refuse — an upgrade that left them behind would leave a
    # working copy that generates nothing.
    if argv[:1] == ["upgrade"]:
        upgrade_main(argv[1:], languages=after_core)
        return
    # "Where am I?" asked the ways people ask it — `slipwai status`, `slipwai --next` — is `adopt --next`.
    if argv[:1] in (["status"], ["next"], ["--status"], ["--next"]):
        adopt_main(["--next", *argv[1:]])
        return
    for verb, run in (("search", search_main), ("show", show_main), ("language", language_main)):
        if argv[:1] == [verb]:
            run(argv[1:])
            return
    # `slipwai install <name>` is `slipwai language install <name>`. The short form is what a reader
    # types after a search result tells them a package exists; the long one stays, because `language
    # upgrade` and `language remove` have no short form worth having.
    if argv[:1] == ["install"]:
        language_main(["install", *argv[1:]])
        return
    parser = argparse.ArgumentParser(
        prog="slipwai",
        description="Scaffold a new product monorepo from a delivery foundation, and grow one afterwards",
        epilog="`%(prog)s generate` asks one question at a time; `%(prog)s generate <name> [flags]` is the "
        "form for scripts and CI. `%(prog)s generate --help` lists its flags. The other verbs — adopting "
        "an existing repository, adding a service, installing a language, upgrading this command — arrive "
        "with the slices that bring them back.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument(
        "verb", nargs="?", choices=VERBS,
        help="generate",
    )
    parser.parse_args(argv)
    # Every verb returned above, so reaching here means none was given.
    # Built from VERBS, not written out: the list was version 1's for an afternoon and named six verbs
    # this copy has not got, which is a worse answer than no list at all.
    parser.error("a verb is required: " + ", ".join(VERBS))


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
    # Checked by `resolve_requested_backend` rather than by `choices`, so a language or backend that is not installed
    # is refused with the line that installs it, not argparse's "invalid choice"; the help reads as before.
    parser.add_argument("--language", default=None, metavar=braced(families()))
    parser.add_argument(
        "--framework",
        default=None,
        metavar="|".join(frameworks) or "FRAMEWORK",
        help="the framework that owns startup, for a language that offers more than one",
    )
    parser.add_argument("--backend", default=None, metavar=braced(CATALOG["backends"]))
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
            metavar="|".join(axis_choices(axis)),
            help=f"{spec['prompt'].lower()} to scaffold (default: {spec['absent']})",
        )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    # A production target needs tools scaffolding does not, and they are checked the moment the target is
    # known rather than at the end of `./init`. Skipped only when another machine will run that.
    parser.add_argument(
        "--skip-checks", action="store_true",
        help="do not check that this machine has what the target's ./init needs (tofu, the aws CLI, a forge)",
    )
    args = parser.parse_args(argv)
    try:
        named = {axis: getattr(args, axis.replace("-", "_")) for axis in CATALOG["axes"]}
        # Bare, or bare but for the one flag that has nothing to prompt about, is the interactive form.
        interactive = all(argument == "--skip-checks" for argument in argv)
        if interactive:
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
            backend = prompt_framework(language, args.target, not_installed_frameworks(language))
            args.service_name = prompt_application_name("Service name", FIRST_SERVICE, set())
            args.purpose = prompt_purpose(args.service_name)
            args.context = prompt_context(args.service_name)
            frontends, default, unavailable = frontend_menu()
            args.frontend = prompt_choice("Frontend", frontends, default, unavailable=unavailable, status="unavailable")
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
            args.output = prompt_output(DEFAULT_OUTPUT)
            args.backend = backend
        elif args.name is None:
            raise GenerationError("project name is required")
        validate_project_name(args.name)
        check_project_name(CATALOG, args.target, args.name)
        if not interactive:
            if args.backend is None and args.language is None and not CATALOG["backends"]:
                raise GenerationError(nothing_loaded())
            if (undeclared := undeclared_target(args.target)) is not None:
                raise GenerationError(undeclared)
            check_requirements(args.target, args.skip_checks)
        backend = resolve_requested_backend(args)
        if (unbuildable := no_browser(args.frontend)) is not None:
            raise GenerationError(unbuildable)
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
        destination = output / args.name
        if destination.exists():
            raise GenerationError(f"refusing to overwrite existing target: {destination}")
        with tempfile.TemporaryDirectory(prefix=f".{args.name}-", dir=output) as staging:
            staging_path = Path(staging)
            write_project(staging_path, args.name, args.profile, args.target, apps)
            staging_path.rename(destination)
        print(f"created: {destination}")
    except GenerationError as error:
        refuse(parser.prog, error)
