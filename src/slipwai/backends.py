"""What every backend's toolchain shares, and the addresses every generated project agrees on.

The pins and tokens a backend's answers are written with, and the shape of its `tooling`. The answers
themselves — how a backend installs, migrates, runs and checks itself — are each language's, in
`project/languages/<language>_toolchain.py`, read through the registry (`registry.py`): one answer per
question rather than a conditional per call site, because the Makefile, the CI workflow, the Compose file
and the README all have to give the same one.
"""
from __future__ import annotations

from typing import NotRequired, TypedDict

# One version each, everywhere: the CI images in each language's toolchain, `setup-node` and `setup-python` in
# both generated workflows, `images.py`'s buildpacks, and the `.nvmrc` and `.python-version` a project is
# pinned with (`project/pins.py`). A second copy of a toolchain version is one that is already wrong somewhere.
NODE_MAJOR = 24
PYTHON_VERSION = "3.13"

# The uv a generated Python project is built against, pinned in the one place everything that installs it
# reads: the CI workflow's install step, the Compose container's setup line, and the message
# `scripts/verify` prints on a machine that has none. A laptop uses whatever uv it already has, exactly as
# it uses its own npm and its own Go — this pin is for the places where the keel does the installing.
UV_VERSION = "0.9.26"

# Where a backend's command says "this service's directory". Every recipe that names a service's path spells
# it with this token and is stamped per service by `tooling.for_app`, which is what lets one answer serve a
# project with any number of services — `apps/service` is the first one's path, not the answer's business.
APP = "__APP__"

# Where a backend's command says "this family's verify script". `scripts/verify` while a project has one
# language family; `scripts/verify-<family>` once it has several, with `scripts/verify` dispatching to each
# — see `tooling.verify_path`. Only Python's recipes run modes of their own script, so only they say it.
VERIFY = "__VERIFY__"


class Tooling(TypedDict):
    """What one backend's toolchain answers, read by the Makefile, the CI workflow and the Compose file.

    The shape of the `tooling` member of the backend protocol (`registry.py`), which each language answers in
    its `project/languages/<language>_toolchain.py`. One answer rather than three, because the Makefile, the
    CI workflow and the README all have to agree about how a project applies a migration, and three copies of
    that is three places for them to drift apart.

    `migrate` and `integration` are the language's answers to operations only a backing service asks for, and
    therefore the default for whichever feature declared it needs them. A feature that spells one differently
    — a store whose migrations its own CLI applies — answers it in the backend's `feature_tooling`, keyed by
    feature, and no call site learns its name (`tooling.app_tooling`). Empty everywhere today, which is the
    honest state rather than an omission: every feature that migrates does it through the language's runner.
    """

    install: str
    migrate: str
    integration: str
    ci_image: str
    ci_install: str
    container_setup: str
    container_environment: dict[str, str]
    #: The seed door: how a service appends the events a slice's `try-it.json` *gives* — `make seed-<service>
    #: FILE=<json>` runs it — through its own event-store port with a deterministic id, so a replay records
    #: nothing twice. Optional: a language whose skeleton has no door yet answers nothing, and a story's
    #: `given` is validated and not applied until it does (feedback-points plan, D4).
    seed: NotRequired[str]


# Where a toolchain writes what it installs, relative to the container: each backend's `compose_caches`
# answer, and a browser app's below. `make demo` mounts the checkout, so these paths get an anonymous volume
# each: a Linux container's installed dependencies landing in the host's working tree is how a demo breaks
# the native `make verify` that ran fine an hour earlier.
#
# Anonymous rather than named volumes because a named one needs a top-level `volumes:` declaration, and the
# only one this Compose file has lives inside the Postgres block deliberately (see the note there). These
# need no declaration and nothing outside the container needs to read them.
WEB_COMPOSE_CACHES = ("/workspace/node_modules", f"/workspace/{APP}/node_modules")


# The addresses the whole project agrees on. `.env.example` writes PORT, Compose publishes it, the browser app's
# dev server proxies to it, and the Makefile prints it — one number, named once. A demo has to be able to state
# its address in advance (see `commands/sail.md`), which it cannot do if four files each pick their own.
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
