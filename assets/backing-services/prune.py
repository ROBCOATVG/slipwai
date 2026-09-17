#!/usr/bin/env python3
"""Prune this project's backing services down to the ones it actually uses.

This file has two lives, deliberately from one copy. The factory imports it to cut a generated project down
to what was selected at generation time, and the generated project carries it as
`scripts/backing-services.py` so `./init` can cut it down further. A second implementation of the same
pruning would be a second set of bugs.

Every question is asked as an **axis** — the role being filled — rather than as a product name:

    scripts/backing-services.py --list
    scripts/backing-services.py --event-store memory     # drop the real store, keep the in-memory one
    scripts/backing-services.py --http none              # drop the inbound HTTP transport
    scripts/backing-services.py --auth none              # drop the staff realm and its adapter
    scripts/backing-services.py --users none             # drop the customers realm, the browser login and its adapter

An axis offers only what is still on disk. A project generated with SQLite can drop to memory but cannot
become a Postgres project: pruning only ever subtracts, and the factory already cut the branch it was not
asked for. `--list` shows what each axis can still be answered with in *this* project.

Naming a selection is a one-way prune: it deletes files and strips the markers. Nothing is committed, so
`git checkout .` before your first commit undoes it.

Regions inside a shared file are delimited by `backing-service:<feature>:begin` / `:end` marker comments
rather than parsed out of each host language. A region two features both need — the one Keycloak container
that serves the staff realm and the customers realm — names both, `backing-service:keycloak|users-keycloak`,
and stays while either remains. That is not laziness: pruning Compose YAML by indentation
looks easy and is not — a two-space key means different things in different sections, `  postgres-data:`
under `volumes:` looks exactly like `  postgres:` under `services:`, and treating it as a service leaves
`volumes:` with nothing under it, which Compose rejects outright. A marker says what the author meant, in
every file, and the author is the only one who knows.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Every marker feature this script knows how to prune. A feature owns files and marked regions; an axis
# option is answered *with* a set of features. The factory asserts this tuple against its catalog.
FEATURES = (
    "fastapi",
    "fastify",
    "keycloak",
    "net-http",
    "postgres",
    "quarkus-rest",
    "spring-web",
    "sqlite",
    "users-keycloak",
)

# Every language family this script knows the layout of. Families rather than backends, because
# `project_services` reads each service's `language` from `project.json`, and every table keyed by it
# below is keyed that way too — per service, since a project's services need not share a language.
#
# Java now has two frameworks, and they turned out to agree about almost all of this: the same marked
# files, the same source layout, the same empty `PACKAGE_EDITS` (their dependencies live in marked pom
# regions, so there is nothing for a package manager to uninstall). They disagree in exactly one place —
# which registration file the datasource configuration is found through — and that is handled by naming
# both paths where they appear, since a prune of a path this project does not have is a no-op. A family
# whose members disagreed about something a no-op could not cover would rekey the table that differs to
# `project.json`'s `backend`, which the factory already writes beside `language`; nothing needs that yet.
# The factory asserts this tuple against its catalog.
LANGUAGES = ("typescript", "python", "go", "java")

# The axes, and which features each answer keeps. An option is offerable in a given project only when every
# feature it needs is still on disk, which is what makes "you may drop to memory, you may not upgrade to
# Postgres" fall out of the data rather than out of a special case.
#
# `notes` is the consequence of the answer, printed when it is chosen and by `--list`. It is prose rather
# than a doc link on purpose: the moment somebody drops the real event store is the moment they need to be
# told what stopped being provable.
#
# `targets` is where an option is offered — the production targets, as `project.json` records this
# project's under `target`. The factory filtered the menu by it at generation time and this script filters
# the same way afterwards, so an answer a project's target cannot carry is refused here too rather than
# pruned into. SQLite is local-only (the file dies with the task), Keycloak is local-only (Cognito is its
# answer in the cloud), and Cognito is offered under `aws` alone.
#
# `capabilities` is what the answer gives the project — the same list `catalog.json` declares on the option
# and the generator writes into `project.json` per deployable, which is why `record_answers` can swap one
# for another rather than recomputing a project's capabilities from a second copy of the rules. Mirrored
# like `features` and `targets`, and the factory asserts the three agree with the catalog.
AXES: dict[str, dict] = {
    "event-store": {
        "prompt": "Event store",
        "options": {
            "postgres": {
                "capabilities": ("event-store-postgres",),
                "features": ("postgres",),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "Postgres — append-only table, unique (stream, version) as the concurrency control",
                "note": (
                    "Postgres is what makes the never-write-the-same-version-twice guarantee provable: "
                    "`make test-integration` races two appends at one version and requires exactly one "
                    "winner."
                ),
            },
            "sqlite": {
                "capabilities": ("event-store-sqlite",),
                "features": ("sqlite",),
                "targets": ("none", "existing"),
                "label": "SQLite — a real append-only log in one file, no container",
                "note": (
                    "SQLite serialises writers, so it proves durability and the append-only rule but NOT "
                    "concurrent behaviour: it cannot race. Move to Postgres before believing any "
                    "concurrency test."
                ),
            },
            "memory": {
                "capabilities": ("event-store-memory",),
                "features": (),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "In-memory only — zero infrastructure, loses all truth on restart",
                "note": (
                    "In-memory only. Nothing survives a restart, and the concurrency guarantee is NOT "
                    "provable on it — being single-threaded it cannot race. Demos only."
                ),
            },
        },
    },
    "http": {
        "prompt": "Inbound HTTP transport",
        "options": {
            "fastify": {
                "capabilities": ("http-fastify",),
                "features": ("fastify",),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "Fastify — JSON API, schema-parsed at the edge",
                "note": "",
            },
            "fastapi": {
                "capabilities": ("http-fastapi",),
                "features": ("fastapi",),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "FastAPI — JSON API on ASGI, schema-parsed at the edge",
                "note": "",
            },
            "net-http": {
                "capabilities": ("http-net-http",),
                "features": ("net-http",),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "net/http — standard-library JSON API, no framework dependency",
                "note": "",
            },
            "quarkus-rest": {
                "capabilities": ("http-quarkus-rest",),
                "features": ("quarkus-rest",),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "Quarkus REST — JSON API on the framework's own HTTP layer, with SmallRye Health "
                         "serving the readiness probe",
                "note": (
                    "Dropping this drops SmallRye Health with it, so the project loses its readiness "
                    "probe as well as its routes — there is no hand-written /health to fall back to, "
                    "on purpose."
                ),
            },
            "spring-web": {
                "capabilities": ("http-spring-web",),
                "features": ("spring-web",),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "Spring MVC — JSON API on Tomcat over virtual threads, with Actuator serving "
                         "the readiness probe",
                "note": (
                    "Dropping this drops Actuator with it, so the project loses its readiness probe as "
                    "well as its routes — there is no hand-written /health to fall back to, on purpose."
                ),
            },
            "none": {
                "capabilities": (),
                "features": (),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "None — library or worker only, no inbound HTTP",
                "note": (
                    "With no external interface, boundary-level scenarios must bind to whatever the real "
                    "entry point becomes (a CLI, a queue consumer). Decide that before writing acceptance "
                    "tests."
                ),
            },
        },
    },
    "auth": {
        "prompt": "Staff authentication",
        "options": {
            "cognito": {
                "capabilities": ("auth-cognito",),
                "features": ("keycloak",),
                "targets": ("aws",),
                "label": "Cognito — a user pool provisioned in AWS; Keycloak is the local stand-in, same "
                         "groups and OIDC_* keys",
                # The same files as Keycloak's, on purpose: what a Cognito project carries locally *is* the
                # Keycloak stand-in — realm, container, group mapping — and `infra/` is where the pool is.
                # Dropping the answer drops both, which is why the two share a feature.
                "note": (
                    "Scaffolded: the Cognito user pool, hosted login domain, groups and confidential client in "
                    "infra/service, and Keycloak locally with the same groups. The protocol flow is the "
                    "ecosystem's maintained client where the backend has one and deliberately unwritten where "
                    "it does not — read the auth adapter's own note, and load the secure-oauth-oidc skill before "
                    "writing any part of it yourself. Cognito puts groups in the `cognito:groups` claim; "
                    "OIDC_GROUPS_CLAIM names it."
                ),
            },
            "entra": {
                "capabilities": ("auth-entra",),
                "features": ("keycloak",),
                "targets": ("azure",),
                "label": "Entra ID — an app registration provisioned in Azure; Keycloak is the local "
                         "stand-in, same groups and OIDC_* keys",
                # The same files as Keycloak's, on purpose: what an Entra ID project carries locally *is*
                # the Keycloak stand-in — realm, container, group mapping — and `infra/` is where the app
                # registration is. Dropping the answer drops both, which is why the two share a feature.
                "note": (
                    "Scaffolded: the Entra ID app registration, the staff groups and a confidential client in "
                    "infra/service, and Keycloak locally with the same groups. The protocol flow is the "
                    "ecosystem's maintained client where the backend has one and deliberately unwritten where "
                    "it does not — read the auth adapter's own note, and load the secure-oauth-oidc skill before "
                    "writing any part of it yourself. Entra puts groups in the `groups` claim; "
                    "OIDC_GROUPS_CLAIM names it."
                ),
            },
            "auth0": {
                "capabilities": ("auth-auth0",),
                "features": ("keycloak",),
                "targets": ("aws", "azure"),
                "label": "Auth0 — an application and the staff roles provisioned through Auth0's own "
                         "Management API, from either cloud; Keycloak is the local stand-in, same groups "
                         "and OIDC_* keys",
                # The same files as Keycloak's, for the reason the two rows above share them: what an
                # Auth0 project carries locally *is* the Keycloak stand-in, and `infra/` is where the
                # tenant's own objects are. Unlike those two, they are not created by the cloud
                # credential — `infra/service/auth0.tf` says what that costs.
                "note": (
                    "Scaffolded: the Auth0 application, the API that names the audience, the staff roles and "
                    "the post-login action that puts them in the token, in infra/service, and Keycloak locally "
                    "with the same groups. The protocol flow is the ecosystem's maintained client where the "
                    "backend has one and deliberately unwritten where it does not — read the auth adapter's own "
                    "note, and load the secure-oauth-oidc skill before writing any part of it yourself. Auth0 "
                    "puts no roles in a token by default; the action adds a namespaced claim and "
                    "OIDC_GROUPS_CLAIM names it."
                ),
            },
            "keycloak": {
                "capabilities": ("auth-keycloak",),
                "features": ("keycloak",),
                "targets": ("none", "existing"),
                "label": "Keycloak — container, realm and group mapping scaffolded",
                # Deliberately says less than it used to about the flow, because the honest answer differs
                # per backend and this script is one file shared by all of them: where a framework owns
                # startup the flow comes from its OIDC client, and where nothing does it is left unwritten.
                # A note that named only the second case told a Quarkus project to hand-roll a flow it
                # already has — which is the one mistake this text most needs not to make.
                "note": (
                    "Scaffolded: the container, the realm, and the group-to-role mapping. The protocol "
                    "flow is the ecosystem's maintained client where the backend has one and deliberately "
                    "unwritten where it does not — read the auth adapter's own note, and load the "
                    "secure-oauth-oidc skill before writing any part of it yourself."
                ),
            },
            "none": {
                "capabilities": (),
                "features": (),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "None — no staff identity yet",
                "note": (
                    "No identity provider, so anything you build has no authentication. Keep authorisation "
                    "decisions in use cases anyway, so wiring a provider later is a change of adapter and "
                    "nothing more."
                ),
            },
        },
    },
    "users": {
        "prompt": "Customer authentication",
        "options": {
            "cognito": {
                "capabilities": ("users-cognito",),
                "features": ("users-keycloak",),
                "targets": ("aws",),
                "label": "Cognito — a second user pool for the product's users, provisioned in AWS; Keycloak's "
                         "customers realm is the local stand-in",
                "note": (
                    "Scaffolded: a user pool with self-registration and a public PKCE client in infra/service, "
                    "the customers realm in Keycloak locally, the browser app's login through a maintained "
                    "client, and the customer adapter in each service. Token validation is the framework's where "
                    "one owns startup and deliberately unwritten where none does. Cognito access tokens carry the "
                    "client id in `client_id` rather than `aud`; read the users adapter's note before trusting "
                    "an audience check written against Keycloak."
                ),
            },
            "auth0": {
                "capabilities": ("users-auth0",),
                "features": ("users-keycloak",),
                "targets": ("aws", "azure"),
                "label": "Auth0 — a database connection with self-registration and a public PKCE client, "
                         "provisioned through Auth0's own Management API, from either cloud; Keycloak's "
                         "customers realm is the local stand-in",
                "note": (
                    "Scaffolded: an Auth0 database connection with self-registration and password reset, the "
                    "API that names the audience and a public PKCE client in infra/service, the customers realm "
                    "in Keycloak locally, the browser app's login through a maintained client, and the customer "
                    "adapter in each service. Token validation is the framework's where one owns startup and "
                    "deliberately unwritten where none does. An Auth0 access token carries the API identifier in "
                    "`aud`, exactly as Keycloak's does, so an audience check written against the stand-in is "
                    "right against the real thing — which is not true of the Cognito row above."
                ),
            },
            "keycloak": {
                "capabilities": ("users-keycloak",),
                "features": ("users-keycloak",),
                "targets": ("none", "existing"),
                "label": "Keycloak — a customers realm beside the staff one, the browser login and the customer "
                         "adapter scaffolded",
                "note": (
                    "Scaffolded: a second realm in the same Keycloak, with self-registration, password reset "
                    "and a public PKCE client; the browser app's login, session and renewal through a "
                    "maintained client; and the customer adapter in each service. Token validation is the "
                    "framework's where one owns startup and deliberately unwritten where none does — read the "
                    "users adapter's own note, and load the secure-oauth-oidc skill before writing any of it "
                    "yourself."
                ),
            },
            "none": {
                "capabilities": (),
                "features": (),
                "targets": ("none", "existing", "aws", "azure"),
                "label": "None — no customer accounts yet",
                "note": (
                    "Nobody outside the organisation can sign in, so nothing you build has a customer. Keep "
                    "per-account authorisation in use cases anyway, so wiring a provider later is a change of "
                    "adapter and nothing more."
                ),
            },
        },
    },
}

# Axes a production target will not take the "none" answer to. `aws` deploys an HTTP service and proves a
# deploy by asking it for /health, so `--http none` is refused in a project going there — the factory refused
# it at generation time, and a later prune has to refuse it for the same reason. Mirrored from the catalog,
# and the factory asserts the two agree.
TARGET_REQUIRES: dict[str, tuple[str, ...]] = {"aws": ("http",), "azure": ("http",)}

# Axes whose non-"none" answer needs another axis to be answered too. The factory refuses these
# combinations at generation time; a later prune has to refuse them for the same reason, or
# `--http none` on a project with Keycloak would leave an auth adapter with no transport and six
# OIDC values the project reads and cannot use. `REQUIRES_BECAUSE` is the sentence the refusal prints,
# per axis, because the reason is the axis's own.
REQUIRES: dict[str, tuple[str, ...]] = {"auth": ("http",), "users": ("http",)}
REQUIRES_BECAUSE: dict[str, str] = {
    "auth": (
        "The authorization-code flow needs an inbound entry point to receive its redirect, so an identity "
        "provider whose adapter has no transport leaves configuration the project reads and cannot use."
    ),
    "users": (
        "A customer signs in from the browser and then presents the token to the service over HTTP, so a "
        "customer adapter with no transport has nothing to validate and configuration nothing reads."
    ),
}

# Files that may carry marker regions. A file listed here and missing is fine; a marked region in a file NOT
# listed here is silently never pruned, so add the file when you add the region. These are the repository's
# own; the per-language table below is relative to a service's directory and is applied to every service
# `project.json` lists.
# The factory's own material — placed under `layout.delivery` where a project records one (`placed`).
DELIVERY_ROOTS = ("Makefile", "init", "scripts", "skills", "commands", "docs")
MARKED_FILES: tuple[str, ...] = (
    "docker-compose.yml",
    "Makefile",
    ".env.example",
    ".github/workflows/verify.yml",
    "README.md",
    "AGENTS.md",
    "docs/gates.md",
    # One README for the one Keycloak container, a section per realm; see SHARED_FILES for who owns it.
    "docker/keycloak/README.md",
    # The production target's stack, where a store or an identity provider is provisioned inside the region
    # of the answer that asked for it. Absent in a local-only project, which is fine: a listed file that is
    # missing is skipped.
    "infra/service/main.tf",
    "infra/service/rds.tf",
    "infra/service/cognito_staff.tf",
    "infra/service/cognito_customers.tf",
    # The one output both clouds assemble from whichever customer-identity answer was given, so the merge
    # has a region per contributor and an answer taken away takes its line with it.
    "infra/service/outputs.tf",
    # The same, for the other cloud. A file listed here that is missing is skipped, so one list serves
    # every target and a project carries only its own.
    "infra/service/postgres.tf",
    "infra/service/entra_staff.tf",
    # The third identity answer, and the only one written as a whole file rather than a region of one: the
    # Auth0 provider cannot configure itself without a tenant credential, so a project that did not choose
    # it carries `no-auth0.tf` under this name instead, whose regions are the same and hold nothing.
    "infra/service/auth0.tf",
    # The one region outside a service stack: the Graph permission the pipeline needs to create an app
    # registration, which goes with the answer that needs one rather than with the target.
    "infra/bootstrap/main.tf",
)

# Relative to a browser app, and applied to every one `project.json` lists. In a list of its own rather than
# the per-language one because a browser app is TypeScript whatever its service is written in. Its
# dev-server proxy is marked with the transport it forwards to, so dropping the transport drops it, and
# its entry point wraps the app in the customer login when the project has one.
# `src/App.tsx` carries the route that shows this project's own API answering, marked with the transport
# it calls — a project with no transport has no API to show.
MARKED_FILES_PER_WEB_APP: tuple[str, ...] = (
    "vite.config.ts",
    "src/main.tsx",
    "src/App.tsx",
    "tests/App.test.tsx",
)

# Patterns may glob, exactly as `OWNED_FILES` below does and for the same reason: a Python service's
# package directory is named after the project, so its entry point cannot be written literally here.
MARKED_FILES_BY_LANGUAGE: dict[str, tuple[str, ...]] = {
    # Two files on every one of these lists carry a region for the same answer. The environment's one
    # schema — `src/config.ts`, `settings.py`, the `config` package — holds each backing service's
    # variables inside that service's region, so a variable goes when the adapter that reads it does; and
    # the *entry point* is the composition root, the one file that names the store this project answered
    # the event-store question with, so the region that opens that store goes with the adapter too.
    "typescript": ("vitest.config.ts", "tsconfig.json", "src/config.ts", "src/main.ts"),
    # Globs because a Python service's package directory is named after the project.
    "python": ("src/*/settings.py", "src/*/main.py"),
    "go": ("config/config.go", "cmd/serve/main.go"),
    # Java's per-feature dependencies live in marked regions of the pom rather than in PACKAGE_EDITS
    # below, and `application.properties` carries the configuration that reads them. Both are XML- and
    # properties-comment marked, so one mechanism removes a dependency and its configuration together.
    "java": ("pom.xml", "src/main/resources/application.properties"),
}

# Files that exist only because a feature was selected, relative to a service's directory — `owned_paths`
# resolves each pattern under every service in `project.json`, so a second service's adapters are pruned
# exactly as the first's are. Patterns may glob, which is how the Python entries reach inside a package
# directory named after the project. The `any` rows are repository-level and relative to the root.
OWNED_FILES: dict[str, dict[str, tuple[str, ...]]] = {
    "sqlite": {
        "typescript": (
            "src/adapters/driven/event-store-sqlite.ts",
            "src/adapters/driven/checkpoint-store-sqlite.ts",
            "tests/contract/event-store-sqlite.test.ts",
            "tests/contract/checkpoint-store-sqlite.test.ts",
        ),
        "python": (
            "src/*/adapters/driven/event_store_sqlite.py",
            "src/*/adapters/driven/checkpoint_store_sqlite.py",
            "tests/contract/test_event_store_sqlite.py",
            "tests/contract/test_checkpoint_store_sqlite.py",
        ),
        "go": (
            "adapters/driven/eventstoresqlite",
            "adapters/driven/checkpointstoresqlite",
        ),
        "java": (
            "src/main/java/com/example/*/adapters/driven/eventstoresqlite",
            "src/test/java/com/example/*/adapters/driven/eventstoresqlite",
            "src/main/java/com/example/*/adapters/driven/checkpointstoresqlite",
            "src/test/java/com/example/*/adapters/driven/checkpointstoresqlite",
        ),
    },
    "postgres": {
        "typescript": (
            "src/adapters/driven/event-store-postgres/index.ts",
            "src/adapters/driven/event-store-postgres/checkpoint-store-postgres.ts",
            "migrations/001_events.js",
            "migrations/002_events_append_only.js",
            "migrations/003_projection_checkpoints.js",
            "migrations/004_event_tags.js",
            "tests/integration/event-store-postgres.test.ts",
            "tests/integration/checkpoint-store-postgres.test.ts",
            "vitest.integration.config.ts",
        ),
        "python": (
            "src/*/adapters/driven/event_store_postgres.py",
            "src/*/adapters/driven/checkpoint_store_postgres.py",
            "migrations/apply.py",
            "migrations/001_events.sql",
            "migrations/002_events_append_only.sql",
            "migrations/003_projection_checkpoints.sql",
            "migrations/004_event_tags.sql",
            "tests/integration/test_event_store_postgres.py",
            "tests/integration/test_checkpoint_store_postgres.py",
        ),
        "go": (
            "adapters/driven/eventstorepostgres",
            "adapters/driven/checkpointstorepostgres",
            "cmd/migrate",
            # embed.go (+ keep) is what puts the .sql files into the ko-built migrate image; without
            # it the command reads an empty working directory even when the repository has .sql files.
            "migrations/embed.go",
            "migrations/keep",
            "migrations/001_events.sql",
            "migrations/002_events_append_only.sql",
            "migrations/003_projection_checkpoints.sql",
            "migrations/004_event_tags.sql",
        ),
        "java": (
            "src/main/java/com/example/*/adapters/driven/eventstorepostgres",
            "src/test/java/com/example/*/adapters/driven/eventstorepostgres",
            "src/main/java/com/example/*/adapters/driven/checkpointstorepostgres",
            "src/test/java/com/example/*/adapters/driven/checkpointstorepostgres",
            # The transaction seam and the framework bean behind it. Only the SQL store needs it: the
            # in-memory adapter is one lock and SQLite is one connection, so a project that keeps
            # neither Postgres adapter has nothing to hand it to.
            "src/main/java/com/example/*/adapters/driven/sql",
            "src/main/java/com/example/*/config",
            "src/test/java/com/example/*/config",
            "src/main/java/com/example/*/migrations",
            "src/main/resources/db",
            # One of these per backend, never both: the datasource learns its address through a
            # MicroProfile `ConfigSource` under Quarkus and a Spring `EnvironmentPostProcessor` under
            # Spring Boot, and each framework finds its own through a registration file whose name is
            # fixed by the interface. Both are named here because a prune of a path this project does not
            # have is a no-op, which is cheaper and more readable than keying this whole table by backend
            # for one line.
            "src/main/resources/META-INF/services",
            "src/main/resources/META-INF/spring",
        ),
    },
    "fastify": {
        "typescript": (
            "src/adapters/driving/http/app.ts",
            "src/config.ts",
            "src/tracing.ts",
            "src/main.ts",
            "src/openapi.ts",
            "openapi.json",
            "tests/edge/http-app.test.ts",
            "tests/edge/tracing.test.ts",
        ),
        "python": (),
        "go": (),
        # And the typed client the browser app generates from this transport's published document:
        # with the document gone there is nothing to generate from, and a package whose build points
        # at a file that is not there fails every target `build-packages` is a prerequisite of.
        "any": ("packages/api-client",),
        "java": (),
    },
    "net-http": {
        "typescript": (),
        "python": (),
        "go": (
            "adapters/driving/http/app.go",
            "adapters/driving/http/app_test.go",
            "adapters/driving/http/security.go",
            "adapters/driving/http/security_test.go",
            "adapters/driving/http/openapi_test.go",
            "openapi.yaml",
            "config",
            "observability",
            "cmd/serve",
        ),
        # And the typed client the browser app generates from this transport's published document:
        # with the document gone there is nothing to generate from, and a package whose build points
        # at a file that is not there fails every target `build-packages` is a prerequisite of.
        "any": ("packages/api-client",),
        "java": (),
    },
    # Named for its own files rather than a whole directory, because the auth adapter lives *under*
    # `driving/http/` and dropping the transport must not take a Keycloak adapter with it — the axes are
    # independent, and `REQUIRES` is what refuses that combination instead.
    "quarkus-rest": {
        "typescript": (),
        "python": (),
        "go": (),
        "java": (
            "src/main/java/com/example/*/adapters/driving/http/SchemaFailure.java",
            "src/main/java/com/example/*/adapters/driving/http/NotFoundMapper.java",
            "src/main/java/com/example/*/adapters/driving/http/ServiceHealthCheck.java",
            "src/test/java/com/example/*/adapters/driving/http/HttpAppTest.java",
        ),
    },
    # Its sibling's twin, and named file by file for the same reason: the auth adapter lives *under*
    # `driving/http/`, so dropping the transport must not take a Keycloak adapter with it.
    "spring-web": {
        "typescript": (),
        "python": (),
        "go": (),
        "java": (
            "src/main/java/com/example/*/adapters/driving/http/SchemaFailure.java",
            "src/main/java/com/example/*/adapters/driving/http/NotFoundAdvice.java",
            "src/main/java/com/example/*/adapters/driving/http/"
            "ServiceHealthIndicator.java",
            "src/test/java/com/example/*/adapters/driving/http/HttpAppTest.java",
        ),
    },
    "fastapi": {
        "typescript": (),
        "python": (
            "src/*/adapters/driving/http/app.py",
            "src/*/main.py",
            "src/*/logging_setup.py",
            "src/*/settings.py",
            "src/*/tracing.py",
            "src/*/openapi.py",
            "openapi.json",
            "tests/edge/test_http_app.py",
            "tests/test_logging_setup.py",
            "tests/test_settings.py",
            "tests/test_tracing.py",
        ),
        "go": (),
        # And the typed client the browser app generates from this transport's published document:
        # with the document gone there is nothing to generate from, and a package whose build points
        # at a file that is not there fails every target `build-packages` is a prerequisite of.
        "any": ("packages/api-client",),
        "java": (),
    },
    "keycloak": {
        "typescript": (
            "src/adapters/driving/http/auth/oidc-keycloak.ts",
            "tests/auth/oidc-keycloak.test.ts",
        ),
        "python": (
            "src/*/adapters/driving/http/auth/oidc_keycloak.py",
            "tests/auth/test_oidc_keycloak.py",
        ),
        "go": ("adapters/driving/http/auth/oidckeycloak",),
        "java": (
            "src/main/java/com/example/*/adapters/driving/http/auth",
            "src/test/java/com/example/*/adapters/driving/http/auth",
        ),
        "any": ("docker/keycloak/realms/app.json",),
    },
    "users-keycloak": {
        "typescript": (
            "src/adapters/driving/http/users/oidc-keycloak.ts",
            "tests/users/oidc-keycloak.test.ts",
        ),
        "python": (
            "src/*/adapters/driving/http/users/oidc_keycloak.py",
            "tests/users/test_users_oidc_keycloak.py",
        ),
        "go": ("adapters/driving/http/users/userskeycloak",),
        "java": (
            "src/main/java/com/example/*/adapters/driving/http/users",
            "src/test/java/com/example/*/adapters/driving/http/users",
        ),
        "any": ("docker/keycloak/realms/customers.json",),
    },
}

# Repository-root files that exist while *any* of several features does, keyed by the features joined with
# `|` the way a shared marked region names them. The Keycloak README describes one container in one file,
# a marked section per realm, so it is nobody's alone: it goes when the last realm does.
SHARED_FILES: dict[str, tuple[str, ...]] = {
    "keycloak|users-keycloak": ("docker/keycloak/README.md",),
}

# Files that exist in a browser app only because a feature was selected, relative to the app and applied
# to every browser app `project.json` lists — the customer login lands in every one, because the pruner
# decides per project and a browser app whose service cannot validate the token would still carry a login
# that leads nowhere.
#
# The route that calls this project's own API goes with the transport that answers it, for the same
# reason: what it shows is a service answering, and a project with no transport has no service to ask.
OWNED_FILES_PER_WEB_APP: dict[str, tuple[str, ...]] = {
    "users-keycloak": ("src/auth", "tests/auth"),
    "fastify": ("src/routes", "tests/routes"),
    "fastapi": ("src/routes", "tests/routes"),
    "net-http": ("src/routes", "tests/routes"),
}

# Compose services a feature needs. A feature absent from here needs no container at all, which is what
# lets a SQLite project have no docker-compose.yml — unless the app is in there too, see below.
CONTAINERS: dict[str, str] = {"postgres": "postgres", "keycloak": "keycloak", "users-keycloak": "keycloak"}

# The features whose presence puts the *app* into Compose: a transport gives the file a `service` to run,
# and a frontend gives it a `web`. Compose is deleted only when nothing is left to compose — dropping the
# last container is not the same question, now that `make demo` runs the app from this file too.
APP_SERVICE_FEATURES: tuple[str, ...] = (
    "fastapi",
    "fastify",
    "net-http",
    "quarkus-rest",
    "spring-web",
)

# Dependencies and scripts that exist only for a feature, per backend.
#
# For TypeScript these are removed with `npm uninstall` rather than by editing package.json, because
# package.json and package-lock.json have to move together — a hand-edited manifest leaves `npm ci`
# refusing to install anything at all. Python's requirements file has no lockfile, so its lines are simply
# dropped. Go's module graph is derived from the imports, so removing the adapter is the removal, and
# `go mod tidy` is what writes it down.
PACKAGE_EDITS: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {
    "typescript": {
        "postgres": {
            "packages": ("pg", "@types/pg", "node-pg-migrate"),
            "scripts": ("migrate", "migrate:down", "test:integration"),
        },
        "sqlite": {"packages": (), "scripts": ()},
        # The transport and the schema library it declares its routes and its environment with: they
        # arrive together and they go together, because nothing else in the service imports either.
        "fastify": {
            "packages": (
                "@fastify/cors",
                "@fastify/env",
                "@fastify/helmet",
                "@fastify/otel",
                "@fastify/swagger",
                "@fastify/type-provider-typebox",
                "@opentelemetry/api",
                "@opentelemetry/exporter-trace-otlp-http",
                "@opentelemetry/resources",
                "@opentelemetry/sdk-trace-node",
                "@opentelemetry/semantic-conventions",
                "@sinclair/typebox",
                "fastify",
            ),
            "scripts": ("dev", "build", "start", "openapi"),
        },
        "keycloak": {"packages": (), "scripts": ()},
        "users-keycloak": {"packages": (), "scripts": ()},
    },
    "python": {
        "postgres": {"packages": ("psycopg[binary]",), "scripts": ()},
        "sqlite": {"packages": (), "scripts": ()},
        # The framework, its server, the client its own edge suite drives it with, and the settings
        # model the composition root checks the environment against — all four arrive with the
        # transport and nothing else in the service imports any of them.
        "fastapi": {
            "packages": (
                "fastapi",
                "uvicorn",
                "httpx",
                "opentelemetry-api",
                "opentelemetry-exporter-otlp-proto-http",
                "opentelemetry-instrumentation-fastapi",
                "opentelemetry-sdk",
                "pydantic-settings",
            ),
            "scripts": (),
        },
        "keycloak": {"packages": (), "scripts": ()},
        "users-keycloak": {"packages": (), "scripts": ()},
    },
    "go": {
        "postgres": {"packages": ("github.com/jackc/pgx/v5",), "scripts": ()},
        "sqlite": {"packages": ("modernc.org/sqlite",), "scripts": ()},
        # The instrumentation and the SDK behind it, which only a transport can use: one span per
        # request, continuing whatever traceparent arrived. Naming them here is what tells the pruner
        # there is a module to tidy — Go's requirements are derived from the imports, so removing the
        # package above is the removal and tidying is what writes it down.
        "net-http": {
            "packages": (
                "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp",
                "go.opentelemetry.io/otel",
                "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp",
                "go.opentelemetry.io/otel/sdk",
            ),
            "scripts": (),
        },
        "keycloak": {"packages": (), "scripts": ()},
        "users-keycloak": {"packages": (), "scripts": ()},
    },
    # Empty on purpose, for every feature. Maven's manifest is XML, and editing XML by dropping lines is
    # how a build file becomes unparseable — so Java's per-feature dependencies sit inside marked regions
    # of `pom.xml` instead (see MARKED_FILES_BY_LANGUAGE), and stripping the region removes the dependency
    # and the `application.properties` block that reads it in one pass. There is nothing left for a
    # package manager to uninstall afterwards.
    "java": {
        "postgres": {"packages": (), "scripts": ()},
        "sqlite": {"packages": (), "scripts": ()},
        "quarkus-rest": {"packages": (), "scripts": ()},
        "spring-web": {"packages": (), "scripts": ()},
        "keycloak": {"packages": (), "scripts": ()},
        "users-keycloak": {"packages": (), "scripts": ()},
    },
}

# The npm packages a feature adds to every browser app, removed the same way as a service's. The factory's
# test suite asserts this agrees with what the generator adds to the browser app's manifest.
WEB_PACKAGE_EDITS: dict[str, tuple[str, ...]] = {
    "users-keycloak": ("react-oidc-context", "oidc-client-ts"),
}

# Environment keys a feature gives the *app's own* Compose service — the address its composition root opens
# the backing service from, which `/ready` then reports on.
#
# A table rather than a marked region, and for a reason the file itself explains: the app's block already
# sits inside its transport's region, a region inside it would be nested, and this script refuses a nested
# marker. An unmarked line would survive `--event-store memory` naming a container the same prune had just
# deleted. So this is the same shape as `PACKAGE_EDITS` above — what generation adds, a prune takes away —
# and the factory's test suite asserts the two agree.
SERVICE_ENVIRONMENT: dict[str, tuple[str, ...]] = {"postgres": ("DATABASE_URL",)}


def project_has_web(root: Path) -> bool:
    """Whether this project has a browser app, read from the manifest rather than guessed.

    Read for one reason: a browser app puts a service in Compose, and a frontend is not a prunable
    feature — so nothing in the marker data can tell this script whether the file still has a job.
    """
    manifest = root / "project.json"
    if not manifest.is_file():
        return False
    deployables = json.loads(manifest.read_text()).get("deployables") or {}
    return any(
        isinstance(record, dict) and record.get("kind") == "web" and record.get("generated") is not False
        for record in deployables.values()
    )


def project_target(root: Path) -> str:
    """Where this project goes to production, read from the manifest; `none` where nothing says.

    `none` rather than a refusal for a manifest without the key, because projects generated before the
    target existed are exactly the local-only ones the key would have said `none` for.
    """
    manifest = root / "project.json"
    if not manifest.is_file():
        return "none"
    target = json.loads(manifest.read_text()).get("target")
    return target if isinstance(target, str) else "none"


def project_services(root: Path) -> list[tuple[str, str]]:
    """Every service's directory and language, from the manifest — the one list of them this project keeps.

    The layouts below are relative to a service and differ per language, so a prune has to know where the
    services are and what each is written in; the manifest is where the factory wrote that down and where
    `add-service` appends to it. Read rather than guessed: a wrong guess deletes the wrong files. A manifest
    that is missing, records no service, or names a language this script has no layout for is refused.
    """
    manifest = root / "project.json"
    if not manifest.is_file():
        raise ValueError("project.json is missing, so the services cannot be found")
    deployables = json.loads(manifest.read_text()).get("deployables")
    services: list[tuple[str, str]] = []
    for record in (deployables or {}).values():
        # A service recorded `"generated": false` already existed when the method was installed around it: it
        # is in any language, has none of these layouts, and is never pruned.
        if not isinstance(record, dict) or record.get("kind") != "service" or record.get("generated") is False:
            continue
        path, language = record.get("path"), record.get("language")
        if not isinstance(path, str):
            continue
        if language not in LANGUAGES:
            raise ValueError(f"project.json names an unsupported backend language for {path}: {language!r}")
        services.append((path, language))
    recorded = [r for r in (deployables or {}).values() if isinstance(r, dict)]
    if not services and not any(r.get("kind") == "service" or r.get("generated") is False for r in recorded):
        raise ValueError("project.json records no service under `deployables`")
    # Empty where every service already existed when the method was installed: nothing here has a layout.
    return services


def owned_paths(
    root: Path, feature: str, services: list[tuple[str, str]], web_apps: list[str] = ()
) -> list[Path]:
    """Every path a feature owns in this project — in every service by that service's layout, in every
    browser app, and at the root — with glob patterns resolved."""
    entry = OWNED_FILES[feature]
    patterns = [
        *(f"{service}/{pattern}" for service, language in services for pattern in entry.get(language, ())),
        *(f"{web}/{pattern}" for web in web_apps for pattern in OWNED_FILES_PER_WEB_APP.get(feature, ())),
        *entry.get("any", ()),
    ]
    paths: list[Path] = []
    for pattern in patterns:
        if any(character in pattern for character in "*?["):
            paths.extend(sorted(root.glob(pattern)))
        else:
            paths.append(root / pattern)
    return paths


def delivery_of(root: Path) -> str:
    """Where the factory's delivery material lives, from the manifest's `layout.delivery`: `.` — the root, as
    every generated project has it and every manifest written before the key meant — or a directory such as
    `delivery`, where the method was installed beside an existing codebase."""
    manifest = root / "project.json"
    if not manifest.is_file():
        return "."
    layout = json.loads(manifest.read_text()).get("layout")
    delivery = layout.get("delivery", ".") if isinstance(layout, dict) else "."
    return delivery if isinstance(delivery, str) and delivery else "."


def placed(relative: str, delivery: str) -> str:
    """A repository-level path as the layout places it: the delivery material under `delivery`, the rest as is."""
    if delivery == "." or not any(relative == r or relative.startswith(f"{r}/") for r in DELIVERY_ROOTS):
        return relative
    return f"{delivery}/{relative}"


def marked_files(services: list[tuple[str, str]], web_apps: list[str] = (), delivery: str = ".") -> tuple[str, ...]:
    """The repository's marked files, each browser app's, and each service's own — by its language."""
    return (
        *(placed(relative, delivery) for relative in MARKED_FILES),
        *(f"{web}/{relative}" for web in web_apps for relative in MARKED_FILES_PER_WEB_APP),
        *(
            f"{service}/{relative}"
            for service, language in services
            for relative in MARKED_FILES_BY_LANGUAGE[language]
        ),
    )


