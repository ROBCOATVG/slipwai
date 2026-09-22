"""`adopt`: install the delivery method around a repository that already exists — Survey, then Wrap.

Brownfield adoption (experimental), experimental as `AGENTS.md` defines the word. The factory's other verbs make a
repository or grow one they made; this one is run at the root of somebody else's and adds the method beside
their code: the gate, CI for it, the skills, commands and documentation, the agent projections, and a
`project.json` that records what was here — detected by the survey, confirmed or overridden by the person —
rather than what was chosen.

What it writes is what `scaffold.project_files` assembles for an adopted project, under `layout.delivery`,
cut to what such a repository takes (`project/adopted.py`); what it appends is a marked block to `AGENTS.md`
and to `.gitignore`, once, and `.claude/settings.json` where there is none. Nothing of the repository's own
is written over, and the whole of it is one commit by the factory, which is how `replay` finds its base the
next time. Refused: a directory that is not a Git repository (`git init` is day zero, not a workaround), an
unclean tree, and a repository that already has a `project.json` — `slipwai migrate` brings that one forward.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .adopt_report import MAKEFILE, SETTINGS, Adopted, report, survey_page
from .assets import VERSION
from .errors import GenerationError
from .layout import Layout
from .origin import FORGES, RELEASE_PATHS, Adoption
from .platform import with_platform
from .project.adopted import WRITTEN, agents_block, gitignore_block, makefile_block
from .project.adopted_ci import gate_path
from .project.agent_settings import claude_settings
from .project.gitignore import build_artifacts
from .project.pin_commands import PINNED_LEDGER
from .project.run_skill import RUNNING, running_ledger
from .project.strangle_command import RETIREMENT, RETIREMENT_LEDGER
from .project.structure_page import structure_page
from .scaffold import FACTORY_IDENTITY, NO_MAINTENANCE, project_files
from .services import App, check_name, wrapped_of
from .strategy import with_recommendation
from .structure import structure
from .survey import Survey, survey
from .toolkit import executable_paths
from .wrappers import write_wrappers

AGENTS = "AGENTS.md"
GITIGNORE = ".gitignore"
SURVEY_PAGE = "survey/survey.md"
STRUCTURE_PAGE = "survey/structure.md"
PINNED = "survey/pinned.md"


@dataclass(frozen=True)
class Answers:
    """What the person decided, over what the survey proposed. Each `provenance` says which of the two it was."""

    name: str
    profile: str = "standard"
    # `existing` wherever the repository deploys somewhere; `none` where its infrastructure is `none`.
    target: str = "existing"
    delivery: str = "delivery"
    why: str | None = None
    # Per wrapped application, by name: the fields as recorded, and where each came from.
    applications: list[App] = field(default_factory=list)
    database: dict = field(default_factory=dict)
    infrastructure: dict = field(default_factory=dict)
    # `{"forge": ..., "provenance": ...}` and `{"path": ..., "provenance": ...}`; empty means the survey's proposal
    # stands as `detected`, or as `unrecorded` where the tree said nothing.
    ci: dict = field(default_factory=dict)
    release: dict = field(default_factory=dict)


def check_repository(root: Path) -> None:
    """A clean Git repository with no `project.json`, or the reason it is not one to adopt."""
    inside = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], cwd=root, text=True, capture_output=True, check=False
    )
    if not inside.stdout.startswith("true"):
        raise GenerationError(
            f"{root} is not a Git repository. Adoption is a commit the factory makes and later merges over, so "
            "`git init` (or a one-way import from Subversion or TFS) is day zero, not a step to work around."
        )
    if (root / "project.json").is_file():
        raise GenerationError(
            "this repository already has a project.json, so the method is already here: `slipwai migrate` "
            "brings it forward, and `add-service` grows it. Adopting again would write over what was confirmed."
        )
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=True)
    if status.stdout.strip():
        raise GenerationError(
            "this repository has uncommitted changes; commit or stash them first, so that the adoption is the "
            "only thing this command leaves behind and `git reset --hard HEAD^` undoes exactly that"
        )


def wrapped_app(
    name: str, path: str, language: str, commands: dict, toolchain: dict, purpose: str | None,
    provenance: dict[str, str], kind: str = "application",
) -> App:
    """One application that already existed, as the manifest records it."""
    check_name([], name)
    return App(
        name, path, kind, language, None, 0, generated=False, commands=commands, toolchain=toolchain,
        purpose=purpose or None, provenance=provenance,
    )


def proposed(found: Survey, name: str) -> list[App]:
    """Every buildable directory the survey found, as the application `adopt` would record with no one changing
    anything: every fact `detected`."""
    apps = []
    taken: set[str] = set()
    for root in found.roots:
        candidate = root.name(name)
        while candidate in taken:
            candidate += "-2"
        taken.add(candidate)
        detected = root.found
        toolchain = {**detected.toolchain, "ecosystem": detected.ecosystem}
        if detected.packaging:
            toolchain["packaging"] = detected.packaging
        # What the directory is for is recorded only where a file said: `application` with `unrecorded`
        # provenance is the written form of "nobody has said yet", never a default that looks like an answer.
        apps.append(wrapped_app(
            candidate, root.path, detected.language, dict(detected.commands), toolchain, None,
            {"language": "detected", "commands": "detected", "kind": "detected" if root.role else "unrecorded"},
            kind=root.role or "application",
        ))
    return apps


def facts(found: Survey, answers: Answers, layout: Layout) -> Adoption:
    """The project-level record: the person's answers where given, the survey's proposal where not — and where
    the tree said nothing and nobody was asked, `unrecorded`, which is a fact about the record and not a guess."""
    database = answers.database or {"schema": found.schema_home, "provenance": "detected"}
    infrastructure = answers.infrastructure or {"home": found.infrastructure_home, "provenance": "detected"}
    forge, forge_evidence = found.forge
    ci = answers.ci or {"forge": forge, "provenance": "detected"}
    assert ci["forge"] in FORGES
    # A refresh that found no CI of the repository's own while the gate this factory wrote is there keeps the forge
    # (`resurvey.refresh`), and the evidence says what the tree does hold rather than that it holds nothing.
    if forge == "none" and ci.get("gate") and ci["forge"] != "none":
        forge_evidence = f"the delivery gate this factory wrote, {ci['gate']}"
    release = answers.release or (
        {"path": found.release_path, "provenance": "detected"} if found.release_path
        else {"path": "unknown", "provenance": "unrecorded"}
    )
    assert release["path"] in RELEASE_PATHS
    return Adoption(
        why=answers.why,
        ci={
            "forge": ci["forge"],
            "gate": gate_path(ci["forge"], layout),
            "branch": found.default_branch,
            "evidence": forge_evidence,
            "provenance": ci["provenance"],
        },
        release={
            "path": release["path"],
            "evidence": [f"{kind}: {path}" for kind, path in found.release_evidence],
            "provenance": release["provenance"],
        },
        database={
            "schema": database["schema"],
            "tools": sorted({tool for tool, _ in found.schema_tools}),
            "drivers": sorted({driver for driver, _ in found.drivers}),
            **({"repository": database["repository"]} if database.get("repository") else {}),
            "provenance": database["provenance"],
        },
        infrastructure={
            "home": infrastructure["home"],
            "describedBy": sorted({kind for kind, _ in found.infrastructure}),
            **({"repository": infrastructure["repository"]} if infrastructure.get("repository") else {}),
            "provenance": infrastructure["provenance"],
        },
        survey={
            "ci": list(found.ci), "containers": list(found.containers),
            "makefile": found.makefile, "readme": found.readme, "quickWins": list(found.quick_wins),
        },
    )


def append_block(path: Path, block: str, begin: str) -> bool:
    """Append `block` to the file at `path` once — created if absent; left alone if its marker is there."""
    existing = path.read_text() if path.is_file() else ""
    if begin in existing:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(existing.rstrip("\n") + ("\n" if existing else "") + block)
    return True


def adopt(root: Path, answers: Answers, found: Survey | None = None) -> Adopted:
    """Install the method around the repository at `root`, as one commit by the factory."""
    check_repository(root)
    found = survey(root) if found is None else found
    layout = Layout(answers.delivery)
    apps = answers.applications
    if not apps:
        raise GenerationError("no application to install the method around: adopt wraps at least one")
    adoption = with_recommendation(root, layout, with_platform(root, facts(found, answers, layout), apps), apps)
    files = project_files(answers.name, answers.profile, answers.target, apps, layout, adoption)
    executables = {layout.place(path) for path in executable_paths(answers.profile, apps)}
    clashing = [path for path in files if (root / path).exists()]
    if clashing:
        raise GenerationError(
            f"refusing to write over files this repository already has: {', '.join(clashing[:5])}"
            f"{' …' if len(clashing) > 5 else ''} — name another directory with --delivery"
        )
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, newline="")
        path.chmod(0o755 if relative in executables else 0o644)
    page = layout.under(SURVEY_PAGE)
    (root / page).parent.mkdir(parents=True, exist_ok=True)
    (root / page).write_text(survey_page(found, apps))
    view = layout.under(STRUCTURE_PAGE)
    found_shape = structure(root, apps, layout.delivery, FACTORY_IDENTITY["GIT_AUTHOR_EMAIL"])
    (root / view).write_text(structure_page(found_shape, adoption, layout))
    ledger = layout.under(PINNED)
    (root / ledger).write_text(PINNED_LEDGER)
    retirement = layout.under(RETIREMENT)
    (root / retirement).write_text(RETIREMENT_LEDGER)
    running = layout.under(RUNNING)
    (root / running).write_text(running_ledger(answers.name, apps))
    written = [*files, page, view, ledger, retirement, running]

    appended = []
    if append_block(root / AGENTS, agents_block(layout, VERSION), "<!-- extension:delivery:begin -->"):
        appended.append(AGENTS)
    ignored = layout.repoint(GITIGNORE, build_artifacts(answers.profile == "event-modelling", apps, answers.target))
    if append_block(root / GITIGNORE, gitignore_block(ignored, layout), "# slipwai:delivery:begin"):
        appended.append(GITIGNORE)
    settings_written = not (root / SETTINGS).exists()
    if settings_written:
        (root / SETTINGS).parent.mkdir(parents=True, exist_ok=True)
        (root / SETTINGS).write_text(claude_settings(apps, answers.target, layout))
        written.append(SETTINGS)
    # No root Makefile means nothing of theirs to clash with, so `make verify` can be one word from day one.
    # Where there is one, its targets are theirs and the include is a person's edit — see `report`.
    makefile_written = not found.makefile and append_block(
        root / MAKEFILE, makefile_block(layout), "# slipwai:delivery:begin"
    )
    if makefile_written:
        appended.append(MAKEFILE)
    wrappers = write_wrappers(root, wrapped_of(apps))
    theirs = [path for paths in wrappers.values() for path in paths]

    subprocess.run(["git", "add", "--", *written, *appended, *theirs], cwd=root, check=True)
    subprocess.run(
        ["git", *NO_MAINTENANCE, "commit", "-q", "-m",
         f"Adopt the delivery method for {answers.name} with slipwai {VERSION}"],
        cwd=root, check=True, env=FACTORY_IDENTITY,
    )
    return Adopted(
        root, answers.name, layout, apps, adoption, written, appended, settings_written, makefile_written, wrappers
    )


def manifest_of(root: Path) -> dict:
    return json.loads((root / "project.json").read_text())


__all__ = ["Adopted", "Answers", "WRITTEN", "adopt", "manifest_of", "proposed", "report"]
