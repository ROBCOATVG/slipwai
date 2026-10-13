"""The browser apps under `apps/`, and the npm workspace that holds them beside the Node services."""
from __future__ import annotations

import json
from pathlib import Path

from ..assets import PRUNER, asset_tree
from ..backends import WEB_PORT
from ..catalog import CATALOG
from ..errors import GenerationError
from ..npm_workspace import BrowserApp, frontend, held_lock, npm, workspace
from ..probes import HEALTH_PATH
from ..services import App, features_of, frontend_of, prunable_features_of, services_of, web_apps
from ..targets import managed
from ..tooling import package_name
from .openapi import API_CLIENT, API_CLIENT_NAME, api_client_package, document_of
from .shared_packages import WORKSPACE, workspace_manifest, workspace_scripts

# What a feature adds to every browser app, keyed by feature: a directory inside the frontend's own material,
# laid out like the app and copied in whole. The browser-app counterpart of a backend's `write_side_files`, and
# the reason the external login needs no branch — a second provider is a row here. Kept in step with
# `OWNED_FILES_PER_WEB_APP` in assets/backing-services/prune.py, which removes them again. The paths are
# relative to the frontend, never to the keel: which directory that is is the frontend's to say
# (`npm_workspace.BrowserApp`), so that the same feature row reads whether the material ships in a language
# package or, as `react-vite` still does, in the keel.
WEB_FEATURE_FILES: dict[str, str] = {
    "users-keycloak": "features/users-keycloak",
}

# What a feature adds to a *browser app's* manifest — the external login's OIDC client. Keyed by feature, and kept in
# step with `WEB_PACKAGE_EDITS` in assets/backing-services/prune.py the same way. A browser app gets a feature's
# dependencies when any service in the project has the feature, because that is when the pruner would keep them.
WEB_PACKAGE_ADDITIONS: dict[str, dict[str, str]] = {
    "users-keycloak": {"oidc-client-ts": "3.5.0", "react-oidc-context": "3.3.1"},
}
# The only features that add an npm dependency to a browser app, and so the part of a workspace lock's name that is
# the browser app's: a lock is committed per dependency set, because `npm ci` refuses one that disagrees with its
# manifest. `scripts/regenerate-locks.py` builds each from the same manifests the generator emits.
WEB_LOCK_FEATURES = tuple(WEB_PACKAGE_ADDITIONS)


def web_package_json(source: str, features: set[str]) -> str:
    """The browser app's manifest with the dependencies its project's features need, from `WEB_PACKAGE_ADDITIONS`."""
    package = json.loads(source)
    dependencies = dict(package.get("dependencies", {}))
    for feature, additions in WEB_PACKAGE_ADDITIONS.items():
        if feature in features:
            dependencies.update(additions)
    package["dependencies"] = dict(sorted(dependencies.items()))
    return json.dumps(package, indent=2) + "\n"


def web_lock_suffix(features: set[str]) -> str:
    """The part of a workspace lock's name that is the browser app's: '' or '-users-keycloak'."""
    return "".join(f"-{feature}" for feature in WEB_LOCK_FEATURES if feature in features)