def marked_paths(
    root: Path, services: list[tuple[str, str]], web_apps: list[str] = (), delivery: str = "."
) -> list[Path]:
    """The same list as paths, with any glob resolved and anything missing left out.

    Resolved here rather than in `marked_files`, which several callers read as names: a Python service's
    package directory is named after the project, so the one file in it that carries a marked region —
    the entry point — can only be named by pattern.
    """
    paths: list[Path] = []
    for relative in marked_files(services, web_apps, delivery):
        if any(character in relative for character in "*?["):
            paths.extend(sorted(root.glob(relative)))
        else:
            paths.append(root / relative)
    return [path for path in paths if path.is_file()]


# There is deliberately no "keep this only when the feature is absent" marker, and it is worth saying why
# because it looks like the obvious way to express an alternative. Pruning only ever subtracts: the factory
# already cut the not-selected branch when it generated the project, so a later prune has nothing to bring
# back and the target would simply vanish. An alternative has to be written so that both states are valid
# at once — the generated Makefile does it with `INTEGRATION_TEST := …` inside the marked block and
# `INTEGRATION_TEST ?= …` outside it, where deleting the block is what activates the fallback.
#
# A marker names one feature, or several joined with `|` for a region they all need: the one Keycloak
# container serves both realms, so its Compose block is `keycloak|users-keycloak` and stays while either
# is kept. That is the whole of the "shared" concept — there is no region kept by the *absence* of anything.
MARKER = re.compile(r"backing-service:([a-z0-9-]+(?:\|[a-z0-9-]+)*):(begin|end)")


