"""How each backend's production image is built, how its migrations run inside one, and what it is told there.

The production target deploys one image per service, built by the ecosystem's own builder rather than by a
Dockerfile — for the reason Compose already runs the checkout: nothing to keep in step with the app's layout.
ko for Go, Jib through Quarkus's own extension, `spring-boot:build-image` for Spring, and Paketo buildpacks for
Node and Python. One table per question, keyed by backend, the way `backends.py` is: the Makefile, the deploy
workflow and the infrastructure all have to agree about how a service becomes an image and how its schema is
applied once it is one, and three copies of that answer are three places for it to drift.

Every command here is a Make recipe line: `__APP__` is the service's directory (`backends.APP`), `__IMAGE__`
the image reference the recipe builds, `__REPOSITORY__` the same reference without its tag (ko wants the two
apart), and `$(PLATFORM)` / `$(GIT_SHA)` are the generated Makefile's own variables.

The third question — what a backend is *told* in production and nowhere else — is `POSTGRES_SSLMODE` and the
`environment` key of `MIGRATIONS_IN_PRODUCTION`. Both are read by `project.infra`, which merges them into the
one `environment` map the stack puts on both task definitions; neither reaches a laptop, where the Compose
Postgres has no TLS and no framework migrates as it starts.
"""
from __future__ import annotations

from typing import Any

from .backends import APP, NODE_MAJOR, PYTHON_VERSION

IMAGE = "__IMAGE__"
REPOSITORY = "__REPOSITORY__"

# The pins. Searched and chosen once; a generated project reads them out of its own Makefile and pom.
PACK_VERSION = "v0.40.9"
KO_VERSION = "v0.19.1"
# Paketo's multi-architecture Ubuntu 24.04 builder — Node.js and Python buildpacks, no C libraries — and the
# Java one Spring's `build-image` is pointed at. Both publish amd64 and arm64, which is what lets `make build`
# on a laptop produce an image the laptop can run while the pipeline builds for Fargate's x86_64.
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
# `make smoke-image`. `--platform` because a laptop is usually arm64 and Fargate is x86_64. `$(PACK_FLAGS)`
# comes last in every recipe, so a flag it repeats — `--pull-policy always`, when the daemon holds the builder
# for the other platform and `if-not-present` would hand pack that one — is the value pack takes.
PACK = (
    f"pack build {IMAGE} $(if $(IMAGE_REGISTRY),--publish,) --builder {PAKETO_BUILDER} "
    "--platform $(PLATFORM) --pull-policy if-not-present"
)

MAVEN = f"cd {APP} && ./mvnw -B -q -DskipTests"

