"""The selected adapters and the files that configure them.

Split in two by where the files land: `backing_service_files` owns the repository root — Compose, the
environment template, the prune script, the Keycloak realms — and `backing_service_service_files` owns
`apps/service`, the ports and adapters themselves with the contract suites that keep them honest.

The prose that explains all of it — the README sections and what each gate proves — is
`backing_service_prose.py`, which answers what a selection *says* where this module writes what it *is* — a different question from different callers.
"""
from __future__ import annotations

import posixpath

from ..assets import BACKING_SERVICE_ROOT, located, source_text
from ..registry import READ_SIDE_FILES, WRITE_SIDE_FILES, registry
from ..rungs import EVENTS, Layout, merged_layout, rung_rows
from ..selection import Selection
from ..services import (
    App,
    families_of,
    features_of,
    first_transport,
    has_feature,
    needs_environment,
    prunable_features_of,
    services_of,
    web_apps,
)
from ..toolkit import spoken_for
from .compose import app_services, composed
from .pruner import emitted

# The repository-root files a feature owns, keyed by feature: destination in the generated project to
# source under assets/backing-services/. The root-level counterpart of a backend's `write_side_files`, and the reason the
# realm import needs no branch — a second identity provider is a row here.
ROOT_FILES = {
    "keycloak": {"docker/keycloak/realms/app.json": "keycloak/realms/app.json"},
    "users-keycloak": {"docker/keycloak/realms/customers.json": "keycloak/realms/customers.json"},
}

# Root files several features share, keyed the way a shared marked region is named: the one Keycloak
# container is described once, a marked section per realm, and the pruner cuts the sections the same way
# it cuts every other marked file and deletes the file with the last realm (`SHARED_FILES` in prune.py).
SHARED_ROOT_FILES = {
    "keycloak|users-keycloak": {"docker/keycloak/README.md": "keycloak/README.md"},
}


def backing_service_files(apps: list[App]) -> dict[str, str]:
    """The repository-root half of the services' selections: Compose, the environment template, the prune
    script and the Keycloak realm — the union of what every service needs.

    Every marked file is emitted whole and cut down afterwards by the keel's `pruner()`, so the selection is
    applied in exactly one place. That prune leaves the markers behind, which is what lets the generated
    project's own `./init` prune further later.
    """
    files: dict[str, str] = {}
    # Compose before the early return below: a project with no backing service at all still has an app to
    # run, and `make demo` is how it is shown. The file is emitted when there is anything to put in it —
    # a container, a service, or the browser app — rather than when a container happens to be needed.
    if composed(apps):
        files["docker-compose.yml"] = (
            (BACKING_SERVICE_ROOT / "docker-compose.yml")
            .read_text(encoding="utf-8")
            .replace("__APP_SERVICES__\n", app_services(apps))
        )
    if not features_of(apps):
        return files
    # Only a selection that still has a choice in it carries the pruner. A project on the in-memory store
    # with no transport and no identity provider has nothing left to answer, and shipping it a script whose
    # every axis is settled is shipping a dead end.
    if prunable_features_of(apps):
        # The keel's one implementation, carrying the rows of this project's languages and no other's.
        files["scripts/backing-services.py"] = emitted(families_of(apps))
    if needs_environment(apps):
        environment = (BACKING_SERVICE_ROOT / "env.example").read_text(encoding="utf-8")
        # One block, marked with the first service's transport, rather than one per framework: the two
        # keys are the first service's — `PORT` is its port — and three near-identical marked regions is
        # three places to forget one.
        environment = environment.replace("__TRANSPORT__", first_transport(apps) or "none")
        # A flag has one spelling and one value, and the browser app is why it is worth saying: it asks
        # the service for it rather than carrying its own copy. Appended rather than marked, because it
        # belongs to the browser app existing and not to any backing-service answer.
        browser = web_apps(apps)
        if browser:
            environment += f"""#
# Feature flags. One product flag, one name, one value, and only the service reads this file: it takes
# `FLAG_CHECKOUT_V2` from here, and {browser[0].path} asks it over `GET /api/flags` — so setting it once
# below moves both halves, and the browser needs no variable of its own. Only `on` is on
# ({browser[0].path}/src/flags.ts is that side of it). Nothing is declared until code reads it:
#
# FLAG_CHECKOUT_V2=off
"""
        files[".env.example"] = environment
    # Repository-level copies speak of the first service and the first browser app, as the toolkit does.
    first, web = services_of(apps)[0], web_apps(apps)
    shared = {
        group: mapping
        for group, mapping in SHARED_ROOT_FILES.items()
        if any(has_feature(apps, feature) for feature in group.split("|"))
    }
    for feature, mapping in {**ROOT_FILES, **shared}.items():
        if feature in ROOT_FILES and not has_feature(apps, feature):
            continue
        for destination, source in mapping.items():
            files[destination] = spoken_for(
                (BACKING_SERVICE_ROOT / source).read_text(encoding="utf-8"), first, web[0] if web else None
            )
    return files


def service_layout(backend: str, write_model: str = EVENTS) -> Layout:
    """Every file a feature owns under a service on this rung: the backend's `write_side_files` and
    `read_side_files`, each read at the rung, merged."""
    answer = registry().answer
    return merged_layout(rung_rows(answer(backend, WRITE_SIDE_FILES), write_model),
                         rung_rows(answer(backend, READ_SIDE_FILES), write_model))


def backing_service_service_files(selection: Selection, backend: str) -> dict[str, str]:
    """The service half of the selection, keyed relative to the service: the ports, every adapter behind
    them, the contract suites that run against all of them, and the migrations.

    The in-memory adapter arrives with every persistence answer rather than only the bare one, on purpose:
    it is what the shared contract runs against in `make verify`, and a fake with no real adapter to be
    checked against has nothing to keep it honest.

    Which set, out of the two a backend declares, is the service's rung: `write-model: events` is given the
    log and the adapters behind it, `state` the repository port and the versioned table. The feature is the
    same either way — the persistence axis chose the store — so the question the rung settles is what the
    store is asked to hold, not which store it is.
    """
    roots = registry().sources(backend)  # its own, then its family's: a framework reads the family's files
    layout = service_layout(backend, selection.write_model)
    files: dict[str, str] = {}
    for feature, mapping in layout.items():
        if not selection.has(feature):
            continue
        for destination, source in mapping.items():
            relative = f"backing-services/{backend}/{source}"
            held = located(roots, relative)
            root = roots[0] if held is None else held[0]
            files[destination] = source_text(root / "assets", posixpath.normpath(relative), root)
    return files
