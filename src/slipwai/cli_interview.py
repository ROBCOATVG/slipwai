"""The questions `slipwai adopt` asks in a terminal, and what each answer does to the record.

Experimental (#74; `AGENTS.md` says what the word means here). Split from `cli_adopt`, which owns the parser
and the flags: this is the interview itself — the descriptions each list shows, the order the questions come
in, and the provenance an answer carries (Enter over a survey finding is `confirmed`, a different answer is
`overridden`). It is also the part the reshaped intro is rewriting, so it is worth having on its own.
"""
from __future__ import annotations

from pathlib import Path

from .cli_prompts import prompt_choice, prompt_yes_no
from .ecosystems import TARGETS
from .errors import GenerationError
from .layout import Layout
from .origin import FORGES, HOMES, RELEASE_PATHS, WRAPPED_KINDS
from .services import App
from .wrappers import WRAPPERS, missing_wrapper

NOTHING_TO_ASK = "nothing to ask on; pass --yes to accept the survey, with flags for what to change"

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
    root: Path, apps: list[App], proposal: dict[str, str | None], delivery: str, reshaped: bool = False
) -> tuple[list[App], dict, dict, dict, dict, str | None]:
    """The questions, in order, each with the survey's answer as its default, every one saying what its answer
    does; `delivery` is where the method's files will go, so the gate is spelled the way the report will.

    `reshaped` is the experimental intro (`experimental.py`): the questions a terminal cannot answer well are
    not asked in one, and the language is the first of them to go."""
    # `make` where adopt will write the root Makefile, `make -f` where the repository has one of its own — the
    # rule `adopt.report` applies afterwards, applied here so the interview and the report agree.
    verify = "make" if not (root / "Makefile").is_file() else Layout(delivery).make
    print(
        "Adopt the delivery method here (experimental). Each question shows what the survey found as its default:\n"
        "Enter accepts it, another answer replaces it, and project.json records which. In a list, ↑/↓ move and\n"
        "Enter chooses."
        + (
            "\nA language is read off the build file and shown rather than asked; `--language NAME=LANGUAGE` is "
            "where to correct one."
            if reshaped else ""
        )
    )
    kept: list[App] = []
    for app in apps:
        ecosystem = app.toolchain.get("ecosystem") if app.toolchain else None
        print(f"\nFound a {ecosystem or 'buildable'} build at {where(app.path)}: {app.language}.")
        if not prompt_yes_no(
            f"Wrap it as the application `{app.name}`? (its build joins the gate; n leaves it out entirely)", True
        ):
            continue
        if not reshaped:
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