# How one service becomes an image, per backend. `tool` is what the deploy workflow has to install on the
# runner for it (`pack`, `ko`, or nothing beyond the toolchain `verify` already set up).
IMAGE_BUILDERS: dict[str, dict[str, Any]] = {
    "typescript": {
        "tool": "pack",
        # Compiled first, by the same `build` script `make dev` runs, and only then packed. The buildpacks
        # cannot do the compiling: Paketo's npm-install copies every npm workspace package into its module
        # layers and leaves a symlink at `apps/<service>` before any `BP_NODE_RUN_SCRIPTS` script runs, so
        # what such a script writes there afterwards lands in the build-time copy and is missing from the
        # image — the container then dies with "Cannot find module …/.build/src/main.js". Compiled up front,
        # `.build/` is part of the workspace when the copy is made. The whole workspace is packed, because
        # the lockfile is the repository's; `BP_LAUNCHPOINT` names this service's compiled entry point, which
        # exists by the time node-start looks for it. `BP_NODE_RUN_SCRIPTS=` (empty) because the run-script
        # buildpack otherwise runs `build` again inside the image — its default — into the copy that is
        # thrown away. And the machine's `node_modules` stays out of the upload (`project.toml`,
        # `WORKSPACE_DESCRIPTOR`): uploaded, npm-install would `npm rebuild` it for the image instead of
        # installing from the lockfile, and a compiler for the image's platform is not in a laptop's.
        # No install step: `build-<service>` takes the npm dependency target as a prerequisite like every
        # other target that runs this project's own npm code (`project/shared_packages`), so the workspace
        # is installed by the time this recipe runs and installed once however many targets asked.
        "build": (
            f"npm --workspace {APP} run build\n\t"
            f"{PACK} --path . --env BP_NODE_VERSION={NODE_VERSION} --env BP_NODE_RUN_SCRIPTS= "
            f"--env BP_LAUNCHPOINT={APP}/.build/src/main.js $(PACK_FLAGS)"
        ),
        "packs_workspace": True,
    },
    "python": {
        "tool": "pack",
        # The service alone: a Python service is self-contained, and the Procfile the target writes beside
        # it is the start command.
        #
        # The requirements file is *exported from the lock* immediately before the build rather than
        # committed, and `--no-dev` is the point of it: the image carries what the service imports when it
        # is running and not the gate's mypy, pytest and ruff. Hashes and all, derived every time, so it
        # can never become a second dependency list that drifts from the first.
        #
        # `uv.lock` itself stays out of the upload (`SERVICE_DESCRIPTOR` below), which is what makes the
        # buildpack read that file: the pinned builder's Python group selects its package manager by what
        # it finds, and a `uv.lock` in the upload sends it to install uv from a GitHub release inside the
        # build. That is a third host to be reachable from wherever `make build` runs, for a resolution
        # this repository has already done and committed. The day the builder ships uv itself, this
        # exclusion and the export both go and the lock is uploaded as it stands.
        "build": (
            f"cd {APP} && uv export --frozen --no-dev --no-emit-project --quiet -o requirements.txt\n\t"
            f"{PACK} --path {APP} --env BP_CPYTHON_VERSION={CPYTHON_VERSION} "
            "--env BP_PIP_REQUIREMENT=requirements.txt $(PACK_FLAGS)"
        ),
        "descriptor": "python",
    },
    "go": {
        "tool": "ko",
        # `--bare` so the image is exactly `__REPOSITORY__`, `--local` so it lands in the daemon like every
        # other backend's and `make push` is one command for all of them. ko's default base is Chainguard's
        # static image, which is right for a binary that needs nothing; `KO_DEFAULTBASEIMAGE` overrides it.
        "build": (
            f"cd {APP} && KO_DOCKER_REPO={REPOSITORY} ko build ./cmd/serve --bare --local "
            "--tags $(GIT_SHA) --platform $(PLATFORM)"
        ),
    },
    "java-quarkus": {
        "tool": "",
        # Quarkus's own Jib extension, into the daemon; the base image is pinned in application.properties.
        "build": (
            f"{MAVEN} package -Dquarkus.container-image.build=true "
            f"-Dquarkus.container-image.image={IMAGE} -Dquarkus.jib.platforms=$(PLATFORM)"
        ),
    },
    "java-spring": {
        "tool": "",
        # Spring Boot's own buildpack build, into the daemon; the builder is pinned in the pom.
        "build": (
            f"{MAVEN} spring-boot:build-image -Dspring-boot.build-image.imageName={IMAGE} "
            "-Dspring-boot.build-image.imagePlatform=$(PLATFORM)"
        ),
    },
}

# How a service's migrations are applied once it is an image, per backend — each in the shape its ecosystem
# already has, and none by a step written twice.
#
# - `command`: run the service's image once more as a one-off task with this command; the same migrate the
#   Makefile runs locally, spelled inside the image. `cwd` is where the buildpack put the code.
# - `image`: a second image built from another entry point — Go's `cmd/migrate` — because ko builds one
#   binary per image, and the one-off task runs that image with its own entry point.
# - `environment`: the framework migrates the schema itself as the service starts, switched on by this
#   environment in production only; locally the default stays off, for the reasons the properties file
#   gives. Flyway holds a lock, so two replicas starting at once take turns rather than colliding.
MIGRATIONS_IN_PRODUCTION: dict[str, dict[str, Any]] = {
    "typescript": {"command": ["npm", "--workspace", APP, "run", "migrate"]},
    "python": {"command": ["python", "migrations/apply.py"]},
    "go": {"image": "migrate", "build": (
        f"cd {APP} && KO_DOCKER_REPO={REPOSITORY} ko build ./cmd/migrate --bare --local "
        "--tags $(GIT_SHA) --platform $(PLATFORM)"
    )},
    "java-quarkus": {"environment": {"QUARKUS_FLYWAY_MIGRATE_AT_START": "true"}},
    "java-spring": {"environment": {"SPRING_FLYWAY_ENABLED": "true"}},
}


