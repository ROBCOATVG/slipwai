"""The selected adapters and the files that configure them.

Split in two by where the files land: `backing_service_files` owns the repository root — Compose, the
environment template, the prune script, the Keycloak realms — and `backing_service_service_files` owns
`apps/service`, the ports and adapters themselves with the contract suites that keep them honest.

The prose that explains all of it — the README sections and what each gate proves — is
`backing_service_prose.py`, split out when this module outgrew its budget.
"""
from __future__ import annotations

from ..assets import BACKING_SERVICE_ROOT
from ..selection import Selection
from ..services import (
    App,
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
from .service_layouts import SERVICE_FILES

# The repository-root files a feature owns, keyed by feature: destination in the generated project to
# source under assets/backing-services/. The root-level counterpart of `SERVICE_FILES`, and the reason the
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

    Every marked file is emitted whole and cut down afterwards by `PRUNER.prune`, so the selection is
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
            .read_text()
            .replace("__APP_SERVICES__\n", app_services(apps))
        )
    if not features_of(apps):
        return files
    # Only a selection that still has a choice in it carries the pruner. A project on the in-memory store
    # with no transport and no identity provider has nothing left to answer, and shipping it a script whose
    # every axis is settled is shipping a dead end.
    if prunable_features_of(apps):
        files["scripts/backing-services.py"] = (BACKING_SERVICE_ROOT / "prune.py").read_text()
    if needs_environment(apps):
        environment = (BACKING_SERVICE_ROOT / "env.example").read_text()
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
                (BACKING_SERVICE_ROOT / source).read_text(), first, web[0] if web else None
            )
    return files


def backing_service_service_files(selection: Selection, backend: str) -> dict[str, str]:
    """The service half of the selection, keyed relative to the service: the ports, every adapter behind
    them, the contract suites that run against all of them, and the migrations.

    The in-memory adapter arrives with every event-store answer rather than only the bare one, on purpose:
    it is what the shared contract runs against in `make verify`, and a fake with no real adapter to be
    checked against has nothing to keep it honest.
    """
    root = BACKING_SERVICE_ROOT / backend
    layout = SERVICE_FILES[backend]
    files: dict[str, str] = {}
    for feature, mapping in layout.items():
        if not selection.has(feature):
            continue
        for destination, source in mapping.items():
            files[destination] = (root / source).read_text()
    return files
