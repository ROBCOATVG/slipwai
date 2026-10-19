"""`.gitignore`: what this project's toolchain writes, and the data it must never commit."""
from __future__ import annotations

import json

from ..assets import NOTES, TOOLKIT_ROOT
from ..catalog import CATALOG
from ..extensions import known_extensions
from ..npm_workspace import npm
from ..registry import GITIGNORE, registry
from ..services import App, backends_of, families_of, needs_environment, services_of, web_apps
from ..targets import managed
from .openapi import API_CLIENT
from .shared_packages import PACKAGES, node_workspace

#: Under `.slipwai/`, what is the run's and not the record's. Ignored, in the order a reader meets them.
#: `catch-up/` holds the archived catch-up pages: each migration moves the last one there rather than
#: overwriting it, and like the page itself it is this machine's working note, not trunk's history.
#: `preflight.json` is what preflight writes before a stage, and `logs.unread-*/` is where a slice's berth
#: keeps lines a session wrote before the berth was linked to the shared deck log; left out, both are
#: untracked files in every berth, and `check-slice-scope` failed every slice run abreast on them.
RUN_STATE = ("logs/", "run-state.json", "running/", "harbourmaster.json", "berths/", "intake-cleanup.json",
             "catch-up/", "preflight.json", "logs.unread-*/")

# What each store writes beside the code, keyed by feature, for a store that keeps its data in the working
# tree. A SQLite event store writes its log next to the code, and WAL mode writes two more files beside it.
# An event log is the one thing in a project that must never be committed: it is data, it is often
# personal, and a merge of two histories is not a history. A store with a container writes nothing here.
STORE_ARTIFACTS = {
    "sqlite": "*.sqlite3\n*.sqlite3-wal\n*.sqlite3-shm\n",
}
# The five slice-scoped artifacts the installed Spec Kit commands write at the feature root.
CANONICAL_SLOTS = ("plan.md", "research.md", "data-model.md", "quickstart.md", "tasks.md")


# Every directory an agent harness's projection lands in (`scripts/agents/registry.json`), read once. The projections
# are derived files — the canonical `skills/`, `commands/` and `agents/` again, with a stamp — written by `./init`,
# `make agents` and `slipwai migrate`, and `check-agents` reads an absent one as a clone nobody has run `./init` in
# yet. Committing them put the whole skill catalogue, thirty thousand lines, into every repository twice; nothing read the
# copy that the canonical file did not say.
REGISTRY = TOOLKIT_ROOT / "scripts/agents/registry.json"


def harness_directories(entry: dict) -> list[str]:
    """Every directory this harness's projections land in: its skills, its commands and its agent types."""
    named = [entry.get(key) for key in ("skillsDir", "commandsDir")]
    if isinstance(entry.get("agentFile"), dict):
        named.append(entry["agentFile"].get("dir"))
    return [value for value in named if isinstance(value, str) and not value.startswith(("~", "/"))]


def projection_artifacts() -> str:
    """One ignored line per harness directory inside the repository, once each, in registry order."""
    harnesses = json.loads(REGISTRY.read_text(encoding="utf-8"))["harnesses"]
    directories = [directory for entry in harnesses for directory in harness_directories(entry)]
    return "".join(f"{directory.rstrip('/')}/\n" for directory in dict.fromkeys(directories))


