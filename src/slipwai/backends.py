"""What differs per backend language, and the addresses every generated project agrees on.

One table per question rather than a conditional per call site: the Makefile, the CI workflow, the Compose
file and the README all have to give the same answer about how a backend installs, migrates and runs, and
three copies of that answer are three places for it to drift.
"""
from __future__ import annotations

from typing import TypedDict

from .naming import python_package_name

# Nothing here asks for an npm install: every npm recipe the Makefile writes takes the npm dependency target
# as a *prerequisite* (`project/shared_packages.NODE_DEPS`) rather than guarding itself.

# One version each, everywhere: the CI images below, `setup-node` and `setup-python` in both generated
# workflows, `images.py`'s buildpacks, and the `.nvmrc` and `.python-version` a project is pinned with
# (`project/pins.py`). A second copy of a toolchain version is one that is already wrong somewhere.
NODE_MAJOR = 24
PYTHON_VERSION = "3.13"

# The uv a generated Python project is built against, pinned in the one place everything that installs it
# reads: the CI workflow's install step, the Compose container's setup line, and the message
# `scripts/verify` prints on a machine that has none. A laptop uses whatever uv it already has, exactly as
# it uses its own npm and its own Go — this pin is for the places where the factory does the installing.
UV_VERSION = "0.9.26"

# Where a command below says "this service's directory". Every recipe that names a service's path spells
# it with this token and is stamped per service by `tooling.for_app`, which is what lets one table serve a
# project with any number of services — `apps/service` is the first one's path, not the table's business.
APP = "__APP__"

# Where a command below says "this family's verify script". `scripts/verify` while a project has one
# language family; `scripts/verify-<family>` once it has several, with `scripts/verify` dispatching to each
# — see `tooling.verify_path`. Only Python's recipes run modes of their own script, so only they say it.
VERIFY = "__VERIFY__"


# Every Maven invocation this factory writes, spelled once. `-B` because a recipe is never at a terminal
# and Maven's progress animation is noise in a CI log; `-q` because a passing gate should say nothing.
#
# `./mvnw`, not `mvn`. Maven was the one unpinned tool in a backend where Quarkus, Temurin, Checkstyle,
# PMD, SpotBugs, Error Prone and NullAway are all pinned exactly, and a wrapper is how this ecosystem
# spells that pin. The default wrapper genuinely cannot ship from here — it needs a `maven-wrapper.jar`
# beside the script and `assets/` is text or it is nothing — but `-Dtype=only-script` emits three text
# files and no jar, which is what `assets/languages/java/build/` carries — the language family's tree,
# shared by both Java backends, because a build wrapper belongs to Maven rather than to whatever owns
# startup above it.
#
# The download this adds is a distribution per `maven-wrapper.properties`, not per build:
# `actions/setup-java@v5` caches `~/.m2/wrapper/dists` under its own key derived from that file alone
# (`additionalCaches`, so `cache-dependency-path`'s pom does not rotate it), and `COMPOSE_CACHES` already
# holds the whole of `/root/.m2` for the containers. The fetch itself needs very little of an image: curl
# or wget, or failing both a `Downloader.java` the script compiles with the JDK, and it takes the `.tar.gz`
# where `unzip` is missing — which is what happens in `ci_image` below, and is proven by `make demo`.
MAVEN = f"cd {APP} && ./mvnw -B -q"

# Resolve and compile everything the gate will need, main and test alike. There is no `mvn install-deps`: in Maven,
# downloading dependencies is a side effect of needing them, so the honest spelling of "install" is the first build.
MAVEN_READY = f"{MAVEN} -DskipTests test-compile"

# What has to be installed inside `ci_image` before `make` can run there.
#
# Almost always nothing: `node:`, `python:` and `golang:` all ship GNU Make, so their containers run the
# same `make dev` a laptop does with no preamble. No official Maven or JDK image ships it — checked across
# `maven:*-eclipse-temurin-25`, its `-noble` and `-alpine` variants, and `eclipse-temurin:25-jdk` — so a
# Java container has to install it, and both places that run `make` inside a container need to know.
#
# A Dockerfile would be the other answer, and it is the wrong one here: `make demo` runs the checkout rather than a
# built image precisely so a demo can never be a stale copy of the code, and so there is no second definition of the
# app's layout to keep in step. One `apt-get` at container start is the cheaper side of that trade.
MAVEN_CONTAINER_SETUP = "apt-get update -qq && apt-get install -y -qq --no-install-recommends make"