# What each backend's Postgres client has to be told before it will encrypt its connection, for the one
# deployment where the server insists on it: a managed Postgres. RDS's `default.postgres17` parameter group
# has carried `rds.force_ssl = 1` since Postgres 15, so an unencrypted connection is refused outright — the
# server answers SQLSTATE `28000`, `no pg_hba.conf entry for host "…", user "app", database "app", no
# encryption`, and the migrate task exits 1 before a single statement runs. Nothing the factory emitted
# asked for encryption, so this was every generated project's first deploy, not one project's accident.
#
# Read per service by `project.infra.production_environment` and set in the container environment. Not set
# locally: the Compose Postgres runs without TLS, so a laptop has nothing to negotiate with.
#
# **Three answers, not one**, and this table exists for that alone. Every row below was settled by running
# the driver against a Postgres configured exactly as RDS is — `ssl=on` with a self-signed certificate and
# `hostnossl … reject`, which is what `rds.force_ssl = 1` amounts to — rather than from the documentation,
# because two of the three answers are not what the documentation would lead you to expect.
#
# - `typescript` → `no-verify`. `node-postgres` reads `PGSSLMODE` with its own vocabulary rather than
#   libpq's (`pg@8.23.0/lib/connection-parameters.js:34-35`, and again at :93-95): `require` there means
#   *verify* the server certificate against Node's bundled CA store, and RDS's certificate chains to
#   Amazon's private RDS root CA, which is not in that store. Measured: unset fails with `28000`,
#   `require` fails with `DEPTH_ZERO_SELF_SIGNED_CERT`, `no-verify` connects over TLSv1.3. This is the
#   only backend whose default is no TLS at all, and therefore the only one that was actually broken.
# - `python`, `go` → `require`. psycopg (libpq) and pgx (its own libpq-compatible parsing) both honour the
#   variable with libpq's semantics, where `require` already *is* "encrypt, do not verify". Measured for
#   both: `require` connects over TLSv1.3, and `disable` is refused with `28000` — which is what proves the
#   variable is read rather than merely harmless. Their default is libpq's `prefer`, so they would have
#   reached RDS anyway; `require` is what stops a silent fall back to plaintext against a server that ever
#   permits it.
# - `java-quarkus`, `java-spring` → **nothing, deliberately**. The PostgreSQL JDBC driver does not read
#   `PGSSLMODE`: the string appears nowhere in `postgresql-42.7.13.jar`, whose `PGEnvironment` reads only
#   `PGPASSFILE`, `PGSERVICEFILE` and `PGSYSCONFDIR`. Measured: with `PGSSLMODE=disable` exported, pgjdbc
#   still connects over TLSv1.3 — the variable is ignored in both directions. Setting it here would be a
#   setting with nothing behind it, which is the one thing this file must not contain. pgjdbc's own default
#   is `prefer`, so both Java backends already negotiate TLS and never verify — the same posture as the
#   other three — and the server-side `rds.force_ssl = 1` in `rds.tf` is what makes "prefer" mean "always".
#   Stating it on the client for Java needs a JDBC-side knob (`sslmode` as a datasource property), whose
#   env-var spelling differs per framework and which nothing here can prove without a TLS Postgres and a
#   built application; `docs/aws-target.md` records that as the follow-up it is.
#
# Same posture on all five — encrypted, unverified — reached by three different routes because that is how
# many the drivers actually offer.
#
# `DATABASE_URL` is deliberately left alone, and that is the other half of the decision. It is one
# libpq-style string shared by all five backends (see `backends.MAVEN_TOOLING["migrate"]` for what that
# already costs Java), and an `sslmode` inside it would mean three different things at once:
# `pg-connection-string@2.14.0:77-79` turns *any* `sslmode` into TLS with Node's default
# `rejectUnauthorized: true` unless the non-libpq keyword `uselibpqcompat=true` is also in the string — and
# libpq rejects that keyword, so it cannot go in a URL the other backends read; and
# `pg@8.23.0/lib/connection-parameters.js:85` lets what it parsed from the string override `PGSSLMODE`
# outright, which would close off this route as well. So the URL stays the address and the credentials, and
# how the connection is protected is said once per backend, here.
#
# Real verification — `verify-full` with an `sslrootcert` — is the better end state and is not this table's
# job: the RDS CA bundle has to reach every image by a path that differs per builder (`/workspace/…` for
# Paketo, `$KO_DATA_PATH` for ko's distroless Go images) while the secret is shared by all of them. That is
# a decision with an ADR behind it, not a column here; the generated
# `docs/adr/0002-production-target.md` says as much where a reader will hit it.
# `None` is an answer, written out rather than left as a missing key: "this driver ignores the variable, and
# that was checked" is what the next reader needs, and an absent row would read as a backend nobody got to.
#
# The outer key is what the target *provisions the store as* rather than the target itself, because every
# reason above is a property of the managed Postgres and not of the cloud around it: `no-verify` is RDS's
# private Amazon root not being in Node's bundle, and a second cloud whose certificate chains to a root Node
# does bundle would answer differently for the same driver. So a second managed Postgres is a second block
# here, measured the same way, and never assumed from this one.
POSTGRES_SSLMODE: dict[str, dict[str, str | None]] = {
    "rds": {
        "typescript": "no-verify",
        "python": "require",
        "go": "require",
        "java-quarkus": None,
        "java-spring": None,
    },
    # **Not measured, and deliberately the conservative copy of the row above.** Azure Database for
    # PostgreSQL Flexible Server also refuses an unencrypted connection — `require_secure_transport` is on
    # by default — so every backend needs the same posture; what is not established is whether TypeScript
    # could have a *stronger* one here. RDS forced `no-verify` because its certificate chains to a private
    # Amazon root Node does not bundle; Flexible Server's chains to DigiCert Global Root G2 and Microsoft
    # RSA Root CA 2017, which Node does, so `require` — which node-postgres reads as *verify* — may well
    # connect and verify. That is a hypothesis about a certificate chain, not a fact about a driver, and
    # this table has never carried one of those.
    #
    # Every value here is safe as it stands: `no-verify` and `require` both encrypt, and neither can fail
    # where the other succeeds. What is owed is one run of node-postgres against a real Flexible Server. If
    # `require` connects, this row says `require` for TypeScript and the ADR loses a paragraph; until
    # somebody has run it, it says what is known to work.
    "flexible-server": {
        "typescript": "no-verify",
        "python": "require",
        "go": "require",
        "java-quarkus": None,
        "java-spring": None,
    },
}


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

