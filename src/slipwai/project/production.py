"""The Makefile's production section: build, push, smoke, deploy, rollback — only under a production target.

Split from `makefile.py`, which is at its budget, and because these targets are a different kind of recipe:
the eight native targets are what every service owes whatever its destination, and these exist only when there
is a destination. What differs per backend — how a service becomes an image, and how its migrations run once
it is one — is read from `images.py`; the verbs that need more than one line hand off to `scripts/deploy.py`.
"""
from __future__ import annotations

from ..images import IMAGE_BUILDERS, MIGRATIONS_IN_PRODUCTION, spelled
from ..services import App, services_of

# Per target: the cloud a person signs in to, the registry the images go to, one of its addresses as an
# example, and whose CPU architecture the default `PLATFORM` is. Four words in one comment block — the verbs
# either side of them are the same everywhere, which is the point of `scripts/deploy.py` owning them.
REGISTRY = {
    "aws": ("AWS", "ECR", "123456789012.dkr.ecr.eu-west-2.amazonaws.com/", "Fargate"),
    "azure": ("Azure", "ACR", "acrshop1a2b3c4d.azurecr.io/", "Container Apps"),
}


def image_variables(project_name: str, services: list[App]) -> str:
    """`IMAGE_REPOSITORY` and `IMAGE` per service — `IMAGE_LEDGER` after the first — and the migrate image a
    backend builds beside a service's own."""
    text = ""
    for service in services:
        text += (
            f"IMAGE_REPOSITORY{service.suffix} = $(IMAGE_REGISTRY){project_name}-{service.name}\n"
            f"IMAGE{service.suffix} = $(IMAGE_REPOSITORY{service.suffix}):$(GIT_SHA)\n"
        )
        if migrate_image_of(service):
            text += (
                f"IMAGE_REPOSITORY{service.suffix}_MIGRATE = $(IMAGE_REGISTRY){project_name}-{service.name}-migrate\n"
                f"IMAGE{service.suffix}_MIGRATE = $(IMAGE_REPOSITORY{service.suffix}_MIGRATE):$(GIT_SHA)\n"
            )
    return text


def migrate_image_of(service: App) -> bool:
    """Whether this service's migrations run from an image of their own, built beside the service's."""
    return (
        service.selection.migrating_feature is not None
        and "image" in MIGRATIONS_IN_PRODUCTION[service.backend]
    )


def build_targets(services: list[App]) -> str:
    text = ""
    for service in services:
        builder = IMAGE_BUILDERS[service.backend]
        tool = builder["tool"] or "its framework's own build"
        recipe = spelled(builder["build"], service.path, f"$(IMAGE{service.suffix})", f"$(IMAGE_REPOSITORY{service.suffix})")
        text += f"build-{service.name}: ## Build {service.name}'s image with {tool}\n\t{recipe}\n"
        if migrate_image_of(service):
            recipe = spelled(
                MIGRATIONS_IN_PRODUCTION[service.backend]["build"], service.path,
                f"$(IMAGE{service.suffix}_MIGRATE)", f"$(IMAGE_REPOSITORY{service.suffix}_MIGRATE)",
            )
            text += f"\t{recipe}\n"
    return text


def named_images(services: list[App]) -> str:
    """`name=$(IMAGE)` for every image, as `scripts/deploy.py` takes them."""
    pairs = []
    for service in services:
        pairs.append(f"{service.name}=$(IMAGE{service.suffix})")
        if migrate_image_of(service):
            pairs.append(f"{service.name}-migrate=$(IMAGE{service.suffix}_MIGRATE)")
    return " ".join(pairs)