# Where a containerised build writes, which for this backend has to be said in the environment rather than
# arranged with a volume.
#
# `MAVEN_ARGS` is applied to every `./mvnw` invocation in the container, and `service.build.dir` is the pom
# property the build directory is declared through — `project.build.directory` is read-only, so there is no
# way to move the output from the command line without that indirection. The path is outside `/workspace`,
# so nothing about the build touches the mounted checkout at all: no root-owned `target/`, and a host-side
# `make verify` still works immediately after `make demo`.
MAVEN_CONTAINER_ENVIRONMENT = {"MAVEN_ARGS": "-Dservice.build.dir=/tmp/service-build"}


# Which of a backend's own skeleton files have to arrive runnable. The toolkit's executable bit can be read
# off disk — `assets/toolkit/` is committed with it set, and everything there lands at the path it is
# committed at — but a language's skeleton is written under each service's directory, so its asset mode
# cannot answer a question asked about the generated path. That pair has to be stated, which is what this
# is — relative to the service, and stamped per service by `toolkit.executable_paths`.
#
# `mvnw` and not `mvnw.cmd`: the wrapper plugin marks only the shell script executable, and a `.cmd` has no
# use for the bit. A lost `chmod +x` is a fresh clone where every Maven goal reports "permission denied",
# so `tests/test_matrix.py` asserts the mode on the written file rather than trusting this table.
# One frozen set, named once and referenced by both Java backends rather than written out twice: the
# wrapper belongs to Maven, not to whatever owns startup above it, so the two siblings cannot disagree
# about it while they share a build tool. A sibling that built with Gradle would want its own entry here —
# `gradlew`, not `mvnw` — which is why this stays keyed by backend rather than by family.
MAVEN_EXECUTABLES = frozenset({f"{APP}/mvnw"})

BACKEND_EXECUTABLES = {
    "typescript": set(),
    "python": set(),
    # The gate scripts a Go service runs through; `project/languages/go.py` writes them, `project/mutation.py` says why.
    "go": frozenset({"scripts/go-coverage.py", "scripts/go-mutation.py"}),
    "java-quarkus": MAVEN_EXECUTABLES,
    "java-spring": MAVEN_EXECUTABLES,
}


class Tooling(TypedDict):
    """What one backend's toolchain answers, read by the Makefile, the CI workflow and the Compose file."""

    install: str
    migrate: str
    integration: str
    ci_image: str
    ci_install: str
    container_setup: str
    container_environment: dict[str, str]


# Named once and shared by both Java backends below, because every answer in it is Maven's rather than
# the framework's: the same wrapper resolves, the same `exec:java` migrates, the same Failsafe goals run
# the integration suite, and the same image carries all of it. Where the two genuinely differ is
# `dev_command`, which is a table of its own further down. Writing these eight fields out twice would
# work on the day it was written and be two places to fix afterwards.
MAVEN_TOOLING: Tooling = {
    "install": MAVEN_READY,
    # Flyway's own Maven plugin is not what runs this, and the reason is the URL shape: every other
    # backend here reads the libpq-style `DATABASE_URL`, while JDBC needs `jdbc:postgresql://…` with the
    # credentials supplied apart from the host. Something has to translate, and doing it in a Make
    # recipe would put a second parser beside the one `config/DatabaseUrl.java` already has — two
    # parsers for one URL, drifting in a way no gate would catch. So the command runs a main that calls
    # Flyway through that single parser. Flyway still owns everything a migration runner is: the
    # ordering by `V<n>__`, the `flyway_schema_history` ledger, and applying each file in one
    # transaction. `<mainClass>` is configured in the pom rather than named here, because the package
    # carries this project's own name and the Makefile does not know it.
    "migrate": f"{MAVEN} -DskipTests compile exec:java",
    # Failsafe rather than Surefire, which is the whole `*Test` / `*IT` split: `make verify` runs
    # Surefire and never compiles a database into the gate. Invoked as goals rather than through
    # `verify`, so this target runs the integration suite and only that.
    "integration": f"{MAVEN} test-compile failsafe:integration-test failsafe:verify",
    "ci_image": "maven:3.9.16-eclipse-temurin-25-noble",
    "ci_install": MAVEN_READY,
    "container_setup": MAVEN_CONTAINER_SETUP,
    "container_environment": MAVEN_CONTAINER_ENVIRONMENT,
}


