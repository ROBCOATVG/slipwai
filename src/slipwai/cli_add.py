"""The command line's verbs run inside a generated project: `add-service`, `add-frontend`, `migrate`, `replay`.

Split from `cli.py` for the reason `native_commands.py` is split from `makefile.py` — one module was over
the budget — and because these are asked in a different place: `generate` from anywhere, naming a project
that does not exist yet; these from inside one that does, naming the new application or, for `migrate` and
`replay`, nothing at all.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import browser_app
from .add_service import add_frontend_to, add_service_to, describe_service_in, described_report, report
from .assets import VERSION
from .catalog import CATALOG, axis_choices, default_language, families, framework_of, resolve_backend
from .cli_language import braced, missing_backend, missing_framework, missing_language, no_framework
from .converge import check as converge_check
from .converge import check_report as converge_check_report
from .converge import converge
from .converge import report as converge_report
from .errors import GenerationError, refuse
from .manifest import read_manifest
from .npm_workspace import NoBrowserLanguage
from .registry import registry
from .replay import replay
from .replay import report as replay_report
from .shape_converge import check as shape_check
from .shape_converge import prepare as shape_prepare

# Set on the `migrate` this one starts once it has installed languages, which then neither installs nor warns again.
RELAUNCHED = "SLIPWAI_MIGRATE_RELAUNCHED"


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
    # A family loaded with no backend of its own (a framework not installed beside it) is installed: what it lacks
    # is the framework, whose own install line `missing_framework` names.
    if args.language is not None and args.language not in families() and args.language not in registry().families:
        raise GenerationError(missing_language(args.language))
    language = args.language or default_language()
    if language not in families():  # a family alone: its framework's install line, the one asked for or its default
        said = missing_framework(language, args.framework) if args.framework is not None else None
        raise GenerationError(said or no_framework(language))
    offered = [framework_of(backend) for backend in families().get(language, [])]
    if args.framework is not None and args.framework not in offered:
        said = missing_framework(language, args.framework)
        if said is not None:
            raise GenerationError(said)
    return resolve_backend(language, args.framework)


def add_service_main(argv: list[str]) -> None:
    """`add-service <name>`, run inside a generated project: a service's walking skeleton, one more.

    A subcommand rather than a flag on `generate`, because the two commands are asked in different places —
    `generate` from anywhere, naming a project that does not exist yet; `add-service` from inside one that
    does, naming the new service and, optionally, its language and answers. Everything else — profile,
    frontend, target, the first service's language and answers to inherit — is read from `project.json`.
    """
    parser = argparse.ArgumentParser(
        prog="slipwai add-service",
        description="Add a service to the generated project in the current directory",
    )
    parser.add_argument("name", help="the new service's name: apps/<name>, and its Compose service")
    frameworks = sorted(
        {backend["framework"] for backend in CATALOG["backends"].values() if backend.get("framework")}
    )
    parser.add_argument(
        "--language", default=None, metavar=braced(families()),
        help="the new service's language (default: the first service's)",
    )
    parser.add_argument(
        "--framework", default=None, metavar="|".join(frameworks) or "FRAMEWORK",
        help="the framework that owns startup, for a language that offers more than one",
    )
    parser.add_argument("--backend", default=None, metavar=braced(CATALOG["backends"]))
    for axis, spec in CATALOG["axes"].items():
        parser.add_argument(
            f"--{axis}",
            default=None,
            metavar="|".join(axis_choices(axis)),
            help=f"{spec['prompt'].lower()} for the new service (default: the first service's answer where "
            "this backend offers it, else this backend's own default)",
        )
    # What the new service is for. Not a flag the scaffold reads — a flag the delivery loop reads: a second
    # service whose purpose nobody recorded is a directory `/sail` cannot place a slice in.
    parser.add_argument(
        "--purpose", default=None, metavar="TEXT",
        help="what this service owns, in a sentence or two (recorded in project.json; /sail places slices "
        "against it)",
    )
    parser.add_argument(
        "--context", action="append", default=None, metavar="NAME",
        help="a bounded context this service holds — an existing one or a new one; repeat for each (default: "
        "the service itself)",
    )
    args = parser.parse_args(argv)
    try:
        backend = None
        if args.backend is not None or args.language is not None or args.framework is not None:
            if args.backend is None and args.language is None:
                raise GenerationError("--framework needs --language beside it")
            backend = resolve_requested_backend(args)
        named = {axis: getattr(args, axis.replace("-", "_")) for axis in CATALOG["axes"]}
        service, added, rewritten = add_service_to(
            Path.cwd(), args.name, backend, named, purpose=args.purpose, contexts=args.context
        )
    except GenerationError as error:
        refuse(parser.prog, error)
    print(report(service, added, rewritten, read_manifest(Path.cwd())["target"]))


def describe_service_main(argv: list[str]) -> None:
    """`describe-service <name>`, run inside a generated project: what a service already there is for.

    `generate` and `add-service` take `--purpose` and `--context` at scaffold time, but the contexts are found
    later — in the model's lanes, in the specification's vocabulary — and a purpose nobody gave at the start is
    the first question `/sail` asks. This is where the answer goes: the manifest, and every page that prints
    it, so the file an agent reads says what was recorded rather than "no purpose recorded yet".
    """
    parser = argparse.ArgumentParser(
        prog="slipwai describe-service",
        description="Record what a service of the generated project in the current directory is for: what it "
        "owns, the bounded contexts it holds, or both. Nothing is scaffolded; project.json and the files that "
        "print the two fields are rewritten.",
    )
    parser.add_argument("name", help="the service, as project.json names it")
    parser.add_argument(
        "--purpose", default=None, metavar="TEXT",
        help="what this service owns, in a sentence or two; replaces the purpose recorded before",
    )
    parser.add_argument(
        "--context", action="append", default=None, metavar="NAME",
        help="a bounded context this service holds; repeat for each. Together they replace the list recorded "
        "before",
    )
    args = parser.parse_args(argv)
    try:
        service, rewritten = describe_service_in(Path.cwd(), args.name, purpose=args.purpose, contexts=args.context)
    except GenerationError as error:
        refuse(parser.prog, error)
    print(described_report(service, rewritten))


def add_frontend_main(argv: list[str]) -> None:
    """`add-frontend <name>`, run inside a generated project: one more browser app.

    The same shape as `add-service`, for the other kind of application. The only question a browser app has
    is which service its `/api` calls go to, and the first service is the answer unless told otherwise.
    """
    parser = argparse.ArgumentParser(
        prog="slipwai add-frontend",
        description="Add a browser app to the generated project in the current directory",
    )
    parser.add_argument("name", help="the new browser app's name: apps/<name>, and its Compose service")
    parser.add_argument("--api", default=None, help="the service its /api calls go to (default: the first)")
    args = parser.parse_args(argv)
    try:
        app, added, rewritten = add_frontend_to(Path.cwd(), args.name, args.api)
    except NoBrowserLanguage:
        refuse(parser.prog, browser_app.refusal("a browser app", generate=False))
    except GenerationError as error:
        refuse(parser.prog, error)
    print(report(app, added, rewritten))


def converge_main(argv: list[str]) -> None:
    """`converge`, run inside an adopted repository whose every map row reads *as generated*: move the delivery
    material to the root as one merge. `--check` only says whether it is ready, and why not."""
    parser = argparse.ArgumentParser(
        prog="slipwai converge",
        description="End an adoption: once every row of the convergence map is at a generated project's rung, move "
        "the delivery material from its directory to the root as one merge",
        epilog="`--check` reads and reports — rows below target, rows the tree contradicts, files at the root the "
        "move would write over — and moves nothing. Without it, the move is a merge commit and a follow-up commit "
        "for what the merge cannot carry; `git reset --hard ORIG_HEAD~1` undoes both. Nothing is pushed.",
    )
    parser.add_argument("--check", action="store_true", help="say whether this repository is ready, and stop")
    parser.add_argument(
        "--shape", choices=("skiff", "liner"),
        help="prepare a deployment change and data-preserving cutover runbook",
    )
    args = parser.parse_args(argv)
    try:
        if args.shape:
            if args.check:
                print(shape_check(Path.cwd(), args.shape))
            else:
                print(f"Prepared: {shape_prepare(Path.cwd(), args.shape)}; read RUNBOOK.md before any apply or cutover")
            return
        if args.check:
            readiness = converge_check(Path.cwd())
            print(converge_check_report(readiness))
            raise SystemExit(0 if readiness.ready else 1)
        done = converge(Path.cwd())
    except GenerationError as error:
        refuse(parser.prog, error)
    print(converge_report(done))
    if done.conflicts:
        raise SystemExit(1)


def replay_main(argv: list[str]) -> None:
    """`replay`, run inside a generated project: this keel's output for its answers, beside it, as a merge.

    The half of `migrate` that writes without merging, for looking before taking: no name to give — the
    project's `project.json` has every answer — and nothing here is written into the project. The result is
    a repository whose one commit sits on the project's last factory commit, and the report is the two `git`
    commands that offer it to the project.
    """
    parser = argparse.ArgumentParser(
        prog="slipwai replay",
        description="Write what this factory generates for the project in the current directory, beside it, "
        "as a commit the project can merge — `slipwai migrate` without the merge, to look at first",
        epilog="Nothing in the project is touched: a replay is an offer, and `git merge` is how the project "
        "takes or refuses each part of it. A language installed at a version older than project.json records is "
        "refused; one that differs is named. docs/upgrading.md in the factory is the recipe.",
    )
    parser.add_argument(
        "--into", type=Path, default=None, metavar="DIR",
        help=f"an empty or absent directory to write into (default: ../<name>-at-{VERSION})",
    )
    parser.add_argument(
        "--base", default=None, metavar="REV",
        help="the project commit the replay sits on (default: the newest commit in its history the factory "
        "made — the scaffold, or the last replay merged)",
    )
    args = parser.parse_args(argv)
    try:
        done = replay(Path.cwd(), args.into, args.base)
    except GenerationError as error:
        refuse(parser.prog, error)
    print(replay_report(done))

