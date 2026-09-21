"""Turning one set of answers into a repository on disk.

The whole of a generated project is assembled here as a path-to-content map and written in one pass, so
there is exactly one place that knows what a project is made of — and the order two contributors disagree
in is stated rather than emergent: `apps/web` owns the npm workspace when there is a frontend, so the
frontend's manifests are written over the backend's.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .assets import ADOPTION_ROOT, PRUNER
from .catalog import CATALOG
from .layout import AT_ROOT, Layout
from .origin import Adoption
from .project.adopted import adopted_files, adoption_page
from .project.agent_settings import claude_settings
from .project.agents import agent_files
from .project.backing_services import backing_service_files
from .project.biome import biome_files
from .project.ci_workflows import workflow
from .project.commands import command_files
from .project.constitution_journey import journey_template
from .project.convergence_page import convergence_page
from .project.deploy_workflow import deploy_workflow, promotion_workflow, rollback_workflow
from .project.docs import documentation_files
from .project.docs_index import docs_index
from .project.drive_settings import drive_config
from .project.event_model import event_model_workflow
from .project.existing import existing_deployment_page
from .project.frontend import frontend_files
from .project.gitignore import build_artifacts
from .project.ground_command import ground_command_files
from .project.guidance import agent_guidance, architecture
from .project.infra import target_files
from .project.init_script import init_script
from .project.languages import language_files
from .project.makefile import makefile
from .project.metadata import metadata
from .project.pin_commands import pin_command_files
from .project.pins import pin_files
from .project.readme import readme
from .project.renovate import renovate_config
from .project.repository import repository_files
from .project.run_skill import run_skill
from .project.shared_packages import PACKAGES
from .project.stage_models import stage_models
from .project.strangle_command import strangle_files
from .services import App, prunable_features_of, services_of, web_apps, wrapped_of
from .targets import managed
from .toolkit import executable_paths, own_paths, toolkit_files_from_assets

# `git commit` flags that keep it from starting a detached maintenance process — see `commit_all`.
NO_MAINTENANCE = ("-c", "maintenance.auto=false", "-c", "gc.auto=0")
# Who a commit the factory makes is by: the factory, so a project's history says which commits were its own —
# the scaffold, and every replay merged since. `replay` reads the newest of them back as its merge base.
FACTORY_EMAIL = "factory@local"
FACTORY_IDENTITY = os.environ | {
    "GIT_AUTHOR_NAME": "Slipwai",
    "GIT_AUTHOR_EMAIL": FACTORY_EMAIL,
    "GIT_COMMITTER_NAME": "Slipwai",
    "GIT_COMMITTER_EMAIL": FACTORY_EMAIL,
}


def project_files(
    project_name: str, profile: str, target: str, apps: list[App], layout: Layout = AT_ROOT,
    adoption: Adoption | None = None,
) -> dict[str, str]:
    """Every file a generated project starts with, keyed by its path in the new repository.

    `apps` is the list of applications the project has — each service with its own language, framework and
    selection, and each browser app with the service it proxies to. Every part that names an application
    takes the list; a part that has to speak in one language (the first slice's paths) speaks the first
    service's, and the skills' example snippets speak every language a service is written in, one labelled
    block per language. `add-service` and `add-frontend` call this with one more application
    on the list and write what changed, which is how a later one gets exactly the files the first did.

    The target reaches the parts that have something to say about it — `project.json`, which records it; the
    Makefile, `.gitignore`, the README, `AGENTS.md`, the docs and the agent settings, which gain a production
    section under a real one; `infra.py` and `deploy_workflow.py`, which contribute nothing under `none`; and
    each backend, which gives a service a flag reader only where there is somewhere to deploy (`flags.py`).
    Every other part is the same file whatever the destination.

    `layout` is where the factory's own material lives in the repository: everything is assembled for the
    root, as every generated project has it, and placed and re-pointed as the last step where `project.json`
    says the delivery material lives elsewhere (`layout.py`). `adoption` says the method was installed around a
    repository that already existed: `project.json` records it, `docs/adoption.md` explains it, and the set is
    cut to what such a repository takes from the factory (`project/adopted.py`). An application on `apps` that
    the factory did not make (`generated: false`) is recorded and otherwise nothing any part here names —
    `services_of` and `web_apps` mean the generated ones.
    """
    event = profile == "event-modelling"
    generated = {
        "README.md": readme(project_name, profile, apps, target),
        "project.json": metadata(project_name, profile, target, apps, layout, adoption),
        "init": init_script(apps, target, layout),
        ".gitignore": build_artifacts(event, apps, target),
        "renovate.json": renovate_config(apps),
        "Makefile": makefile(project_name, profile, apps, target, layout),
        "AGENTS.md": agent_guidance(profile, apps, target),
        ".claude/settings.json": claude_settings(apps, target),
        ".specify/models.json": stage_models(),
        ".specify/drive.json": drive_config(),
        ".github/workflows/verify.yml": workflow(apps, layout),
        "docs/architecture.md": architecture(profile, apps),
        f"{PACKAGES}/.gitkeep": "",
        "skills/run-the-app/SKILL.md": run_skill(project_name, apps, layout),
    }
    if event:
        generated[".github/workflows/event-model.yml"] = event_model_workflow(layout.make)
    if adoption is not None:
        generated["docs/adoption.md"] = adoption_page(project_name, apps, adoption, layout)
        generated["docs/convergence.md"] = convergence_page(
            project_name, adoption.convergence, layout, adoption.converged
        )
        # The constitution template, adapted to where this repository stands: a principle the map says is not
        # yet reachable is written as a target, held to the map, rather than a fiction the gate then defends.
        generated[f".specify/presets/{profile}/templates/constitution-template.md"] = journey_template(
            profile, adoption.convergence
        )
        generated.update(pin_command_files(apps, layout, event))
        generated.update(ground_command_files(apps, layout, adoption))
        generated.update(strangle_files(apps, layout, target, adoption))
    if target == "existing":
        generated["docs/deployment.md"] = existing_deployment_page(project_name, adoption)
    if wrapped_of(apps):
        # The ratchet, only where there is code that was written before the gate that now judges it.
        generated["scripts/ratchet.py"] = (ADOPTION_ROOT / "scripts/ratchet.py").read_text()
        generated["scripts/check-convergence.py"] = (ADOPTION_ROOT / "scripts/check-convergence.py").read_text()
    if managed(CATALOG, target):
        # The one answer whose credential the cloud did not issue, so the one the workflows carry extra.
        auth0 = any(
            app.selection.option(axis) == "auth0"
            for app in services_of(apps)
            for axis in ("auth", "users")
        )
        generated[".github/workflows/deploy.yml"] = deploy_workflow(apps, target, auth0)
        generated[".github/workflows/production.yml"] = promotion_workflow(bool(web_apps(apps)), target, auth0)
        generated[".github/workflows/rollback.yml"] = rollback_workflow(target, auth0)
    generated.update(pin_files(apps))
    generated.update(repository_files(project_name, profile, apps, target))
    generated.update(agent_files(layout))
    generated.update(biome_files(apps))
    generated.update(command_files(event, apps, target, layout, adoption))
    generated.update(documentation_files(project_name, profile, apps, target))
    generated.update(backing_service_files(apps))
    generated.update(target_files(project_name, profile, target, apps))
    # The copied assets first, so that anything generated above wins where both have an opinion. What a
    # copied asset means by `apps/service` and `apps/web` is spelled for this project on the way in.
    files = toolkit_files_from_assets(profile, apps)
    files.update(generated)
    files.update(own_paths(language_files(project_name, event, apps, target), apps))
    # Last, because the frontend owns the npm workspace whenever there is one: its `package.json` and
    # lockfile describe every Node deployable, and each backend's describe only itself.
    files.update(frontend_files(project_name, apps, target))
    # The docs index last of all, over everything above, so it lists exactly the pages this project ships.
    files["docs/README.md"] = docs_index(files)
    files = layout.relocate(files, persons_words(apps, adoption))
    return adopted_files(files, apps, layout, adoption) if adoption is not None else files


def persons_words(apps: list[App], adoption: Adoption | None) -> tuple[str, ...]:
    """The strings in an adopted repository's record that are somebody's words and not the factory's pointers — a
    recorded command, a row's evidence, a quick win's place, the release and CI evidence — which `Layout.relocate`
    leaves exactly as written wherever a page, the Makefile or `project.json` repeats them."""
    if adoption is None:
        return ()
    words: list[str] = [
        command for app in apps if not app.generated for command in (app.commands or {}).values() if command
    ]
    words += [str(row.get("evidence")) for row in adoption.convergence or []
              if isinstance(row, dict) and row.get("evidence")]
    words += [str(win.get(key)) for win in (adoption.survey or {}).get("quickWins") or []
              for key in ("where", "what", "fix") if win.get(key)]
    words += [str(e) for e in (adoption.release or {}).get("evidence") or []]
    if (adoption.ci or {}).get("evidence"):
        words.append(str(adoption.ci["evidence"]))
    return tuple(words)


def write_project(
    destination: Path,
    project_name: str,
    profile: str,
    target: str,
    apps: list[App],
    *,
    files: dict[str, str] | None = None,
    keep: set[str] | None = None,
    settled: set[str] | None = None,
    layout: Layout = AT_ROOT,
    adoption: Adoption | None = None,
) -> None:
    """Write the project and commit it, once, as the repository it starts life as.

    `generate` passes the answers alone. `replay` passes what it has already assembled from them — `files`,
    with the provenance the manifest carried put back — and cuts the result down to `keep`, the features the
    project it replays still has on disk, with `settled` the ones whose markers that project has already
    shed. Left unsaid, a project keeps every feature its answers selected and stays open to choose again.
    `layout` is the one `files` was assembled for.
    """
    files = project_files(project_name, profile, target, apps, layout, adoption) if files is None else files
    executables = {layout.place(path) for path in executable_paths(profile, apps)}
    destination.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        # `newline=""` writes the string's own line endings rather than translating them, which is the
        # other half of `asset_tree`'s faithful read. Only `mvnw.cmd` depends on it today, but the pair is
        # what makes "an asset arrives as committed" true of the bytes and not just of the characters.
        path.write_text(content, newline="")
        desired_mode = 0o755 if relative in executables else 0o644
        path.chmod(desired_mode)
    prunable = set(prunable_features_of(apps)) if keep is None else keep
    # Marked regions are written whole above and cut down here, so "which features this project has" is
    # decided in exactly one place — the same code the project itself runs from `./init`. The markers
    # survive, which is what lets that later prune find them.
    #
    # Unconditionally, including when the set to keep is empty. Skipping the prune because there was
    # nothing left to keep is how a project on the in-memory store with no transport and no identity
    # provider ended up with every marked region of `application.properties` intact — a Postgres
    # datasource, a SQLite path and two Keycloak tenants configured in a service that has none of them.
    # An empty keep set is an answer, not a missing one.
    PRUNER.prune(destination, prunable, settled=settled, log=lambda _message: None)
    commit_all(destination, f"Scaffold {project_name}")


def commit_all(repository: Path, message: str) -> None:
    """Make `repository` a Git repository on `main` with everything in it as one commit."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repository, check=True)
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    # No auto-maintenance: `git commit` would otherwise launch a detached `git maintenance run --auto`, which
    # takes its lock inside .git/objects/ after this returns — and a caller that deletes the repository next
    # (every factory test) finds the directory not empty. There is nothing to maintain in a first commit.
    subprocess.run(
        ["git", *NO_MAINTENANCE, "commit", "-q", "-m", message], cwd=repository, check=True, env=FACTORY_IDENTITY
    )