# What each backend calls the operations a backing service adds. One table because the Makefile, the CI
# workflow and the README all have to agree about them, and three copies of "how does a Go project apply a
# migration" is three places for them to drift apart.
BACKEND_TOOLING: dict[str, Tooling] = {
    "typescript": {
        # The answer is owed and is this, but no recipe runs it: a target of this family's takes the npm
        # dependency target as a prerequisite instead (`project/shared_packages.npm_dependency`).
        "install": "npm ci",
        "migrate": f"npm --workspace {APP} run migrate",
        "integration": f"npm --workspace {APP} run test:integration",
        "ci_image": f"node:{NODE_MAJOR}-bookworm",
        "ci_install": "npm ci",
        "container_setup": "",
        "container_environment": {},
    },
    "python": {
        "install": f"./{VERIFY} --install-only",
        "migrate": f"./{VERIFY} --migrate",
        "integration": f"./{VERIFY} --integration-only",
        "ci_image": f"python:{PYTHON_VERSION}-bookworm",
        "ci_install": f"./{VERIFY} --install-only",
        # uv is this backend's toolchain and the official Python images do not ship it, so the two places
        # that run `make` inside one install it first — at the pin above, from PyPI, which is the one
        # registry these jobs already ask anything of.
        "container_setup": f"python3 -m pip install --disable-pip-version-check -q uv=={UV_VERSION}",
        "container_environment": {},
    },
    "go": {
        "install": f"cd {APP} && go mod download",
        "migrate": f"cd {APP} && go run ./cmd/migrate",
        "integration": f"cd {APP} && go test -tags=integration ./...",
        "ci_image": "golang:1.26-bookworm",
        "ci_install": f"cd {APP} && go mod download",
        "container_setup": "",
        "container_environment": {},
    },
    "java-quarkus": MAVEN_TOOLING,
    "java-spring": MAVEN_TOOLING,
}


# What one *feature* spells differently from the language it runs inside. `migrate` and `integration` above
# are the language's answers to operations only a backing service asks for, and they are therefore the
# default for whichever feature declared it needs them: a per-language default with a per-(language,
# feature) override, rather than a fourth key nobody could name — see `tooling.app_tooling`.
#
# Empty, and that is the honest state rather than an omission — every feature that migrates today does it
# through the language's own runner. A store whose migrations are applied by its own CLI adds a row here,
# keyed language then feature, and no call site learns its name.
FEATURE_TOOLING: dict[str, dict[str, dict[str, str]]] = {}


# Where each backend's toolchain writes what it installs, relative to the container. `make demo` mounts the
# checkout, so these paths get an anonymous volume each: a Linux container's installed dependencies landing
# in the host's working tree is how a demo breaks the native `make verify` that ran fine an hour earlier.
#
# Anonymous rather than named volumes because a named one needs a top-level `volumes:` declaration, and the
# only one this Compose file has lives inside the Postgres block deliberately (see the note there). These
# need no declaration and nothing outside the container needs to read them.
# Maven's, shared by both Java backends: where a dependency cache lives is the build tool's answer, and
# neither framework moves it.
MAVEN_COMPOSE_CACHES = ("/root/.m2",)