# `project.toml` beside one service, for a backend whose `build` packs that directory alone. Keyed by the
# `descriptor` a builder declares, so a second backend that needs one is a row rather than a branch.
SERVICE_DESCRIPTORS = {
    "python": """# Read by `pack build --path <this directory>` (`make build`): what the upload leaves out.
#
# `uv.lock` is excluded deliberately, and `make build` exports its runtime half to `requirements.txt`
# first. The builder's Python group picks its package manager from what it finds, and a lock in the
# upload sends it to fetch uv from a GitHub release inside the build — a third host to be reachable, for
# a resolution this repository has already done. The exported file carries the same versions and their
# hashes. `.venv` is this machine's environment, for this machine's platform and interpreter; the image
# builds its own.
[_]
schema-version = "0.2"

[io.buildpacks]
exclude = ["uv.lock", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"]
""",
}


def tools_needed(backends: list[str]) -> list[str]:
    """The image-building tools the deploy workflow installs beyond each family's toolchain, once each."""
    return list(dict.fromkeys(IMAGE_BUILDERS[b]["tool"] for b in backends if IMAGE_BUILDERS[b]["tool"]))


def spelled(text: str, path: str, image: str, repository: str) -> str:
    """One recipe, for one service and one image reference."""
    return text.replace(APP, path).replace(IMAGE, image).replace(REPOSITORY, repository)
