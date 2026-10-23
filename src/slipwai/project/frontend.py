"""The browser apps under `apps/`, and the npm workspace that holds them beside the Node services."""
from __future__ import annotations

import json
from pathlib import Path

from ..assets import PRUNER, asset_tree
from ..backends import SERVICE_PORT
from ..catalog import CATALOG
from ..errors import GenerationError
from ..npm_workspace import BrowserApp, frontend, held_lock, npm, workspace
from ..probes import HEALTH_PATH
from ..services import (
    App,
    features_of,
    frontend_of,
    prunable_features_of,
    services_of,
    web_apps,
    web_features,
)
from ..targets import managed
from ..tooling import package_name
from .openapi import API_CLIENT, API_CLIENT_NAME, api_client_package, document_of
from .shared_packages import WORKSPACE, workspace_manifest, workspace_scripts

# What a feature does to a browser app is the frontend's to say, because it is written in the frontend's
# framework: the files it adds (a directory inside the frontend's own material, laid out like the app and copied
# in whole), the paths in the app it owns, and the npm dependencies it adds to the app's manifest. The
# browser-app counterpart of a backend's `write_side_files`, and the reason the external login needs no branch
# here. They are the catalogue's `frontends.<name>.features`, declared in the family's `language.json` beside its
# backends (`docs/frontend-protocol.md`), so the pruner a generated project carries reads the same rows to take
# a feature back out (`project/pruner.py`). A browser app gets a feature's when any service in the project has
# the feature, because that is when the pruner would keep them.


def web_package_json(source: str, features: set[str], frontend: str) -> str:
    """The browser app's manifest with the dependencies its project's features need, as the frontend lists them."""
    package = json.loads(source)
    dependencies = dict(package.get("dependencies", {}))
    for feature, row in web_features(frontend).items():
        if feature in features:
            dependencies.update(row.get("dependencies", {}))
    package["dependencies"] = dict(sorted(dependencies.items()))
    return json.dumps(package, indent=2) + "\n"


def web_lock_features(frontend: str) -> tuple[str, ...]:
    """The features that add an npm dependency to `frontend`'s apps, and so the part of a workspace lock's name
    that is the browser app's: a lock is committed per dependency set, because `npm ci` refuses one that
    disagrees with its manifest."""
    return tuple(feature for feature, row in web_features(frontend).items() if row.get("dependencies"))


def web_lock_suffix(features: set[str], frontend: str) -> str:
    """The part of a workspace lock's name that is the browser app's: its `lock-name`, where its family ships
    more than one frontend and their locks need telling apart, then each dependency-adding feature —
    '' or '-users-keycloak' for a family's first frontend."""
    named = CATALOG["frontends"].get(frontend, {}).get("lock-name")
    return (f"-{named}" if named else "") + "".join(
        f"-{feature}" for feature in web_lock_features(frontend) if feature in features)


def web_files(project_name: str, web: App, apps: list[App], target: str, found: BrowserApp) -> dict[str, str]:
    """One browser app's files from the committed skeleton, named and addressed for itself.

    `found` is where that skeleton is: the frontend `--frontend <name>` named, as the family that ships it hands
    it over. Nothing here names a file inside it. Each tree — the skeleton, the flag reader and the route this
    project can use, each feature it has — is laid out like the app and copied whole, and every file in it has
    the same tokens resolved (`TOKENS`), so a frontend in another framework is a different tree and the same
    code (`docs/frontend-protocol.md`).

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
    tokens = app_tokens(project_name, web, api, status_path)
    # The flag reader, in the one shape this project can actually use. With somewhere to deploy the flag
    # lives in an environment and the service enforcing it answers for it, so the bundle asks over
    # `GET /api/flags`; with nowhere to deploy there is no environment and no reader on the service, so the
    # value comes from `.env` through the bundle — which is still the only way to hide a half-built screen.
    # Both export the same things, so the skeleton and every slice are identical either way.
    trees = ["app", "app-flags-target" if managed(CATALOG, target) else "app-flags-local"]
    # The one route, in the shape this project can actually write it. A service that publishes an API
    # document gets a client generated from it and calls through that; one whose framework publishes
    # nothing — both Java backends today — fetches by hand and says so on the page, because a type
    # asserting fields nothing promised is worse than no type at all. Not emitted at all with no API:
    # a marked region cut from a file leaves an empty file rather than no file, and the project-wide
    # prune that would delete it does not run for a project with nothing prunable.
    if api is not None:
        trees.append("app-route-client" if document_of(api) is not None else "app-route-plain")
    trees += [row["files"] for feature, row in web_features(found.name).items() if feature in features]
    files: dict[str, str] = {}
    for tree in trees:
        for relative, content in asset_tree(found.at(tree)).items():
            if tree == "app" and relative == "package.json":
                package = json.loads(web_package_json(content, features, found.name))
                package["name"] = package_name(project_name, web)
                content = json.dumps(package, indent=2) + "\n"
            content = resolved(content, tokens)
            if PRUNER.MARKER.search(content):
                content = PRUNER.strip_markers(content, keep, set())
            files[f"{web.path}/{relative}"] = content
    return files


#: The tokens a frontend's trees may carry, each resolved in every file of them: the project's name, the
#: dev server's port and the variable that moves it, the transport whose marked region the proxy sits in,
#: the port of the service it proxies to, the one path its route calls, and the typed client's package name.
TOKENS = ("__PROJECT_NAME__", "__WEB_PORT__", "__WEB_PORT_VARIABLE__", "__TRANSPORT__", "__API_PORT__",
          "__STATUS_PATH__", "__API_CLIENT__")


def app_tokens(project_name: str, web: App, api: App | None, status_path: str) -> dict[str, str]:
    """What each of `TOKENS` is for this browser app. `__TRANSPORT__` is `none` where there is nothing to call
    — a name no feature has, so the marked region goes — and the API's port the first service's otherwise."""
    return {
        "__PROJECT_NAME__": project_name,
        "__WEB_PORT_VARIABLE__": web.port_variable,
        "__WEB_PORT__": str(web.port),
        "__TRANSPORT__": (api.transport if api is not None else None) or "none",
        "__API_PORT__": str(api.port if api is not None else SERVICE_PORT),
        "__STATUS_PATH__": status_path,
        "__API_CLIENT__": api_client_package(project_name),
    }


def resolved(content: str, tokens: dict[str, str]) -> str:
    for token, value in tokens.items():
        content = content.replace(token, value)
    return content


def member_lock(service: App) -> Path:
    """A workspace member service's own committed lock, as its language answers for its selection."""
    return held_lock(service.language, "member_lock", workspace(service.language).member_lock(service.selection))


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
    # Which frontend it is, and where its material lives, is `npm_workspace.frontend`'s to answer: a family
    # ships each one, and this module knows no frontend's name.
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
    # The lock is one file resolved with every member at once, and the family that commits it can only have
    # resolved its own services beside its own browser apps. A service of one npm family beside a browser app
    # of another has no lock anybody committed, so it is refused here, naming both, rather than at `npm ci`.
    strangers = sorted({service.language for service in node if service.language != found.family})
    if strangers:
        raise GenerationError(
            f"{', '.join(strangers)} services share one npm workspace and one lock with the browser apps, and the "
            f"{found.name} browser app is {found.family}'s: no package resolves the two together. Use a frontend "
            f"{strangers[0]} ships, or a service in a language outside the npm workspace")
    web_suffix = web_lock_suffix(set(features_of(apps)), found.name)
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
