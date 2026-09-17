"""The browser apps under `apps/`, and the npm workspace that holds them beside the Node services."""
from __future__ import annotations

import json

from ..assets import FRONTEND_ROOT, PRUNER, asset_tree
from ..backends import WEB_PORT
from ..catalog import CATALOG
from ..errors import GenerationError
from ..probes import HEALTH_PATH
from ..services import App, features_of, prunable_features_of, services_of, web_apps
from ..targets import managed
from ..tooling import package_name
from .languages.typescript import (
    lock_suffix,
    service_lock,
    web_lock_suffix,
    web_package_json,
    workspace_manifest,
    workspace_scripts,
)
from .openapi import API_CLIENT, API_CLIENT_NAME, api_client_package, document_of
from .shared_packages import WORKSPACE

# What a feature adds to every browser app, keyed by feature: a directory under
# `assets/frontends/react-vite/` laid out like the app, copied in whole. The browser-app counterpart of
# `SERVICE_FILES`, and the reason the customer login needs no branch — a second provider is a row here. Kept
# in step with `OWNED_FILES_PER_WEB_APP` in assets/backing-services/prune.py, which removes them again.
WEB_FEATURE_FILES: dict[str, str] = {
    "users-keycloak": "react-vite/features/users-keycloak",
}


def web_files(project_name: str, web: App, apps: list[App], target: str) -> dict[str, str]:
    """One browser app's files from the committed skeleton, named and addressed for itself.

    The skeleton is written for the first browser app on 5173 talking to a service on 3000; a later one is
    given its own dev-server port and the address of the service it proxies to, and the proxy sits in that
    service's transport's marked region. Every other marked region is a feature some service has — the
    customer login — and the files a feature adds arrive with it.

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
    for relative, content in asset_tree(FRONTEND_ROOT / "react-vite/app").items():
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
        content = (FRONTEND_ROOT / "react-vite" / variant / relative).read_text()
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
            content = (FRONTEND_ROOT / "react-vite" / variant / relative).read_text()
            files[f"{web.path}/{destination}"] = spoken_for_app(content, project_name, api, status_path)
    for feature, source in WEB_FEATURE_FILES.items():
        if feature not in features:
            continue
        for relative, content in asset_tree(FRONTEND_ROOT / source).items():
            files[f"{web.path}/{relative}"] = content
    return files


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


def api_client_files(project_name: str, apps: list[App]) -> dict[str, str]:
    """`packages/api-client`: the typed client, generated from the document its service publishes.

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
    for relative, content in asset_tree(FRONTEND_ROOT / "react-vite/api-client").items():
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
    if any(app.framework != "react-vite" for app in web):
        raise GenerationError(f"unsupported frontend capability: {web[0].framework}")

    files: dict[str, str] = {}
    for app in web:
        files.update(web_files(project_name, app, apps, target))
    files.update(api_client_files(project_name, apps))

    # The workspace is shared with every Node service, which is a property of the language rather than of
    # the backend: a TypeScript service behind any framework still has npm. A Python or Go service beside
    # them is not a workspace — npm would look for a package.json it does not have — so the list names the
    # Node services and the browser apps and nothing else. The lock is named for the first Node service's
    # dependency set and then the browser apps', which every browser app in a project shares.
    node = [service for service in services_of(apps) if service.language == "typescript"]
    web_suffix = web_lock_suffix(set(features_of(apps)))
    lock_name = (
        f"typescript-backend{lock_suffix(node[0].selection)}{web_suffix}.json"
        if node
        else f"frontend-only{web_suffix}.json"
    )
    lock = json.loads((FRONTEND_ROOT / f"react-vite/locks/{lock_name}").read_text())
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
                record = json.loads(service_lock(service.selection).read_text())["packages"][""]
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
        for key, value in json.loads(service_lock(service.selection).read_text())["packages"].items():
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