def marker_features(name: str) -> set[str]:
    """The features a marker names — one, or the several a shared region belongs to."""
    return set(name.split("|"))


def strip_markers(text: str, keep: set[str], settled: set[str]) -> str:
    """Drop the marked regions no feature in `keep` still holds.

    A feature in `settled` has had its fate decided, so its surviving markers go too — a marker nothing
    will ever act on again is noise in a shipped project. Every other feature keeps its markers, which is
    what lets a later prune find it. `settled` is deliberately per-feature rather than one flag: answering
    the auth question must not quietly settle the event-store question as well, or a project that ran
    `./init --auth none` could never afterwards drop Postgres.

    A shared marker is rewritten to name only the features still holding it open — a dropped or settled
    one leaves the name, or `--list` would keep offering an answer whose files are gone — and goes
    altogether once none remain.
    """
    output: list[str] = []
    open_name: str | None = None
    for line in text.splitlines(keepends=True):
        match = MARKER.search(line)
        if match is None:
            if open_name is None or marker_features(open_name) & keep:
                output.append(line)
            continue
        name, edge = match.group(1), match.group(2)
        if edge == "begin":
            if open_name is not None:
                raise ValueError(f"nested backing-service marker: {name} inside {open_name}")
            open_name = name
        else:
            if open_name != name:
                raise ValueError(f"unbalanced backing-service marker: {name}")
            open_name = None
        holding = [feature for feature in name.split("|") if feature in keep and feature not in settled]
        if holding:
            output.append(line.replace(f"backing-service:{name}:", f"backing-service:{'|'.join(holding)}:"))
    if open_name is not None:
        raise ValueError(f"unclosed backing-service marker: {open_name}")
    return "".join(output)


