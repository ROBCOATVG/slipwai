"""`infra/`, `scripts/deploy.py` and the ADR: what a project going to a production target is given.

Only a managed target has any of this; under `none` the module contributes nothing, which is the whole
difference between the two. The HCL is copied from the target package as committed — the bootstrap stack,
the service stack, the environments' tfvars, named by its `shapes` — and what the *project* decides is
written beside it as data:
`project.auto.tfvars.json`, one map of the services with each answer translated into what the target provisions
for it (`store` and `auth` as that target provisions them), how each service's migrations run once it is an
image, and the
environment its backend needs in production. The stack reads that map with `for_each`, so `add-service` is a
change to the data and never to the HCL.

The feature-owned parts of the stack — the database, the two user pools — sit inside `backing-service:<feature>`
marker comments in the HCL, exactly as they do in docker-compose.yml, so the same prune that drops an answer
locally drops its infrastructure too. The parts that depend on a browser app existing (the bucket and the
distribution in front of it) are chosen by file rather than marked: a frontend is not a feature.
"""
from __future__ import annotations

import json

from ..catalog import CATALOG
from ..deployment_shapes import row
from ..images import WORKSPACE_DESCRIPTOR, image_builder, migrations_in_production
from ..loaded_targets import answer, root_of
from ..probes import HEALTH_PATH, ready_path
from ..registry import POSTGRES_SSLMODE, PROCFILE, SERVICE_DESCRIPTORS, registry
from ..services import App, services_of, web_apps
from ..target_protocol import SCRIPTS, SHAPES
from ..targets import managed
from ..tooling import for_app
from .flag_route import wire_transports
from .provisioning import provisioned
from .target_docs import pages

# `frontend.tf` is emitted whichever way, with one of two contents: the site behind whatever the target
# puts in front of it when the project has a browser app, and only the public address otherwise. One file rather than two chosen between, because
# `add-frontend` rewrites the files whose content changes and deletes nothing — two files would leave the
# old one behind, defining the address twice.
WITH_FRONTEND = "service/frontend.tf"
WITHOUT_FRONTEND = "service/no-frontend.tf"

# The same two-file choice for the one answer whose provider will not configure itself without a credential.
# Auth0 is a third party: the provider is configured the moment anything in the module refers to it — a
# `count = 0` resource is enough — and it refuses to configure without a tenant credential. A project that
# did not choose Auth0 has none, so it must not carry the provider at all, and the choice cannot be left to
# the pruner: `keycloak` is the feature behind every target's own identity answer *and* Auth0, so no
# marker can tell them apart.
WITH_AUTH0 = "service/auth0.tf"
WITHOUT_AUTH0 = "service/no-auth0.tf"


def migrations_of(service: App) -> dict:
    """How this service's migrations run in production, in the two fields the stack reads."""
    fields: dict = {"migrate_command": None, "migrate_image": None}
    if service.selection.migrating_feature is None:
        return fields
    strategy = migrations_in_production(service.backend)
    if "command" in strategy:
        fields["migrate_command"] = [for_app(word, service.path) for word in strategy["command"]]
    if "image" in strategy:
        fields["migrate_image"] = f"{service.name}-{strategy['image']}"
    return fields


def production_environment(service: App, target: str) -> dict[str, str]:
    """What this service's backend has to be told in production and nowhere else.

    Two contributions from two different answers, which is why this is not a field of `migrations_of`:

    - The migration strategy, for a framework that applies the schema as the service starts (both Java
      backends). Gated on there being something to migrate at all.
    - The **store**, for the client half of a managed Postgres's TLS policy (the backend's
      `postgres_sslmode`; `images.py` writes the per-driver divergence down above
      `postgres_sslmode_kinds`, `None` included — a backend whose driver ignores `PGSSLMODE` is told
      nothing rather than told something inert). Keyed by what the target provisions the store as,
      because the policy is the managed Postgres's and not the cloud's. Gated on the store
      and nothing else: a service that reads Postgres and never migrates it still cannot connect without
      this, so gating it on the migration strategy would have given the fix to only some of the services
      that need it.
    """
    environment: dict[str, str] = {}
    if service.selection.migrating_feature is not None:
        environment.update(migrations_in_production(service.backend).get("environment", {}))
    store = provisioned(service, "persistence", target)
    sslmode = registry().answer(service.backend, POSTGRES_SSLMODE).get(store) if store else None
    if sslmode is not None:
        environment["PGSSLMODE"] = sslmode
    return environment


def service_record(service: App, target: str) -> dict:
    return {
        "port": service.port,
        # The path the platform's own health check asks — and it is the *readiness* path, not the
        # liveness one. An ALB target group and an App Service probe both decide whether to send a
        # revision traffic, which is the question `/ready` answers by asking the event store; `/health`
        # says only that the process is listening, and a service whose store is unreachable would pass it
        # all day while every request failed. The key keeps the platforms' own name for it.
        "health_path": ready_path(service.backend),
        # And the other question, for the platform that asks both: liveness is "is this process up", and a
        # probe that fails it is a restart. A backend whose framework serves one readiness endpoint answers
        # both on one path, which is honest — it is the probe that framework maintains.
        "liveness_path": HEALTH_PATH,
        "store": provisioned(service, "persistence", target),
        "auth": provisioned(service, "auth", target),
        "users": provisioned(service, "users", target),
        **migrations_of(service),
        "environment": production_environment(service, target),
    }