COMPOSE_CACHES = {
    "typescript": (
        "/workspace/node_modules",
        f"/workspace/{APP}/node_modules",
        f"/workspace/{APP}/.build",
    ),
    # The environment `uv sync` builds beside each service, and uv's own download cache above them.
    "python": (f"/workspace/{APP}/.venv", "/root/.cache/uv"),
    "go": ("/root/go", "/root/.cache"),
    # Only `~/.m2`, which sits outside the mounted checkout and so is exactly what an anonymous volume is
    # for. The build output is handled the other way — see MAVEN_CONTAINER_ENVIRONMENT. Masking
    # a service's `target/` with a volume keeps the class files out of the host tree but still
    # has Docker create the mount point on the host, owned by root, and the next host-side `./mvnw` then
    # fails with a permission error nowhere near its cause.
    "java-quarkus": MAVEN_COMPOSE_CACHES,
    "java-spring": MAVEN_COMPOSE_CACHES,
}


WEB_COMPOSE_CACHES = ("/workspace/node_modules", f"/workspace/{APP}/node_modules")


# The addresses the whole project agrees on. `.env.example` writes PORT, Compose publishes it, the Vite dev
# server proxies to it, and the Makefile prints it — one number, named once. A demo has to be able to state
# its address in advance (see `commands/drive.md`), which it cannot do if four files each pick their own.
SERVICE_PORT = 3000
WEB_PORT = 5173

# Which features contribute keys to `.env.example`. A project whose selection contributes none gets no
# environment template at all, which is the difference between "nothing to configure" and "an empty file
# implying there is".
ENV_FEATURES = {
    "postgres",
    "sqlite",
    "keycloak",
    "users-keycloak",
    "fastify",
    "fastapi",
    "net-http",
    "quarkus-rest",
    "spring-web",
}


def dev_command(backend: str, qualifier: str, path: str, verify: str = "scripts/verify") -> str:
    """How this backend starts one service in the foreground.

    One table rather than three scattered strings, because Compose runs the very same `make dev` inside a
    container: if the demo path and the local path were spelled separately they would drift, and the way
    that failure presents is a demo that works for whoever wrote it. `qualifier` is what the service's
    package is named after (`tooling.service_qualifier`), `path` where it lives. `LOG_FORMAT=pretty` is
    set here and in TypeScript's `dev` script; every other way of starting one gets JSON.
    """
    return {
        "typescript": f"npm --workspace {path} run dev",
        "python": f"./{verify} --install-only\n\tLOG_FORMAT=pretty PYTHONPATH={path}/src "
        f"uv run --project {path} --no-sync python -m {python_package_name(qualifier)}.main",
        "go": f"cd {path} && LOG_FORMAT=pretty go run ./cmd/serve",
        # Quarkus dev mode, which is the reason to reach for `make dev` at all: it recompiles and reloads on
        # the next request, so an edit is visible without restarting anything. It reads HOST and PORT
        # through `application.properties`, so the container and the laptop are configured the same way.
        "java-quarkus": f"{MAVEN.replace(APP, path)} quarkus:dev",
        # The Spring Boot plugin's own run goal, which compiles first and then runs the application from
        # the exploded classes — so `./mvnw compile` in a second terminal is picked up. That is a weaker
        # reload than its sibling's, and honestly so: Quarkus recompiles on the next request by itself,
        # whereas this is Spring Boot without `spring-boot-devtools`, which is not a dependency here
        # because it also restarts on every classpath change a container mount produces. Reads HOST and
        # PORT through `application.properties`, so the container and the laptop are configured the same
        # way.
        "java-spring": f"{MAVEN.replace(APP, path)} spring-boot:run",
    }[backend]


# Where a Maven project's driven adapters live, for prose that has to point at them. Shared, because
# `src/main/java` is the build tool's convention and neither framework moves it.
MAVEN_DRIVEN_ADAPTERS = f"{APP}/src/main/java/com/example/<package>/adapters/driven/"


def event_store_directory(backend: str, path: str) -> str:
    """Where one service's driven adapters live, for prose that has to point at them."""
    return {
        "typescript": f"{APP}/src/adapters/driven/",
        "python": f"{APP}/src/<package>/adapters/driven/",
        "go": f"{APP}/adapters/driven/",
        # Both Java backends, because this is Maven's source layout rather than a framework's.
        "java-quarkus": MAVEN_DRIVEN_ADAPTERS,
        "java-spring": MAVEN_DRIVEN_ADAPTERS,
    }[backend].replace(APP, path)
