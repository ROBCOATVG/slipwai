"""`infra/`, `scripts/deploy.py` and the ADR: what a project going to a production target is given.

Only the `aws` target has any of this; under `none` the module contributes nothing, which is the whole
difference between the two. The HCL is copied from `assets/targets/aws/` as committed — the bootstrap stack,
the service stack, the environments' tfvars — and what the *project* decides is written beside it as data:
`project.auto.tfvars.json`, one map of the services with each answer translated into what the target provisions
for it (`store = "rds"`, `auth = "cognito"`), how each service's migrations run once it is an image, and the
environment its backend needs in production. The stack reads that map with `for_each`, so `add-service` is a
change to the data and never to the HCL.

The feature-owned parts of the stack — the database, the two user pools — sit inside `backing-service:<feature>`
marker comments in the HCL, exactly as they do in docker-compose.yml, so the same prune that drops an answer
locally drops its infrastructure too. The parts that depend on a browser app existing (the bucket and the
distribution in front of it) are chosen by file rather than marked: a frontend is not a feature.
"""
from __future__ import annotations

import json

from ..assets import ROOT, asset_tree
from ..catalog import CATALOG
from ..images import (
    IMAGE_BUILDERS,
    MIGRATIONS_IN_PRODUCTION,
    POSTGRES_SSLMODE,
    SERVICE_DESCRIPTORS,
    WORKSPACE_DESCRIPTOR,
)
from ..naming import python_package_name
from ..probes import HEALTH_PATH, ready_path
from ..services import App, family_of, services_of, web_apps
from ..targets import managed
from ..tooling import for_app, service_qualifier
from .flag_route import wire_transports
from .provisioning import provisioned
from .target_docs import pages

TARGET_ROOT = ROOT / "assets/targets"  # also `targets.TARGET_ROOT`; spelled here for the asset reads below

# `frontend.tf` is emitted whichever way, with one of two contents: the site behind CloudFront when the project
# has a browser app, and only the public address otherwise. One file rather than two chosen between, because
# `add-frontend` rewrites the files whose content changes and deletes nothing — two files would leave the
# old one behind, defining the address twice.
WITH_FRONTEND = "service/frontend.tf"
WITHOUT_FRONTEND = "service/no-frontend.tf"

# The same two-file choice for the one answer whose provider will not configure itself without a credential.
# Auth0 is a third party: the provider is configured the moment anything in the module refers to it — a
# `count = 0` resource is enough — and it refuses to configure without a tenant credential. A project that
# did not choose Auth0 has none, so it must not carry the provider at all, and the choice cannot be left to
# the pruner: `keycloak` is the feature behind Cognito, Entra *and* Auth0, so no marker can tell them apart.
WITH_AUTH0 = "service/auth0.tf"
WITHOUT_AUTH0 = "service/no-auth0.tf"


def migrations_of(service: App) -> dict:
    """How this service's migrations run in production, in the two fields the stack reads."""
    fields: dict = {"migrate_command": None, "migrate_image": None}
    if service.selection.migrating_feature is None:
        return fields
    strategy = MIGRATIONS_IN_PRODUCTION[service.backend]
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
    - The **store**, for the client half of a managed Postgres's TLS policy (`images.POSTGRES_SSLMODE`,
      where the per-driver divergence is written down, `None` included — a backend whose driver ignores
      `PGSSLMODE` is told nothing rather than told something inert). Keyed by what the target provisions
      the store as, because the policy is the managed Postgres's and not the cloud's. Gated on the store
      and nothing else: a service that reads Postgres and never migrates it still cannot connect without
      this, so gating it on the migration strategy would have given the fix to only some of the services
      that need it.
    """
    environment: dict[str, str] = {}
    if service.selection.migrating_feature is not None:
        environment.update(MIGRATIONS_IN_PRODUCTION[service.backend].get("environment", {}))
    store = provisioned(service, "event-store", target)
    sslmode = POSTGRES_SSLMODE.get(store, {}).get(service.backend) if store else None
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
        "store": provisioned(service, "event-store", target),
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
    """The start command of each Python service, for the buildpack: it has no other way to know that the
    package lives under `src/`. Nothing else in the project reads this file."""
    files: dict[str, str] = {}
    for service in services_of(apps):
        if IMAGE_BUILDERS[service.backend]["tool"] != "pack" or family_of(service.backend) != "python":
            continue
        package = python_package_name(service_qualifier(project_name, service))
        files[f"{service.path}/Procfile"] = (
            "# The production start command, read by the Paketo buildpack `make build` runs; `make dev` does\n"
            "# not use it. `src` is prepended to PYTHONPATH because the package lives under src/, exactly as\n"
            "# scripts/verify says — prepended, not set, because the buildpack's own PYTHONPATH is where the\n"
            "# installed packages are; replacing it starts a container that cannot import uvicorn.\n"
            f"web: PYTHONPATH=src:$PYTHONPATH python -m {package}.main\n"
        )
    return files


def target_files(project_name: str, profile: str, target: str, apps: list[App]) -> dict[str, str]:
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
    for relative, content in asset_tree(TARGET_ROOT / target).items():
        if relative.startswith("scripts/"):
            files[relative] = content
            continue
        if relative == (WITH_FRONTEND if not web else WITHOUT_FRONTEND):
            continue
        if relative == WITHOUT_FRONTEND:
            relative = WITH_FRONTEND
        if relative == (WITH_AUTH0 if not auth0 else WITHOUT_AUTH0):
            continue
        if relative == WITHOUT_AUTH0:
            relative = WITH_AUTH0
        files[f"infra/{relative}"] = content
    # Which flag transports this project's services can actually read. See `flag_route.wire_transports`.
    wire_transports(files, {service.backend for service in services_of(apps)}, target)
    data = tfvars(project_name, apps, target)
    files["infra/bootstrap/project.auto.tfvars.json"] = data
    files["infra/service/project.auto.tfvars.json"] = data
    files.update(procfiles(project_name, apps))
    files.update(pages(project_name, apps, target))
    if any(IMAGE_BUILDERS[s.backend].get("packs_workspace") for s in services_of(apps)):
        files["project.toml"] = WORKSPACE_DESCRIPTOR
    # And one beside each service whose own directory is what gets packed.
    for service in services_of(apps):
        descriptor = IMAGE_BUILDERS[service.backend].get("descriptor")
        if descriptor:
            files[f"{service.path}/project.toml"] = SERVICE_DESCRIPTORS[descriptor]
    return files