def tfvars(project_name: str, apps: list[App], target: str) -> str:
    """`project.auto.tfvars.json`: the one file both stacks read for what this project is."""
    web = web_apps(apps)
    document = {
        "project": project_name,
        "services": {service.name: service_record(service, target) for service in services_of(apps)},
        "web": {"path": web[0].path, "api": web[0].api} if web else None,
    }
    return json.dumps(document, indent=2) + "\n"


def image_names(project_name: str, apps: list[App]) -> dict[str, App]:
    """Every image the project builds, keyed by its name in `images.json` — a service's, and the migrate image
    a backend builds beside it."""
    names: dict[str, App] = {}
    for service in services_of(apps):
        names[service.name] = service
        if migrations_of(service)["migrate_image"] is not None:
            names[f"{service.name}-migrate"] = service
    return names


def procfiles(project_name: str, apps: list[App]) -> dict[str, str]:
    """The start command of each service whose backend answers one, for the buildpack (`pack`) that reads it: the
    backend's `procfile`. A backend that needs none answers `None`."""
    files: dict[str, str] = {}
    for service in services_of(apps):
        procfile = registry().answer(service.backend, PROCFILE)
        if image_builder(service.backend)["tool"] != "pack" or procfile is None:
            continue
        files[f"{service.path}/Procfile"] = procfile(project_name, service)
    return files


def read_from(target: str, relative: str) -> str:
    """One file of the target's package, as written. A package's own files are text the keel copies."""
    return (root_of(target) / relative).read_text(encoding="utf-8")


def stack_files(target: str, shape: str = "liner") -> dict[str, str]:
    """Both stacks, by the path they take under `infra/`, which is the path they have in the package.

    The two shapes are named by the protocol and not by each package, so `make bootstrap` applies the first
    and `make deploy` the second on every cloud. What is *in* each is the package's to say.
    """
    if choice := row(target, shape):
        return {destination: read_from(target, source)
                for files in choice["stacks"].values() for destination, source in files.items()}
    shapes = answer(target, SHAPES, default={})
    return {relative: read_from(target, relative)
            for shape in sorted(shapes) for relative in sorted(shapes[shape])}


def target_scripts(target: str, shape: str = "liner") -> dict[str, str]:
    """What the project gets under `scripts/` to bootstrap the account and deploy into it, by the path it
    lands at — which the package names, because the path in the project and the path in the package are two
    different facts and a package that moved a file should not move it in every project."""
    choice = row(target, shape)
    scripts = choice["scripts"] if choice else answer(target, SCRIPTS, default={})
    return {where: read_from(target, source) for where, source in sorted(scripts.items())}


def target_files(
    project_name: str, profile: str, target: str, apps: list[App], shape: str = "liner",
) -> dict[str, str]:
    """Everything a managed production target adds to the repository; nothing for `none` or `existing`."""
    if not managed(CATALOG, target):
        return {}
    files: dict[str, str] = {}
    web = web_apps(apps)
    auth0 = any(
        provisioned(service, axis, target) == "auth0"
        for service in services_of(apps)
        for axis in ("auth", "users")
    )
    for relative, content in stack_files(target, shape).items():
        if relative == (WITH_FRONTEND if not web else WITHOUT_FRONTEND):
            continue
        if relative == WITHOUT_FRONTEND:
            relative = WITH_FRONTEND
        if relative == (WITH_AUTH0 if not auth0 else WITHOUT_AUTH0):
            continue
        if relative == WITHOUT_AUTH0:
            relative = WITH_AUTH0
        files[f"infra/{relative}"] = content
    files.update(target_scripts(target, shape))
    # Which flag transports this project's services can actually read. See `flag_route.wire_transports`.
    wire_transports(files, {service.backend for service in services_of(apps)}, target)
    data = tfvars(project_name, apps, target)
    files["infra/bootstrap/project.auto.tfvars.json"] = data
    files["infra/service/project.auto.tfvars.json"] = data
    files.update(procfiles(project_name, apps))
    files.update(pages(project_name, apps, target, shape))
    if choice := row(target, shape):
        files["infra/SHAPE.md"] = (
            f"# {shape.title()} deployment\n\nCompute: {choice['compute']}.\n\n"
            f"Database: {choice['database']}.\n\n{choice['guidance']}\n\n{choice['transition']}\n"
        )
    if any(image_builder(s.backend).get("packs_workspace") for s in services_of(apps)):
        files["project.toml"] = WORKSPACE_DESCRIPTOR
    # And one beside each service whose own directory is what gets packed.
    for service in services_of(apps):
        for name, text in registry().answer(service.backend, SERVICE_DESCRIPTORS).items():
            files[f"{service.path}/{name}"] = text
    return files