def project_web_apps(root: Path) -> list[str]:
    """Every browser app's directory, from the same manifest — empty for a project without one."""
    manifest = root / "project.json"
    if not manifest.is_file():
        return []
    deployables = json.loads(manifest.read_text()).get("deployables")
    return [
        record["path"]
        for record in (deployables or {}).values()
        if isinstance(record, dict) and record.get("kind") == "web" and isinstance(record.get("path"), str)
        and record.get("generated") is not False
    ]


def features_installed(root: Path, services: list[tuple[str, str]]) -> set[str]:
    """Which features have their own files on disk, whether or not the choice is still open."""
    web = project_web_apps(root)
    return {
        feature
        for feature in FEATURES
        if any(path.exists() for path in owned_paths(root, feature, services, web))
    }


def features_present(root: Path, services: list[tuple[str, str]]) -> set[str]:
    """Which features are still *choosable* — those whose marked regions survive on disk.

    A feature with owned files but no surviving marker has been settled already, and a feature with neither
    was never generated. Both are excluded, so an axis never offers an answer that cannot be given.
    """
    present: set[str] = set()
    for path in marked_paths(root, services, project_web_apps(root), delivery_of(root)):
        for name, edge in MARKER.findall(path.read_text()):
            if edge == "begin":
                present |= marker_features(name) & set(FEATURES)
    return present