def web_files(project_name: str, web: App, apps: list[App], target: str, found: BrowserApp) -> dict[str, str]:
    """One browser app's files from the committed skeleton, named and addressed for itself.

    `found` is where that skeleton is: the frontend `--frontend <name>` named, as the family that writes it —
    or, for the one the keel still carries, the keel — hands it over. Nothing here spells a directory under
    `assets/`, so the material can move without this function changing.

    The skeleton is written for the first browser app on 5173 talking to a service on 3000; a later one is
    given its own dev-server port and the address of the service it proxies to, and the proxy sits in that
    service's transport's marked region. Every other marked region is a feature some service has — the
    external login — and the files a feature adds arrive with it.

    The regions are cut here as well as by the project-wide prune that follows, with the same `keep`, because
    that prune does not run for a project with nothing prunable — and a web app whose service has no transport
    is exactly such a project. `__TRANSPORT__` becomes `none` where there is nothing to proxy to: a name no
    feature has, so the region goes.
    """
    api = web.api_service(apps)
    features = set(features_of(apps))
    keep = set(prunable_features_of(apps))
    # What the app's one route asks for, and where the typed client that asks comes from. The path is the
    # project's own product surface where it has one — a flag route is under `/api`, which the dev server
    # forwards and a deployment routes — and the probe otherwise, which is the only path a project with
    # nowhere to deploy publishes at all.
    status_path = "/api/flags" if managed(CATALOG, target) else HEALTH_PATH
    files: dict[str, str] = {}
    for relative, content in asset_tree(found.at("app")).items():
        if relative == "package.json":
            package = json.loads(web_package_json(content, features))
            package["name"] = package_name(project_name, web)
            content = json.dumps(package, indent=2) + "\n"
        elif relative == "index.html":
            content = content.replace("<title>Product</title>", f"<title>{project_name}</title>")
        elif relative == "vite.config.ts":
            content = content.replace(f"port: {WEB_PORT},", f"port: {web.port},")
            transport = api.transport if api is not None else None
            content = content.replace("__TRANSPORT__", transport or "none")
            if api is not None:
                content = content.replace("'http://localhost:3000'", f"'http://localhost:{api.port}'")
        elif relative in ("src/App.tsx", "tests/App.test.tsx"):
            content = spoken_for_app(content, project_name, api, status_path)
        if PRUNER.MARKER.search(content):
            content = PRUNER.strip_markers(content, keep, set())
        files[f"{web.path}/{relative}"] = content
    # The flag reader, in the one shape this project can actually use. With somewhere to deploy the flag
    # lives in an environment and the service enforcing it answers for it, so the bundle asks over
    # `GET /api/flags`; with nowhere to deploy there is no environment and no reader on the service, so the
    # value comes from `.env` through the bundle — which is still the only way to hide a half-built screen.
    # Both export the same things, so `main.tsx` and every slice are identical either way.
    variant = "app-flags-target" if managed(CATALOG, target) else "app-flags-local"
    for relative, destination in (("flags.ts", "src/flags.ts"), ("flags.test.ts", "tests/flags.test.ts")):
        content = found.at(f"{variant}/{relative}").read_text(encoding="utf-8")
        files[f"{web.path}/{destination}"] = content
    # The one route, in the shape this project can actually write it. A service that publishes an API
    # document gets a client generated from it and calls through that; one whose framework publishes
    # nothing — both Java backends today — fetches by hand and says so on the page, because a type
    # asserting fields nothing promised is worse than no type at all. Not emitted at all with no API:
    # a marked region cut from a file leaves an empty file rather than no file, and the project-wide
    # prune that would delete it does not run for a project with nothing prunable.
    if api is not None:
        variant = "app-route-client" if document_of(api) is not None else "app-route-plain"
        for relative, destination in (
            ("Home.tsx", "src/routes/Home.tsx"),
            ("Home.test.tsx", "tests/routes/Home.test.tsx"),
        ):
            content = found.at(f"{variant}/{relative}").read_text(encoding="utf-8")
            files[f"{web.path}/{destination}"] = spoken_for_app(content, project_name, api, status_path)
    for feature, source in WEB_FEATURE_FILES.items():
        if feature not in features:
            continue
        for relative, content in asset_tree(found.at(source)).items():
            files[f"{web.path}/{relative}"] = content
    return files


def member_lock(service: App) -> Path:
    """A workspace member service's own committed lock, as its language answers for its selection."""
    return held_lock(service.language, "member_lock", workspace(service.language).member_lock(service.selection))


def spoken_for_app(content: str, project_name: str, api: App | None, status_path: str) -> str:
    """The browser app's tokens, resolved: its project's name, its API's transport, and the one path it
    calls. `__TRANSPORT__` becomes `none` where there is nothing to call — a name no feature has, so the
    marked region goes — and the client's package name is only ever written where there is a client."""
    return (
        content.replace("__TRANSPORT__", (api.transport if api is not None else None) or "none")
        .replace("__PROJECT_NAME__", project_name)
        .replace("__STATUS_PATH__", status_path)
        .replace("__API_CLIENT__", api_client_package(project_name))
    )


def api_client_files(project_name: str, apps: list[App], found: BrowserApp) -> dict[str, str]:
    """`packages/api-client`: the typed client, generated from the document its service publishes.

    `found` is the browser app that calls through it, because the client is written in that browser app's
    language and shipped beside it: the package that moves the one moves the other.

    Only where there is a document to generate from. A project answering `--http none` has no contract, so
    it gets no client rather than a package whose build points at a file that was never written — and the
    browser app's one route, which is what uses it, sits inside the same transport's marked region.

    `src/schema.ts` is deliberately not emitted: it is a build output, `make build-packages` writes it, and
    `.gitignore` refuses it. A committed generated file is a file somebody edits.
    """
    documents = [document for service in services_of(apps) if (document := document_of(service))]
    if not documents:
        return {}
    files: dict[str, str] = {}
    for relative, content in asset_tree(found.at("api-client")).items():
        if relative == "package.json":
            package = json.loads(content)
            package["name"] = api_client_package(project_name)
            # The first service's document: a browser app talks to one API, and a project with two
            # services gives the second its own package when it gives it its own client.
            package["scripts"]["build"] = package["scripts"]["build"].replace(
                "__DOCUMENT__", f"../../{documents[0]}"
            )
            content = json.dumps(package, indent=2) + "\n"
        else:
            content = content.replace("__DOCUMENT__", documents[0])
        files[f"{API_CLIENT}/{relative}"] = content
    return files


