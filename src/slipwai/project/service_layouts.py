"""Which committed asset lands at which path under `apps/service`, per backend.

One table, keyed by backend and then by marker feature, because the answer is pure data: a feature's files
are the same files whatever else the selection contains. It sits apart from `backing_services.py` for the
ordinary reason — the table is most of the bytes and none of the behaviour, and a module that holds both
outgrows what anybody wants to read at once.

Sources are relative to `assets/backing-services/<backend>/`; a `../` reaches material shared between
backends, which is how one event-log schema serves every SQL adapter here rather than being copied per
language and drifting.

The read side's files are the same shape and live in `read_side_layouts.py`, merged in at the bottom of
this module. Two tables rather than one because each is already most of a module's bytes, and because they
answer different questions — what a project writes its log with, and what it maintains a view with.
"""
from __future__ import annotations

from .read_side_layouts import JAVA_PORTS, with_read_side

WRITE_SIDE_FILES: dict[str, dict[str, dict[str, str]]] = {
    "typescript": {
        "memory": {
            "src/application/ports/events.ts": "events.ts",
            "src/adapters/driven/event-store-memory.ts": "event-store-memory.ts",
            "tests/contract/event-store-contract.ts": "tests/event-store-contract.ts",
            "tests/contract/event-store-memory.test.ts": "tests/event-store-memory.test.ts",
        },
        "sqlite": {
            "src/adapters/driven/event-store-sqlite.ts": "event-store-sqlite.ts",
            "tests/contract/event-store-sqlite.test.ts": "tests/event-store-sqlite.test.ts",
        },
        "postgres": {
            "src/adapters/driven/event-store-postgres/index.ts": "event-store-postgres.ts",
            "tests/integration/event-store-postgres.test.ts": "tests/event-store-postgres.test.ts",
            "vitest.integration.config.ts": "vitest.integration.config.ts",
            "migrations/001_events.js": "migrations/001_events.js",
            "migrations/002_events_append_only.js": "migrations/002_events_append_only.js",
        },
        "fastify": {
            "src/adapters/driving/http/app.ts": "http-app.ts",
            # The environment's one schema. Under the transport rather than beside the store because
            # `@fastify/env` is what checks it and the app is what carries the result: a project with
            # `--http none` has no process of its own to configure.
            "src/config.ts": "config.ts",
            # The SDK's wiring, under the transport for the same reason: a span per request is the one
            # thing only a transport can produce, and a project with `--http none` has no request to
            # open one for.
            "src/tracing.ts": "tracing.ts",
            "src/main.ts": "main.ts",
            # The published document, written from the app rather than beside it. A second entry point,
            # because it builds the app exactly as `main.ts` does and then binds nothing at all.
            "src/openapi.ts": "openapi-export.ts",
            "tests/edge/http-app.test.ts": "tests/http-app.test.ts",
            "tests/edge/tracing.test.ts": "tests/tracing.test.ts",
        },
        "keycloak": {
            "src/adapters/driving/http/auth/oidc-keycloak.ts": "oidc-keycloak.ts",
            "tests/auth/oidc-keycloak.test.ts": "tests/oidc-keycloak.test.ts",
        },
        "users-keycloak": {
            "src/adapters/driving/http/users/oidc-keycloak.ts": "users-oidc-keycloak.ts",
            "tests/users/oidc-keycloak.test.ts": "tests/users-oidc-keycloak.test.ts",
        },
    },
    # Emitted under the template package name; `language_files` renames the directory after the project
    # and rewrites the imports, which is why every path here says `delivery_starter`.
    "python": {
        "memory": {
            "src/delivery_starter/application/ports/events.py": "events.py",
            "src/delivery_starter/adapters/driven/event_store_memory.py": "event_store_memory.py",
            "tests/conftest.py": "tests/conftest.py",
            "tests/contract/event_store_contract.py": "tests/event_store_contract.py",
            "tests/contract/test_event_store_memory.py": "tests/test_event_store_memory.py",
        },
        "sqlite": {
            "src/delivery_starter/adapters/driven/event_store_sqlite.py": "event_store_sqlite.py",
            "tests/contract/test_event_store_sqlite.py": "tests/test_event_store_sqlite.py",
        },
        "postgres": {
            "src/delivery_starter/adapters/driven/event_store_postgres.py": "event_store_postgres.py",
            "tests/integration/test_event_store_postgres.py": "tests/test_event_store_postgres.py",
            "migrations/apply.py": "migrations_apply.py",
            "migrations/001_events.sql": "../sql/001_events.sql",
            "migrations/002_events_append_only.sql": "../sql/002_events_append_only.sql",
        },
        "fastapi": {
            "src/delivery_starter/adapters/driving/http/app.py": "http_app.py",
            "src/delivery_starter/main.py": "main.py",
            "src/delivery_starter/logging_setup.py": "logging_setup.py",
            # The environment's one model. Under the transport rather than beside the store because
            # the composition root is what reads it: a project with `--http none` has no process of
            # its own to configure.
            "src/delivery_starter/settings.py": "settings.py",
            # The SDK's wiring, under the transport for the same reason: a span per request is
            # the one thing only a transport can produce.
            "src/delivery_starter/tracing.py": "tracing.py",
            # The published document, written from the app rather than beside it. A second entry point,
            # because it builds the app exactly as `main` does and then binds nothing at all.
            "src/delivery_starter/openapi.py": "openapi_export.py",
            "tests/edge/test_http_app.py": "tests/test_http_app.py",
            "tests/test_logging_setup.py": "tests/test_logging_setup.py",
            "tests/test_settings.py": "tests/test_settings.py",
            "tests/test_tracing.py": "tests/test_tracing.py",
        },
        "keycloak": {
            "src/delivery_starter/adapters/driving/http/auth/oidc_keycloak.py": "oidc_keycloak.py",
            "tests/auth/test_oidc_keycloak.py": "tests/test_oidc_keycloak.py",
        },
        "users-keycloak": {
            "src/delivery_starter/adapters/driving/http/users/oidc_keycloak.py": "users_oidc_keycloak.py",
            "tests/users/test_users_oidc_keycloak.py": "tests/test_users_oidc_keycloak.py",
        },
    },
    # Go keeps a package's tests beside its code, so there is no separate tests/ tree here. The
    # `.sql` migrations come from `../sql/`, shared with the Python backend: one schema, one
    # copy, because two copies of an event-log schema drift and nothing would notice.
    "go": {
        "memory": {
            "application/ports/events/events.go": "events.go",
            "adapters/driven/eventstorememory/store.go": "event_store_memory.go",
            "adapters/driven/eventstorememory/store_test.go": "event_store_memory_test.go",
            "eventstorecontract/contract.go": "event_store_contract.go",
        },
        "sqlite": {
            "adapters/driven/eventstoresqlite/store.go": "event_store_sqlite.go",
            "adapters/driven/eventstoresqlite/store_test.go": "event_store_sqlite_test.go",
        },
        "postgres": {
            "adapters/driven/eventstorepostgres/store.go": "event_store_postgres.go",
            "adapters/driven/eventstorepostgres/store_integration_test.go": "event_store_postgres_integration_test.go",
            "cmd/migrate/main.go": "migrate_main.go",
            "cmd/migrate/main_test.go": "migrate_main_test.go",
            # embed.go (+ keep) is what puts the .sql files into the ko-built migrate image; without
            # it the command reads an empty working directory even when the repository has .sql files.
            # `keep` lets //go:embed compile when there are not yet any migrations.
            "migrations/embed.go": "migrations_embed.go",
            "migrations/keep": "migrations_keep",
            "migrations/001_events.sql": "../sql/001_events.sql",
            "migrations/002_events_append_only.sql": "../sql/002_events_append_only.sql",
        },
        "net-http": {
            "adapters/driving/http/app.go": "http_app.go",
            "adapters/driving/http/app_test.go": "http_app_test.go",
            # What a browser meets before any route does. A wrapper rather than part of the mux:
            # a preflight is a question about a request, and no route has an answer to it.
            "adapters/driving/http/security.go": "http_security.go",
            "adapters/driving/http/security_test.go": "http_security_test.go",
            # The contract the routes above make, published as a file — there is no generator on this
            # backend and buying one would cost the dependency it exists without. `openapi_test.go` is
            # what holds the two together.
            "adapters/driving/http/openapi_test.go": "http_openapi_test.go",
            "openapi.yaml": "openapi.yaml",
            # The environment's one struct. A package rather than a block in `cmd/serve`, because
            # checking the environment is a rule with values that pass and values that do not, and
            # `cmd/serve` is the one package in the service that has no test.
            "config/config.go": "config.go",
            "config/config_test.go": "config_test.go",
            # The SDK's wiring, under the transport for the same reason: a span per request is the
            # one thing only a transport can produce.
            "observability/tracing.go": "tracing.go",
            "observability/tracing_test.go": "tracing_test.go",
            "cmd/serve/main.go": "serve_main.go",
        },
        "keycloak": {
            "adapters/driving/http/auth/oidckeycloak/oidckeycloak.go": "oidc_keycloak.go",
            "adapters/driving/http/auth/oidckeycloak/oidckeycloak_test.go": "oidc_keycloak_test.go",
        },
        "users-keycloak": {
            "adapters/driving/http/users/userskeycloak/userskeycloak.go": "users_oidc_keycloak.go",
            "adapters/driving/http/users/userskeycloak/userskeycloak_test.go": "users_oidc_keycloak_test.go",
        },
    },
    # Maven's layout, which is why every path is longer than the others': production code under
    # `src/main/java`, tests under `src/test/java`, both mirroring the package. Emitted under the
    # template package name; `language_files` renames the directories after the project and rewrites
    # every `package` and `import` line, which is why every path here says `deliverystarter`.
    "java-quarkus": {
        "memory": {
            f"{JAVA_PORTS}/events/Actor.java": "../java/actor.java",
            f"{JAVA_PORTS}/events/AppendResult.java": "../java/append_result.java",
            f"{JAVA_PORTS}/events/CausationId.java": "../java/causation_id.java",
            f"{JAVA_PORTS}/events/CommittedEvent.java": "../java/committed_event.java",
            f"{JAVA_PORTS}/events/CorrelationId.java": "../java/correlation_id.java",
            f"{JAVA_PORTS}/events/DomainEvent.java": "../java/domain_event.java",
            f"{JAVA_PORTS}/events/EventStore.java": "../java/event_store.java",
            f"{JAVA_PORTS}/events/EventStoreException.java": "../java/event_store_exception.java",
            f"{JAVA_PORTS}/events/EventVisitor.java": "../java/event_visitor.java",
            "src/main/java/com/example/deliverystarter/adapters/driven/eventstorememory/"
            "InMemoryEventStore.java": "../java/event_store_memory.java",
            "src/test/java/com/example/deliverystarter/eventstorecontract/EventStoreContract.java": (
                "../java/tests/event_store_contract.java"
            ),
            "src/test/java/com/example/deliverystarter/adapters/driven/eventstorememory/"
            "InMemoryEventStoreTest.java": "../java/tests/event_store_memory_test.java",
        },
        "sqlite": {
            "src/main/java/com/example/deliverystarter/adapters/driven/eventstoresqlite/"
            "SqliteEventStore.java": "../java/event_store_sqlite.java",
            "src/test/java/com/example/deliverystarter/adapters/driven/eventstoresqlite/"
            "SqliteEventStoreTest.java": "../java/tests/event_store_sqlite_test.java",
        },
        "postgres": {
            "src/main/java/com/example/deliverystarter/adapters/driven/eventstorepostgres/"
            "PostgresEventStore.java": "../java/event_store_postgres.java",
            "src/main/java/com/example/deliverystarter/config/DatabaseUrl.java": "../java/database_url.java",
            "src/main/java/com/example/deliverystarter/config/DatabaseUrlConfigSource.java": (
                "database_url_config_source.java"
            ),
            # ServiceLoader registration, which is how a config source is found before any bean
            # exists. The filename is the interface's own, so it cannot be anything else.
            "src/main/resources/META-INF/services/"
            "org.eclipse.microprofile.config.spi.ConfigSource": "config_source_registration",
            "src/main/java/com/example/deliverystarter/migrations/MigrateMain.java": "../java/migrate_main.java",
            # Flyway names migrations `V<version>__<description>.sql` and orders them by that version,
            # so the shared `.sql` files arrive under Flyway's convention rather than the numeric one
            # the other backends' own runners read. Same schema, one copy: `../sql/` is shared with
            # every SQL backend here, because two copies of an event-log schema drift and nothing
            # would notice.
            "src/main/resources/db/migration/V1__events.sql": "../sql/001_events.sql",
            "src/main/resources/db/migration/V2__events_append_only.sql": "../sql/002_events_append_only.sql",
            "src/test/java/com/example/deliverystarter/adapters/driven/eventstorepostgres/"
            "PostgresEventStoreIT.java": "tests/event_store_postgres_it.java",
            "src/test/java/com/example/deliverystarter/config/DatabaseUrlTest.java": (
                "../java/tests/database_url_test.java"
            ),
        },
        "quarkus-rest": {
            "src/main/java/com/example/deliverystarter/adapters/driving/http/SchemaFailure.java": (
                "../java/http_schema_failure.java"
            ),
            "src/main/java/com/example/deliverystarter/adapters/driving/http/NotFoundMapper.java": (
                "http_not_found_mapper.java"
            ),
            # The readiness check, not the endpoint: SmallRye Health owns the route, and this is what
            # the application contributes to it. There is deliberately no `main` here either — the
            # framework owns startup, so there is no composition root to write.
            "src/main/java/com/example/deliverystarter/adapters/driving/http/"
            "ServiceHealthCheck.java": "http_health_check.java",
            "src/test/java/com/example/deliverystarter/adapters/driving/http/HttpAppTest.java": (
                "tests/http_app_test.java"
            ),
        },
        "keycloak": {
            "src/main/java/com/example/deliverystarter/adapters/driving/http/auth/"
            "KeycloakRoles.java": "../java/oidc_keycloak.java",
            "src/main/java/com/example/deliverystarter/adapters/driving/http/auth/"
            "KeycloakGroupRoleAugmentor.java": "oidc_keycloak_augmentor.java",
            "src/test/java/com/example/deliverystarter/adapters/driving/http/auth/"
            "KeycloakRolesTest.java": "../java/tests/oidc_keycloak_test.java",
        },
        "users-keycloak": {
            "src/main/java/com/example/deliverystarter/adapters/driving/http/users/"
            "CustomerIdentity.java": "../java/users_oidc_keycloak.java",
            "src/main/java/com/example/deliverystarter/adapters/driving/http/users/"
            "CurrentCustomer.java": "users_current_customer.java",
            "src/test/java/com/example/deliverystarter/adapters/driving/http/users/"
            "CustomerIdentityTest.java": "../java/tests/users_oidc_keycloak_test.java",
        },
    },
    # Its sibling's twin, and the `../java/` sources are the point: the event port, all three store
    # adapters, the URL parser, the migration entry point, the 400 body and the group mapping are the same
    # files here, not copies of them. They name no framework type, so there is nothing for a second copy to
    # say differently — and an event-log adapter kept in two places is one this factory could watch drift
    # without noticing. What is genuinely this backend's is what touches Spring: how the datasource learns
    # its address, what serves the probe, what answers a 404, how a validated token becomes authorities, and
    # the two tests that need an application context.
    "java-spring": {
        "memory": {
            f"{JAVA_PORTS}/events/Actor.java": "../java/actor.java",
            f"{JAVA_PORTS}/events/AppendResult.java": "../java/append_result.java",
            f"{JAVA_PORTS}/events/CausationId.java": "../java/causation_id.java",
            f"{JAVA_PORTS}/events/CommittedEvent.java": "../java/committed_event.java",
            f"{JAVA_PORTS}/events/CorrelationId.java": "../java/correlation_id.java",
            f"{JAVA_PORTS}/events/DomainEvent.java": "../java/domain_event.java",
            f"{JAVA_PORTS}/events/EventStore.java": "../java/event_store.java",
            f"{JAVA_PORTS}/events/EventStoreException.java": "../java/event_store_exception.java",
            f"{JAVA_PORTS}/events/EventVisitor.java": "../java/event_visitor.java",
            "src/main/java/com/example/deliverystarter/adapters/driven/eventstorememory/"
            "InMemoryEventStore.java": "../java/event_store_memory.java",
            "src/test/java/com/example/deliverystarter/eventstorecontract/EventStoreContract.java": (
                "../java/tests/event_store_contract.java"
            ),
            "src/test/java/com/example/deliverystarter/adapters/driven/eventstorememory/"
            "InMemoryEventStoreTest.java": "../java/tests/event_store_memory_test.java",
        },
        "sqlite": {
            "src/main/java/com/example/deliverystarter/adapters/driven/eventstoresqlite/"
            "SqliteEventStore.java": "../java/event_store_sqlite.java",
            "src/test/java/com/example/deliverystarter/adapters/driven/eventstoresqlite/"
            "SqliteEventStoreTest.java": "../java/tests/event_store_sqlite_test.java",
        },
        "postgres": {
            "src/main/java/com/example/deliverystarter/adapters/driven/eventstorepostgres/"
            "PostgresEventStore.java": "../java/event_store_postgres.java",
            "src/main/java/com/example/deliverystarter/config/DatabaseUrl.java": "../java/database_url.java",
            "src/main/java/com/example/deliverystarter/config/"
            "DatabaseUrlEnvironmentPostProcessor.java": "database_url_environment_post_processor.java",
            # Spring Boot's own registration file, which is how a post-processor is found before any bean
            # exists. The filename is the interface's own, so it cannot be anything else.
            "src/main/resources/META-INF/spring/"
            "org.springframework.boot.env.EnvironmentPostProcessor.imports": "environment_post_processor_registration",
            "src/main/java/com/example/deliverystarter/migrations/MigrateMain.java": "../java/migrate_main.java",
            # Flyway's own naming convention, `V<version>__<description>.sql`, from the same shared `.sql`
            # files every other SQL backend here reads. See the note in the sibling's block.
            "src/main/resources/db/migration/V1__events.sql": "../sql/001_events.sql",
            "src/main/resources/db/migration/V2__events_append_only.sql": "../sql/002_events_append_only.sql",
            "src/test/java/com/example/deliverystarter/adapters/driven/eventstorepostgres/"
            "PostgresEventStoreIT.java": "tests/event_store_postgres_it.java",
            "src/test/java/com/example/deliverystarter/config/DatabaseUrlTest.java": (
                "../java/tests/database_url_test.java"
            ),
        },
        "spring-web": {
            "src/main/java/com/example/deliverystarter/adapters/driving/http/SchemaFailure.java": (
                "../java/http_schema_failure.java"
            ),
            "src/main/java/com/example/deliverystarter/adapters/driving/http/NotFoundAdvice.java": (
                "http_not_found_advice.java"
            ),
            # The readiness contributor, not the endpoint: Actuator owns the route, and this is what the
            # application contributes to it. The composition root is not here either — `ServiceApplication`
            # in the skeleton is the whole of it, because the framework owns startup.
            "src/main/java/com/example/deliverystarter/adapters/driving/http/"
            "ServiceHealthIndicator.java": "http_health_indicator.java",
            "src/test/java/com/example/deliverystarter/adapters/driving/http/HttpAppTest.java": (
                "tests/http_app_test.java"
            ),
        },
        "keycloak": {
            "src/main/java/com/example/deliverystarter/adapters/driving/http/auth/"
            "KeycloakRoles.java": "../java/oidc_keycloak.java",
            "src/main/java/com/example/deliverystarter/adapters/driving/http/auth/"
            "SecurityConfig.java": "oidc_keycloak_security.java",
            "src/test/java/com/example/deliverystarter/adapters/driving/http/auth/"
            "KeycloakRolesTest.java": "../java/tests/oidc_keycloak_test.java",
        },
        "users-keycloak": {
            "src/main/java/com/example/deliverystarter/adapters/driving/http/users/"
            "CustomerIdentity.java": "../java/users_oidc_keycloak.java",
            "src/main/java/com/example/deliverystarter/adapters/driving/http/users/"
            "CustomerSecurityConfig.java": "users_security.java",
            "src/test/java/com/example/deliverystarter/adapters/driving/http/users/"
            "CustomerIdentityTest.java": "../java/tests/users_oidc_keycloak_test.java",
        },
    },
}

#: What `backing_services.py` reads: every file a feature owns, whichever side of the log it is on.
SERVICE_FILES: dict[str, dict[str, dict[str, str]]] = with_read_side(WRITE_SIDE_FILES)