def governed(axis: str) -> set[str]:
    """Every feature this axis decides the fate of."""
    return {
        feature
        for option in AXES[axis]["options"].values()
        for feature in option["features"]
    }


def governed_capabilities(axis: str) -> set[str]:
    """Every capability this axis's answers give, whichever one was recorded.

    The whole axis rather than the answer that is being replaced, for the same reason `governed` takes the
    whole axis: what is being written is "this axis is now answered *this* way", and a manifest that
    recorded some other answer of the same axis has to end up saying so too.
    """
    return {
        capability
        for option in AXES[axis]["options"].values()
        for capability in option["capabilities"]
    }


def answered(axis: str, keep: set[str]) -> bool:
    """Whether this axis ends up with a real answer rather than "none"."""
    return bool(governed(axis) & keep)


def axis_options(axis: str, present: set[str], target: str) -> list[str]:
    """The answers this axis can still be given, most capable first.

    An option is offerable when every feature it needs is still choosable and the project's target offers
    it. `none`, needing nothing and offered everywhere, is always offerable — which is correct: any axis
    can always be answered by dropping it.
    """
    return [
        name
        for name, option in AXES[axis]["options"].items()
        if set(option["features"]) <= present and target in option["targets"]
    ]


def _remove(path: Path, log) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()
    else:
        return
    log(f"  removed {path}")