def frontend_files(project_name: str, apps: list[App], target: str) -> dict[str, str]:
    """Every browser app, and the npm workspace manifest and lockfile above them and the Node services."""
    web = web_apps(apps)
    if not web:
        return {}
    # One frontend per project, and it is named rather than assumed. The browser apps share a workspace, a
    # lock and one Biome, so two frontends in a project would be two dependency trees npm hoists into one.
    # Which frontend it is, and where its material lives, is `npm_workspace.frontend`'s to answer: the keel
    # carries `react-vite` and a language family may carry others, and this module knows neither name.
    asked = {app.framework or frontend_of(apps) for app in web}
    if len(asked) > 1:
        raise GenerationError("a project's browser apps are all one frontend, and this one asks for "
                              f"{', '.join(sorted(asked))}")
    found = frontend(asked.pop())

    files: dict[str, str] = {}
    for app in web:
        files.update(web_files(project_name, app, apps, target, found))
    files.update(api_client_files(project_name, apps, found))

    # The workspace is shared with every service whose language is in it (`npm_workspace`), which is a property of
    # the family rather than of the backend: a service of such a family behind any framework still has npm. A
    # service of another language beside them is not a workspace member — npm would look for a package.json it does
    # not have — so the list names the member services and the browser apps and nothing else. The lock is the first
    # member service's language's, for its dependency set and then the browser apps', which every browser app in a
    # project shares; with no member service it is the frontend's own, the browser apps' alone.
    node = [service for service in services_of(apps) if npm(service.language)]
    web_suffix = web_lock_suffix(set(features_of(apps)))
    lock_path = (
        held_lock(node[0].language, "workspace_lock",
                  workspace(node[0].language).workspace_lock(node[0].selection, web_suffix))
        if node
        else found.at(f"locks/frontend-only{web_suffix}.json")
    )
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["name"] = project_name
    root_record = lock["packages"][""]
    root_record["name"] = project_name
    root_record.pop("license", None)
    workspaces = [*(service.path for service in node), *(app.path for app in web), WORKSPACE]
    root_record["workspaces"] = workspaces
    # The committed lock was resolved with one service and one browser app. Every further one adds its own
    # workspace record and link — the browser apps share one manifest, the Node services pin the same
    # versions in every variant — so the union is the tree npm would produce. Rebuilt in place so the
    # records keep the positions npm wrote them in, with the links appended as npm appends them.
    web_template = lock["packages"].pop("apps/web")
    web_link = lock["packages"].pop("node_modules/delivery-starter-web")
    # The typed client, renamed the same way. A project that has no document to generate from has no
    # package on disk either, and its records simply go — npm reads a lock entry for a workspace that is
    # not there as nothing to install, but a record naming a package nobody can find is a record nobody
    # can act on.
    client_template = lock["packages"].pop(API_CLIENT, None)
    client_link = lock["packages"].pop(f"node_modules/{API_CLIENT_NAME}", None)
    has_client = f"{API_CLIENT}/package.json" in files
    service_template = lock["packages"].pop("apps/service", None)
    service_link = lock["packages"].pop("node_modules/delivery-starter", None)
    packages: dict = {}
    for key, value in lock["packages"].items():
        packages[key] = value
        if key == "":
            for service in node:
                record = json.loads(member_lock(service).read_text(encoding="utf-8"))["packages"][""]
                packages[service.path] = dict(
                    service_template,
                    **{k: record[k] for k in ("dependencies", "devDependencies") if k in record},
                    name=package_name(project_name, service),
                )
            for app in web:
                packages[app.path] = dict(web_template, name=package_name(project_name, app))
            if has_client and client_template is not None:
                packages[API_CLIENT] = dict(client_template, name=api_client_package(project_name))
    for service in node[1:]:
        for key, value in json.loads(member_lock(service).read_text(encoding="utf-8"))["packages"].items():
            if key and key not in packages:
                packages[key] = value
    for app in web:
        packages[f"node_modules/{package_name(project_name, app)}"] = dict(web_link, resolved=app.path)
    for service in node:
        packages[f"node_modules/{package_name(project_name, service)}"] = dict(service_link, resolved=service.path)
    if has_client and client_link is not None:
        packages[f"node_modules/{api_client_package(project_name)}"] = dict(client_link, resolved=API_CLIENT)
    lock["packages"] = packages

    # The build script names the Node services and not the browser apps: a service's image runs it.
    files["package.json"] = workspace_manifest(project_name, workspaces, workspace_scripts(node))
    files["package-lock.json"] = json.dumps(lock, indent=2) + "\n"
    return files