def build_artifacts(event: bool, apps: list[App], target: str = "none") -> str:
    """Every backend's artifacts once each, then the frontend's, the event profile's, the selection's and the
    production target's."""
    # What each backend's toolchain writes beside the code: its `gitignore` answer, once each.
    answer = registry().answer
    language_artifacts = "".join(dict.fromkeys(answer(backend, GITIGNORE) for backend in backends_of(apps)))
    frontend_artifacts = "".join(f"{web.path}/dist/\n" for web in web_apps(apps))
    # Of the family, not the backend: a TypeScript service behind any framework already ignores
    # node_modules for its own sake, and a second copy of the line is not the answer for either.
    if web_apps(apps) and not any(npm(family) for family in families_of(apps)):
        frontend_artifacts = "node_modules/\n" + frontend_artifacts
    # Rendered Mermaid artifacts are CI-owned: the pages workflow regenerates them on every model change,
    # and nothing browser-free can prove a committed copy is current, so none is committed. The draw.io
    # canvas beside them, `docs/event-model/model.drawio`, is the one rendering that *is* committed — it
    # needs no browser, and `check-drawio` proves it current inside `verify` — so it is not listed here.
    event_artifacts = (
        "scripts/event-model/node_modules/\n"
        "scripts/event-model/.mermaid-cli/\n"
        "docs/event-model/model.mmd\n"
        "docs/event-model/model.svg\n"
        "docs/event-model/model.png\n"
        "docs/event-model/model.html\n"
        "docs/event-model/slices/\n"
        "docs/event-model/segments/\n"
        if event
        else ""
    )
    # What `make build-packages` writes, on the same reasoning as `.env` below: an ignored path that nothing
    # has created yet costs nothing, and the alternative is the first `packages/<name>` somebody adds
    # arriving with its `dist/` committed — a build output in the history, which is how a stale one comes to
    # look like a current one. `dist/` because that is the convention the browser app beside it already uses.
    shared_package_artifacts = f"{PACKAGES}/*/dist/\n" if node_workspace(apps) else ""
    # And the typed client's generated types, on the same reasoning: `make build-packages` writes them from
    # the service's published document, so a committed copy is one that can disagree with the contract
    # while looking authoritative — and a generated file in the tree is a file somebody edits.
    if node_workspace(apps):
        shared_package_artifacts += f"{API_CLIENT}/src/schema.ts\n"
    # `.env` holds the local values copied out of `.env.example`, including a database URL with a password
    # in it. Ignored whether or not the services survive a later prune: an ignored path that no longer
    # exists costs nothing, and an un-ignored one that does is a committed credential.
    environment_artifacts = ".env\n" if needs_environment(apps) else ""
    store_artifacts = "".join(
        dict.fromkeys(
            STORE_ARTIFACTS.get(service.selection.feature_of("persistence") or "", "")
            for service in services_of(apps)
        )
    )
    # What `make push` and `make deploy` write locally, and what `tofu init` keeps beside each stack. The
    # bootstrap stack's state is deliberately *not* here: it is committed, encrypted, on purpose.
    production_artifacts = (
        ".build/\ninfra/**/.terraform/\ninfra/**/*.tfplan\ninfra/**/terraform.tfstate.backup\n"
        if managed(CATALOG, target)
        else ""
    )
    # Every extension's local state, whether or not `./init --extension <key>` was ever run: an ignored
    # path that does not exist yet costs nothing, same reasoning as `.env` above, and it means adopting an
    # extension later never needs a second edit to `.gitignore`.
    extension_artifacts = "".join(
        extension.get("ignore", "") for extension in known_extensions(CATALOG).values()
    )
    return (
        language_artifacts
        + frontend_artifacts
        + shared_package_artifacts
        + event_artifacts
        + environment_artifacts
        + store_artifacts
        + production_artifacts
        + extension_artifacts
        # What a factory command leaves for this project to act on and then throw away.
        + f"{NOTES}\n"
        # The run's own state, which is not a record of it. Heartbeat and token lines arrive every few
        # seconds; the pid files and the harbourmaster's cursor are about one machine; `run-state.json` is
        # a fold of the logs and `berths/` is worktree paths and port numbers. None of it belongs in
        # trunk's history, and `logs.py` has said so since 5.13 while nothing ignored them.
        #
        # Four things under `.slipwai/` stay committed, and each for a reason: `extensions.json` is the
        # election record `migrate` re-projects from without asking the menu again; `hooks.json` is a
        # controlled file, so an iteration that edits it is refused like one that edits a gate — which
        # needs it diffable; `packages/` is a project's own pinned packages where it has any; and
        # `dispatch/` is the dispatch ledger, one file per feature, which `check-dispatch` and the
        # `pre-push` hook read on a checkout that has only what git carries.
        + "".join(f".slipwai/{name}\n" for name in RUN_STATE)
        + ".specify-tools/\n.delivery-tools/\n"
        # The canonical slot the installed Spec Kit plan and tasks commands resolve to, one per feature. Since
        # 1.15.0 it is a link into `specs/<feature>/slices/<id>/`, where a slice's record lives from the day it
        # is planned, so two slices of one feature never overwrite each other's plan. The link is local
        # scaffolding — committed, it would point somewhere different on every slice branch and conflict at
        # every merge — and `check-slice-scope` refuses a regular file left where the link was.
        + "".join(f"specs/*/{slot}\n" for slot in CANONICAL_SLOTS)
        # The runner's files were ignored here until 7.7d: a checkpoint, a stop file, a pid, a feed, a raw
        # stream, a watch cursor, a kept last message and two inbox files. Every one of them was state held
        # outside the logs by the single process that held the run, and all nine went with it. Nothing has
        # replaced them, which is the point: a captain's state is its deck log, and that is committed.
        # The agent projections: derived from `skills/`, `commands/` and `agents/`, rewritten by `./init`, `make agents` and
        # `slipwai migrate`, and never the place to edit — so never committed, whichever harness the project uses.
        + projection_artifacts()
    )