def _prune_empty_parents(path: Path, stop: Path, log) -> None:
    parent = path.parent
    while parent != stop and parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
        log(f"  removed {parent} (now empty)")
        parent = parent.parent


def _uninstall_typescript(
    root: Path, service: str, packages: tuple[str, ...], scripts: tuple[str, ...], log
) -> None:
    manifest = root / service / "package.json"
    if not manifest.is_file():
        return
    package = json.loads(manifest.read_text())
    wanted = [
        name
        for name in packages
        if name in {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    ]
    leftover_scripts = [name for name in scripts if name in package.get("scripts", {})]
    if not wanted and not leftover_scripts:
        return

    if leftover_scripts:
        for name in leftover_scripts:
            del package["scripts"][name]
        manifest.write_text(json.dumps(package, indent=2) + "\n")
        log(f"  {service}/package.json: dropped script(s) {', '.join(leftover_scripts)}")

    if not wanted:
        return
    if shutil.which("npm") is None:
        log(
            f"  npm not found. Remove the now-unused dependencies yourself so package.json and the\n"
            f"    lockfile stay in step:  npm uninstall -w {service} {' '.join(wanted)}"
        )
        return
    result = subprocess.run(
        ["npm", "uninstall", "--no-audit", "--no-fund", "-w", service, *wanted],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        log(f"  npm uninstall -w {service} {' '.join(wanted)}")
    else:
        log(
            f"  `npm uninstall -w {service} {' '.join(wanted)}` failed; run it yourself so\n"
            f"    package.json and the lockfile stay in step:\n"
            f"    {result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'no stderr'}"
        )


# A dependency line inside one of `pyproject.toml`'s two arrays: `  "fastapi==0.141.1",`. Matched on the
# distribution name rather than on the whole pinned line, so a version bump in the generated project does
# not make this silently miss, and anchored to the array's own indentation so a string anywhere else in
# the manifest cannot look like one.
PYTHON_DEPENDENCY = re.compile(r'^\s+"([^"\[<>=!;\s]+)')


def _uninstall_python(root: Path, service: str, packages: tuple[str, ...], log) -> None:
    """Drop the dependency lines a feature added, from both of the manifest's arrays, and re-lock.

    The lock has to follow, because `uv sync --locked` refuses one that disagrees with its manifest — the
    same reason the npm half of this runs `npm uninstall` rather than editing `package.json` alone. Unlike
    npm, uv can re-resolve from the versions already in the lock with no network at all, so this is not a
    prune that needs the registry.
    """
    manifest = root / service / "pyproject.toml"
    if not manifest.is_file() or not packages:
        return
    names = {name.split("[")[0].lower() for name in packages}
    kept: list[str] = []
    dropped: list[str] = []
    for line in manifest.read_text().splitlines(keepends=True):
        match = PYTHON_DEPENDENCY.match(line)
        if match is not None and match.group(1).lower() in names:
            dropped.append(line.strip().rstrip(","))
        else:
            kept.append(line)
    if not dropped:
        return
    manifest.write_text("".join(kept))
    log(f"  {service}/pyproject.toml: dropped {', '.join(dropped)}")
    if shutil.which("uv") is None:
        log(
            "  uv not found. Re-lock yourself so pyproject.toml and uv.lock stay in step:\n"
            f"    (cd {service} && uv lock)"
        )
        return
    result = subprocess.run(
        ["uv", "lock", "--quiet"], cwd=root / service, capture_output=True, text=True
    )
    if result.returncode == 0:
        log(f"  (cd {service} && uv lock)")
    else:
        log(
            f"  `uv lock` failed in {service}; run it yourself so pyproject.toml and uv.lock stay in\n"
            f"    step:\n    {result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'no stderr'}"
        )


def _uninstall_go(root: Path, service_path: str, packages: tuple[str, ...], log) -> None:
    """Let the module graph follow the imports.

    Go derives its requirements from what the code imports, so deleting the adapter *is* the removal and
    `go mod tidy` is only what writes it into go.mod and go.sum. Editing go.mod by hand instead would leave
    go.sum describing a module nothing needs, which `go mod verify` reports and no gate here would.
    """
    service = root / service_path
    if not packages or not (service / "go.mod").is_file():
        return
    # Only when go.mod actually still requires one of them. Generation prunes every feature the project was
    # not given, and running a network operation for a module that was never there would make scaffolding
    # need the network.
    required = (service / "go.mod").read_text()
    if not any(package in required for package in packages):
        return
    if shutil.which("go") is None:
        log(
            "  go not found. Run it yourself so go.mod and go.sum stop naming the dropped adapter's\n"
            f"    module:  (cd {service_path} && go mod tidy)"
        )
        return
    result = subprocess.run(["go", "mod", "tidy"], cwd=service, capture_output=True, text=True)
    if result.returncode == 0:
        log(f"  go mod tidy — dropped {', '.join(packages)}")
    else:
        log(
            "  `go mod tidy` failed; run it yourself so go.mod and go.sum stop naming the dropped\n"
            f"    adapter's module:\n    {result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'no stderr'}"
        )


def _apply_package_edits(root: Path, services: list[tuple[str, str]], dropped: set[str], log) -> None:
    for service, language in services:
        edits = PACKAGE_EDITS[language]
        packages: tuple[str, ...] = ()
        scripts: tuple[str, ...] = ()
        for feature in sorted(dropped):
            entry = edits.get(feature)
            if entry is None:
                continue
            packages += entry["packages"]
            scripts += entry["scripts"]
        if not packages and not scripts:
            # Every Java feature lands here: its dependencies are marked regions of the pom, already
            # stripped above, so there is no manifest left to edit. Checked before the dispatch rather than
            # as another branch in it, because "nothing to uninstall" is the honest condition — a language
            # whose features add no packages needs no uninstaller, whatever it is called.
            continue
        if language == "typescript":
            _uninstall_typescript(root, service, packages, scripts, log)
        elif language == "python":
            _uninstall_python(root, service, packages, log)
        elif language == "go":
            _uninstall_go(root, service, packages, log)
    # A browser app is TypeScript whatever its service is written in, so its manifest is edited npm's way.
    web_packages: tuple[str, ...] = ()
    for feature in sorted(dropped):
        web_packages += WEB_PACKAGE_EDITS.get(feature, ())
    if web_packages:
        for web in project_web_apps(root):
            _uninstall_typescript(root, web, web_packages, (), log)


def _drop_compose_environment(root: Path, dropped: set[str], log) -> None:
    """Take the app service's address for a dropped backing service out of docker-compose.yml.

    Matched on the key at the start of a mapping line, which is the only shape the factory writes it in.
    A file that does not have the key is left alone, so this is idempotent like everything else here.
    """
    keys = tuple(key for feature in sorted(dropped) for key in SERVICE_ENVIRONMENT.get(feature, ()))
    path = root / "docker-compose.yml"
    if not keys or not path.is_file():
        return
    pattern = re.compile(rf"^\s+({'|'.join(re.escape(key) for key in keys)}):")
    lines = path.read_text().splitlines(keepends=True)
    kept = [line for line in lines if not pattern.match(line)]
    if len(kept) == len(lines):
        return
    path.write_text("".join(kept))
    log(f"  docker-compose.yml: dropped {', '.join(keys)} from the app service")


def prune(root: Path, keep: set[str], *, settled: set[str] | None = None, log=print) -> None:
    """Cut the project down to `keep`. Idempotent: pruning what is already absent does nothing.

    `settled` names the features whose choice is now final; their markers are removed along with the
    dropped features' regions. The factory passes none of them, so a generated project can still choose.
    """
    settled = set() if settled is None else settled
    services = project_services(root)
    present = features_present(root, services)
    unknown = (keep | settled) - set(FEATURES)
    if unknown:
        raise ValueError(f"unknown backing-service feature(s): {', '.join(sorted(unknown))}")
    keep = keep & present
    dropped = present - keep

    for path in marked_paths(root, services, project_web_apps(root), delivery_of(root)):
        text = path.read_text()
        if not MARKER.search(text):
            continue
        path.write_text(strip_markers(text, keep, settled))

    web = project_web_apps(root)
    for feature in sorted(dropped):
        for path in owned_paths(root, feature, services, web):
            _remove(path, log)
            _prune_empty_parents(path, root, log)
    for group, relatives in SHARED_FILES.items():
        if marker_features(group) & keep:
            continue
        for relative in relatives:
            _remove(root / relative, log)
            _prune_empty_parents(root / relative, root, log)

    _apply_package_edits(root, services, dropped, log)
    _drop_compose_environment(root, dropped, log)

    installed = features_installed(root, services)
    containers_left = any(feature in installed for feature in CONTAINERS)
    app_left = (
        any(feature in installed for feature in APP_SERVICE_FEATURES)
        or project_has_web(root)
    )
    if not containers_left and not app_left:
        _remove(root / "docker-compose.yml", log)
        if dropped:
            log("  nothing left to compose; docker-compose.yml is gone")
    if not containers_left:
        docker = root / "docker"
        if docker.is_dir() and not any(docker.rglob("*")):
            _remove(docker, log)

    if dropped:
        log(f"  pruned: {', '.join(sorted(dropped))}")
    if keep:
        log(f"  kept: {', '.join(sorted(keep))}")


def restated(recorded: list[str], dropped: set[str], gained: tuple[str, ...]) -> list[str]:
    """One axis's answer swapped for another inside a recorded capability list, in the generator's order.

    In place rather than appended: the generator writes the profile's capabilities, then the language, then
    one per axis in catalog order, and a project that answers an axis again should end with the file a
    generation with that answer would have written — not the same set in a different order.
    """
    updated: list[str] = []
    swapped = False
    for capability in recorded:
        if capability not in dropped:
            updated.append(capability)
            continue
        if not swapped:
            updated.extend(gained)
            swapped = True
    if not swapped:
        updated.extend(capability for capability in gained if capability not in updated)
    return updated


# Answering an axis again is the one moment a project's answers change with no factory running, so it is the
# one moment `project.json` can go stale: the adapters are gone and the manifest still names them. That is
# not only untidy. The manifest is what `slipwai migrate` and `replay` regenerate from — they would put the
# dropped adapter back — and each deployable's `capabilities` is what decides which skills the project is
# given, so a dropped identity provider would leave eleven thousand words about OAuth looking justified and
# `make check-agents` with nothing to report.
#
# `generator` is deliberately left exactly as found. `updatedWith` names the newest *factory* to have
# written here, and this script is the copy that factory shipped into the project — nothing newer has run —
# so moving it forward would make `migrate` skip the catch-up notes the project still owes.
def record_answers(root: Path, answers: list[tuple[str, str]], log=print) -> None:
    """Write the new answers into `project.json`: every generated service's `selection` and `capabilities`.

    Only the applications that recorded the axis, and only that axis's own capabilities: the profile's, the
    language's and the other axes' stay exactly where the generator put them. A deployable recording no
    `capabilities` — a project generated before they were written, which `slipwai migrate` brings the field
    to — keeps none rather than being given a half-derived list this script cannot complete.
    """
    manifest = root / "project.json"
    if not manifest.is_file():
        return
    document = json.loads(manifest.read_text())
    deployables = document.get("deployables")
    if not isinstance(deployables, dict):
        return
    changed: list[str] = []
    for name, record in deployables.items():
        selection = record.get("selection") if isinstance(record, dict) else None
        if not isinstance(selection, dict) or record.get("generated") is False:
            continue
        for axis, chosen in answers:
            if selection.get(axis) in (None, chosen):
                continue
            selection[axis] = chosen
            recorded = record.get("capabilities")
            if isinstance(recorded, list):
                record["capabilities"] = restated(
                    recorded, governed_capabilities(axis), AXES[axis]["options"][chosen]["capabilities"]
                )
            changed.append(f"{name}: {axis} is now {chosen}")
    if not changed:
        return
    manifest.write_text(json.dumps(document, indent=2) + "\n")
    for line in changed:
        log(f"  project.json — {line}")


def _main(argv: list[str], root: Path | None = None) -> int:
    if root is None:
        # The repository root is the nearest directory above this script with a manifest: this is
        # `<root>/scripts/backing-services.py` in a generated project and `<root>/<layout.delivery>/scripts/…`
        # where the method was installed beside an existing codebase.
        script = Path(__file__).resolve()
        root = next((c for c in script.parents if (c / "project.json").is_file()), script.parents[1])
    try:
        services = project_services(root)
    except ValueError as error:
        print(f"cannot prune this project: {error}", file=sys.stderr)
        return 2
    target = project_target(root)
    present = features_present(root, services)
    installed = features_installed(root, services)

    parser = argparse.ArgumentParser(
        prog="scripts/backing-services.py",
        description="Prune this project's backing services to the ones it uses. One axis, one answer.",
    )
    parser.add_argument("--list", action="store_true", help="show what each axis can still be answered with")
    for axis, spec in AXES.items():
        parser.add_argument(
            f"--{axis}",
            metavar="|".join(axis_options(axis, present, target)) or "none",
            help=spec["prompt"],
        )
    args = parser.parse_args(argv)
    answers = {axis: getattr(args, axis.replace("-", "_")) for axis in AXES}

    if args.list or not any(answers.values()):
        open_axes = {axis: axis_options(axis, present, target) for axis in AXES}
        open_axes = {axis: options for axis, options in open_axes.items() if len(options) > 1}
        if not open_axes:
            print("Every backing-service choice in this project is already settled.")
            return 0
        print("Backing services in this project — one answer per axis:\n")
        for axis, options in open_axes.items():
            print(f"  --{axis}  ({AXES[axis]['prompt']})")
            for name in options:
                option = AXES[axis]["options"][name]
                print(f"      {name.ljust(9)} {option['label']}")
                if option["note"]:
                    print(f"      {' ' * 9} {option['note']}")
            print("")
        print("Naming an answer prunes the rest. Nothing is committed, so `git checkout .` undoes it.")
        return 0

    keep = set(present)
    settled: set[str] = set()
    chosen_options: list[tuple[str, str, dict]] = []
    for axis, chosen in answers.items():
        if chosen is None:
            continue
        options = axis_options(axis, present, target)
        if chosen not in AXES[axis]["options"]:
            print(
                f"Unknown --{axis} value {chosen!r}. This project can still be given: "
                f"{', '.join(options)}.",
                file=sys.stderr,
            )
            return 2
        if chosen not in options:
            missing = sorted(set(AXES[axis]["options"][chosen]["features"]) - present)
            if target not in AXES[axis]["options"][chosen]["targets"]:
                reason = (
                    f"it is not offered under the {target} target this project goes to, and the factory "
                    "would have refused it for the same reason"
                )
            elif set(missing) & installed:
                reason = (
                    f"{', '.join(missing)} was settled already and its files are here to stay. Undo it with "
                    "`git checkout .` before your first commit, or add it by hand"
                )
            else:
                reason = (
                    f"this project was generated without {', '.join(missing)}, and pruning only ever "
                    "subtracts — it cannot add an adapter the factory did not emit"
                )
            print(f"--{axis} {chosen} is not available here: {reason}.", file=sys.stderr)
            return 2
        option = AXES[axis]["options"][chosen]
        # Only the features this axis governs are affected; another axis's features are left alone, or
        # answering the auth question would quietly drop the event store.
        decided = governed(axis)
        keep -= decided
        keep |= set(option["features"])
        settled |= decided & present
        chosen_options.append((axis, chosen, option))

    for axis in TARGET_REQUIRES.get(target, ()):
        if answered(axis, keep):
            continue
        print(
            f"Refusing to prune: this project goes to the {target} target, which deploys its {axis} answer "
            f"and proves a deploy by asking it for /health — so `--{axis} none` would leave nothing to deploy. "
            f"Keep the {axis} answer, or change the target in project.json to none first.",
            file=sys.stderr,
        )
        return 2

    for axis, required_axes in REQUIRES.items():
        if not answered(axis, keep):
            continue
        for required in required_axes:
            if answered(required, keep):
                continue
            print(
                f"Refusing to prune: this project would keep its {axis} adapter with no {required} "
                f"to reach it.\n\n{REQUIRES_BECAUSE[axis]}\nDrop both, with "
                f"`--{axis} none --{required} none`, or keep the transport.",
                file=sys.stderr,
            )
            return 2

    for axis, chosen, option in chosen_options:
        print(f"{axis}: {chosen} — {option['label']}")
        if option["note"]:
            print(f"  {option['note']}")

    prune(root, keep, settled=settled)
    # After the files, never before: a prune that raised would otherwise leave a manifest describing a
    # project that is not on disk, which is the one state every reader of it trusts cannot happen.
    record_answers(root, [(axis, chosen) for axis, chosen, _option in chosen_options])
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