def production_targets(project_name: str, apps: list[App], target: str) -> str:
    """The whole production section, for a project with a destination."""
    services = services_of(apps)
    builds = " ".join(f"build-{service.name}" for service in services)
    migrating = [s for s in services if s.selection.migrating_feature is not None]
    # Only a store applied by a task — not by the framework at start-up — gives a person something to run by
    # hand, and it goes with the store: inside the migrating feature's marked region.
    remote = ""
    features = dict.fromkeys(
        s.selection.migrating_feature for s in migrating if "environment" not in MIGRATIONS_IN_PRODUCTION[s.backend]
    )
    for feature in features:
        remote += f"""# backing-service:{feature}:begin
.PHONY: migrate-remote
migrate-remote: ## Run the services' migrations inside an environment, as a one-off task: make migrate-remote ENV=staging
\tpython3 scripts/deploy.py migrate $(ENV)
# backing-service:{feature}:end
"""
    # One service needs no `SERVICE=` on every flip; more than one has no defensible default, so the example
    # names one rather than the Makefile guessing at it.
    if len(services) == 1:
        flag_service = f"SERVICE ?= {services[0].name}\n"
        flag_example = "make flag ENV=production KEY=checkout-v2 VALUE=off"
    else:
        flag_service = ""
        flag_example = f"make flag ENV=production SERVICE={services[0].name} KEY=checkout-v2 VALUE=off"
    cloud, registry, registry_example, platform = REGISTRY[target]
    return f"""
# ── Production ────────────────────────────────────────────────────────────────────────────────────────
# One image per service, built by the ecosystem's own builder and tagged with the commit that built it.
# IMAGE_REGISTRY is the {registry} prefix the bootstrap stack printed (`{registry_example}`);
# empty, the images stay in the local Docker daemon, which is what `make smoke-image` runs. PLATFORM is
# {platform}'s; a laptop overrides it to run its own build (`make build smoke-image PLATFORM=linux/arm64`).
# PACK_FLAGS is anything more `pack build` should be told — `--network host` so its containers reach a
# registry on this machine's localhost, `--pull-policy always` when the daemon holds the builder for the
# other platform — and is empty for {registry}. It comes last, so a flag it repeats is the one pack takes.
GIT_SHA ?= $(shell git rev-parse HEAD)
IMAGE_REGISTRY ?=
PLATFORM ?= linux/amd64
PACK_FLAGS ?=
ENV ?= staging
{flag_service}{image_variables(project_name, services)}
.PHONY: bootstrap build {builds} push smoke-image smoke deploy promote rollback url flag flags
bootstrap: ## Once, with admin {cloud} credentials: create what the pipeline needs and configure the repository on the forge
	python3 scripts/bootstrap.py $(if $(REPOSITORY),--repository $(REPOSITORY),) $(if $(FORGE),--forge $(FORGE),) $(if $(AUTO_PROMOTE),--auto-promote $(AUTO_PROMOTE),)
build: {builds} ## Build every service's production image (into the daemon, or --publish to IMAGE_REGISTRY)
{build_targets(services)}push: ## Push every built image and record the digests in .build/images.json (needs IMAGE_REGISTRY and a docker login)
\tpython3 scripts/deploy.py push {named_images(services)}
smoke-image: ## Run each built image locally and prove it starts, listens and answers its probe
\tpython3 scripts/deploy.py smoke-image {named_images(services)}
deploy: ## Apply an environment from .build/images.json, migrate, upload the site, record the release: make deploy ENV=staging
\tpython3 scripts/deploy.py deploy $(ENV)
promote: ## Deploy production with the commit staging is running (the forge runs it): make promote
	python3 scripts/deploy.py promote $(COMMIT)
rollback: ## Re-apply the release before the current one: make rollback ENV=production
\tpython3 scripts/deploy.py rollback $(ENV)
url: ## Print an environment's address: make url ENV=staging
\t@python3 scripts/deploy.py url $(ENV)
flag: ## Set a feature flag and restart the service that reads it: {flag_example}
\tpython3 scripts/deploy.py flag $(ENV) $(SERVICE) $(KEY) $(VALUE)
flags: ## Print an environment's feature flags and what they are set to now: make flags ENV=staging
\t@python3 scripts/deploy.py flags $(ENV)
smoke: ## Prove a deployed environment answers: make smoke URL=$$(make -s url ENV=staging)
\tpython3 scripts/deploy.py smoke $(URL)
{remote}"""
