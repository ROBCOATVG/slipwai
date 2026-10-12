"""How each backend's production image is built, how its migrations run inside one, and what it is told there.

The production target deploys one image per service, built by the ecosystem's own builder rather than by a
Dockerfile — for the reason Compose already runs the checkout: nothing to keep in step with the app's layout.
ko for Go, Jib through Quarkus's own extension, `spring-boot:build-image` for Spring, and Paketo buildpacks for
Node and Python. Each backend answers how it becomes an image on its own object, as the protocol's
`image_builder` (`registry.py`, `project/languages/`), and the keel asks the registry: the Makefile, the deploy
workflow and the infrastructure all have to agree about how a service becomes an image and how its schema is
applied once it is one, and three copies of that answer are three places for it to drift. The same holds for
how its migrations run in one (`migrations_in_production`). What stays here is the keel's: the recipe vocabulary
below, the pins, the managed-database kinds with the measurements behind every backend's TLS answer, the
repository-root upload list, and the readers.

Every recipe a backend answers is a Make recipe line: `__APP__` is the service's directory (`backends.APP`),
`__IMAGE__` the image reference the recipe builds, `__REPOSITORY__` the same reference without its tag (ko
wants the two apart), and `$(PLATFORM)` / `$(GIT_SHA)` are the generated Makefile's own variables.

The third question — what a backend is *told* in production and nowhere else — is each backend's
`postgres_sslmode` and the `environment` key of its `migrations_in_production`. Both are read by
`project.infra`, which merges them into the one `environment` map the stack puts on both task definitions;
neither reaches a laptop, where the Compose Postgres has no TLS and no framework migrates as it starts.
"""
from __future__ import annotations

from typing import Any

from .backends import APP, NODE_MAJOR, PYTHON_VERSION
from .registry import IMAGE_BUILDER, MIGRATIONS_IN_PRODUCTION, registry

IMAGE = "__IMAGE__"
REPOSITORY = "__REPOSITORY__"

# The pins. Searched and chosen once; a generated project reads them out of its own Makefile and pom.
PACK_VERSION = "v0.40.9"
KO_VERSION = "v0.19.1"
# Paketo's multi-architecture Ubuntu 24.04 builder — Node.js and Python buildpacks, no C libraries — and the
# Java one Spring's `build-image` is pointed at. Both publish amd64 and arm64, which is what lets `make build`
# on a laptop produce an image the laptop can run while the pipeline builds for production's x86_64.
PAKETO_BUILDER = "paketobuildpacks/ubuntu-noble-builder:0.0.174"
PAKETO_JAVA_BUILDER = "paketobuildpacks/builder-noble-java-tiny:0.0.176"
NODE_VERSION = f"{NODE_MAJOR}.*"
CPYTHON_VERSION = f"{PYTHON_VERSION}.*"
# Jib's base for the Quarkus image: the same Temurin 25 the CI image and `actions/setup-java` install, rather
# than Quarkus's Red Hat UBI default, so one JDK vendor appears everywhere a generated Java project runs.
JIB_BASE_IMAGE = "eclipse-temurin:25-jre-noble"

# The Paketo invocation shared by the two buildpack-built backends. `--publish` when a registry is named,
# because pack then pushes straight from the build container without exporting to the local daemon — the
# path CI takes, and the one that also works on a Docker daemon using the containerd image store, where
# the daemon export fails (buildpacks/pack#2272). Without a registry the image lands in the daemon, for
# `make smoke-image`. `--platform` because a laptop is usually arm64 and production is x86_64. `$(PACK_FLAGS)`
# comes last in every recipe, so a flag it repeats — `--pull-policy always`, when the daemon holds the builder
# for the other platform and `if-not-present` would hand pack that one — is the value pack takes.
PACK = (
    f"pack build {IMAGE} $(if $(IMAGE_REGISTRY),--publish,) --builder {PAKETO_BUILDER} "
    "--platform $(PLATFORM) --pull-policy if-not-present"
)

MAVEN = f"cd {APP} && ./mvnw -B -q -DskipTests"


# **What a managed Postgres is provisioned as, per target, is the target package's declaration** — the
# `provisions` it records against the `postgres` option — so the set of kinds a backend's `postgres_sslmode`
# has to cover is read off the merged catalogue rather than listed here. Listed, it was a keel constant
# naming two clouds' products, and a third cloud's managed Postgres would have been a kind nothing asked
# any backend about.
#
# The policy itself is the managed Postgres's and not the cloud's, which is why it is keyed this way at all:
# a server that refuses an unencrypted connection refuses it whoever runs the server, and a client that
# cannot verify its certificate cannot verify it wherever the certificate came from. A backend whose driver
# ignores `PGSSLMODE` answers `None` for a kind rather than leaving it out, so "told nothing" and "not
# thought about" are different answers.
def postgres_sslmode_kinds(catalog: dict) -> tuple[str, ...]:
    """Every kind of managed Postgres the installed targets provision, in catalogue order."""
    provisioned = [held.get(target, {}).get("provisions")
                   for held in [catalog["axes"]["persistence"]["options"].get("postgres", {})]
                   for target in catalog["targets"]]
    return tuple(dict.fromkeys(kind for kind in provisioned if kind))


# `project.toml` at the repository root, read by `pack build --path .`: what stays out of the upload. The
# machine's `node_modules` is the machine's — the image installs its own from the lockfile, for its own
# platform — and `.git` is history the image has no use for. `.build/` is deliberately not excluded: `make
# build` compiles before packing, and the compiled entry point is what the image runs.
WORKSPACE_DESCRIPTOR = """# Read by `pack build --path .` (`make build`): what the upload leaves out. `node_modules` is
# this machine's; the image installs its own from the lockfile, for its own platform — uploaded, the
# buildpack would rebuild this one instead, and the compiler for the image's platform is not in it.
# `.build/` is not excluded: `make build` compiles before packing, and that is what the image runs.
[_]
schema-version = "0.2"

[io.buildpacks]
exclude = ["node_modules", ".git"]
"""


# How a service's migrations are applied once it is an image, which each backend answers as its
# `migrations_in_production` — each in the shape its ecosystem already has, and none by a step written twice.
#
# - `command`: run the service's image once more as a one-off task with this command; the same migrate the
#   Makefile runs locally, spelled inside the image. `cwd` is where the buildpack put the code.
# - `image`: a second image built from another entry point — Go's `cmd/migrate` — because ko builds one
#   binary per image, and the one-off task runs that image with its own entry point.
# - `environment`: the framework migrates the schema itself as the service starts, switched on by this
#   environment in production only; locally the default stays off, for the reasons the properties file
#   gives. Flyway holds a lock, so two replicas starting at once take turns rather than colliding.
def migrations_in_production(backend: str) -> dict[str, Any]:
    """How this backend's migrations run once it is an image: its own `migrations_in_production` answer."""
    return registry().answer(backend, MIGRATIONS_IN_PRODUCTION)


def image_builder(backend: str) -> dict[str, Any]:
    """How a service on this backend becomes an image: the backend's own `image_builder` answer."""
    return registry().answer(backend, IMAGE_BUILDER)


def tools_needed(backends: list[str]) -> list[str]:
    """The image-building tools the deploy workflow installs beyond each family's toolchain, once each."""
    tools = (image_builder(backend)["tool"] for backend in backends)
    return list(dict.fromkeys(tool for tool in tools if tool))


def spelled(text: str, path: str, image: str, repository: str) -> str:
    """One recipe, for one service and one image reference."""
    return text.replace(APP, path).replace(IMAGE, image).replace(REPOSITORY, repository)
