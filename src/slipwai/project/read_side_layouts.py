"""Which committed read-side asset lands at which path under `apps/service`, per backend.

The other half of `service_layouts.py`, in the same shape and keyed the same way, merged into
`SERVICE_FILES` there. It is a table of its own for the reason that one is a module of its own:
it is most of the bytes and none of the behaviour.

What is here is the machinery a read model is *maintained* with, as opposed to the log it is
derived from — the checkpoint port and its adapters, the catch-up runner, and the two migrations
that create the checkpoint table and the tag index. Every backend gets the same set, because an
asymmetric read side would reproduce the defect this slice exists to fix one level down: whoever
picks the language with less would build the per-request fold nobody chose.

Sources are relative to `assets/backing-services/<backend>/`, and a `../` reaches the material
shared between backends — which is how one `003_projection_checkpoints.sql` serves every SQL
adapter here instead of being written four times.
"""
from __future__ import annotations

#: Where the two ports sit in Maven's layout: under the application layer, which owns them.
JAVA_PORTS = "src/main/java/com/example/deliverystarter/application/ports"

READ_SIDE_FILES: dict[str, dict[str, dict[str, str]]] = {
    # java-quarkus: the read side is the same set of files as its sibling framework's, because the
    # event store and everything derived from it are framework-agnostic by construction — the port is
    # what makes the framework's own datasource, migrations and health check a driven adapter's problem.
    "java-quarkus": {
        "memory": {
            f"{JAVA_PORTS}/events/TagsOf.java": "../java/tags_of.java",
            f"{JAVA_PORTS}/events/TagQuery.java": "../java/tag_query.java",
            f"{JAVA_PORTS}/events/TaggedRead.java": "../java/tagged_read.java",
            f"{JAVA_PORTS}/events/Condition.java": "../java/condition.java",
            f"{JAVA_PORTS}/events/ConditionalAppendResult.java": "../java/conditional_append_result.java",
            f"{JAVA_PORTS}/readmodels/CheckpointStore.java": "../java/read_models.java",
            f"{JAVA_PORTS}/readmodels/Projection.java": "../java/projection.java",
            "src/main/java/com/example/deliverystarter/projections/Projections.java": "../java/projections.java",
            "src/main/java/com/example/deliverystarter/adapters/driven/eventstorememory/"
            "InMemoryDatabase.java": "../java/event_store_memory_database.java",
            "src/main/java/com/example/deliverystarter/adapters/driven/checkpointstorememory/"
            "InMemoryCheckpointStore.java": "../java/checkpoint_store_memory.java",
            "src/test/java/com/example/deliverystarter/checkpointstorecontract/"
            "CheckpointStoreContract.java": "../java/tests/checkpoint_store_contract.java",
            "src/test/java/com/example/deliverystarter/adapters/driven/checkpointstorememory/"
            "InMemoryCheckpointStoreTest.java": "../java/tests/checkpoint_store_memory_test.java",
            # What runs an async projection: the framework's own scheduler, ticking a catch-up pass.
            # One per framework, because `@Scheduled` is the framework's and so is how it finds the
            # project's `Projection` beans — and a hand-written worker loop is the thing this
            # replaces. Beside the runner rather than under `adapters/driving/`, because it ships with
            # the read side and everything under `adapters/driving/` goes with its transport.
            "src/main/java/com/example/deliverystarter/projections/ScheduledProjections.java": (
                "scheduled_projections.java"
            ),
            # The runner has no I/O of its own, so its suite runs whatever the store is — which is why
            # it is here under the feature every project has rather than beside an adapter.
            "src/test/java/com/example/deliverystarter/projections/ProjectionsTest.java": (
                "../java/tests/projections_test.java"
            ),
        },
        "sqlite": {
            "src/main/java/com/example/deliverystarter/adapters/driven/checkpointstoresqlite/"
            "SqliteCheckpointStore.java": "../java/checkpoint_store_sqlite.java",
            "src/test/java/com/example/deliverystarter/adapters/driven/checkpointstoresqlite/"
            "SqliteCheckpointStoreTest.java": "../java/tests/checkpoint_store_sqlite_test.java",
        },
        "postgres": {
            # The unit of work, delegated to the framework that owns transactions. The port is
            # shared with the sibling framework; `JtaTransactions` is the one class in the project that
            # names a transaction API, which is why there is one per framework and no `ThreadLocal`
            # anywhere. It is here rather than in the write-side table because the seam exists for
            # the read side: an inline view and an async checkpoint both have to commit inside
            # somebody else's transaction, and the framework is what binds a connection to one.
            "src/main/java/com/example/deliverystarter/adapters/driven/sql/Transactions.java": (
                "../java/transactions.java"
            ),
            "src/main/java/com/example/deliverystarter/adapters/driven/sql/JtaTransactions.java": (
                "jta_transactions.java"
            ),
            "src/main/java/com/example/deliverystarter/adapters/driven/checkpointstorepostgres/"
            "PostgresCheckpointStore.java": "../java/checkpoint_store_postgres.java",
            # Flyway orders by the version in the name, so the shared `.sql` files arrive under its
            # convention rather than the numeric one the other backends' runners read.
            "src/main/resources/db/migration/V3__projection_checkpoints.sql": "../sql/003_projection_checkpoints.sql",
            "src/main/resources/db/migration/V4__event_tags.sql": "../sql/004_event_tags.sql",
            "src/test/java/com/example/deliverystarter/adapters/driven/checkpointstorepostgres/"
            "PostgresCheckpointStoreIT.java": "tests/checkpoint_store_postgres_it.java",
        },
    },
    # java-spring: the read side is the same set of files as its sibling framework's, because the
    # event store and everything derived from it are framework-agnostic by construction — the port is
    # what makes the framework's own datasource, migrations and health check a driven adapter's problem.
    "java-spring": {
        "memory": {
            f"{JAVA_PORTS}/events/TagsOf.java": "../java/tags_of.java",
            f"{JAVA_PORTS}/events/TagQuery.java": "../java/tag_query.java",
            f"{JAVA_PORTS}/events/TaggedRead.java": "../java/tagged_read.java",
            f"{JAVA_PORTS}/events/Condition.java": "../java/condition.java",
            f"{JAVA_PORTS}/events/ConditionalAppendResult.java": "../java/conditional_append_result.java",
            f"{JAVA_PORTS}/readmodels/CheckpointStore.java": "../java/read_models.java",
            f"{JAVA_PORTS}/readmodels/Projection.java": "../java/projection.java",
            "src/main/java/com/example/deliverystarter/projections/Projections.java": "../java/projections.java",
            "src/main/java/com/example/deliverystarter/adapters/driven/eventstorememory/"
            "InMemoryDatabase.java": "../java/event_store_memory_database.java",
            "src/main/java/com/example/deliverystarter/adapters/driven/checkpointstorememory/"
            "InMemoryCheckpointStore.java": "../java/checkpoint_store_memory.java",
            "src/test/java/com/example/deliverystarter/checkpointstorecontract/"
            "CheckpointStoreContract.java": "../java/tests/checkpoint_store_contract.java",
            "src/test/java/com/example/deliverystarter/adapters/driven/checkpointstorememory/"
            "InMemoryCheckpointStoreTest.java": "../java/tests/checkpoint_store_memory_test.java",
            # What runs an async projection: the framework's own scheduler, ticking a catch-up pass.
            # One per framework, because `@Scheduled` is the framework's and so is how it finds the
            # project's `Projection` beans — and a hand-written worker loop is the thing this
            # replaces. Beside the runner rather than under `adapters/driving/`, because it ships with
            # the read side and everything under `adapters/driving/` goes with its transport.
            "src/main/java/com/example/deliverystarter/adapters/driving/projections/"
            "ScheduledProjections.java": "scheduled_projections.java",
            # The runner has no I/O of its own, so its suite runs whatever the store is — which is why
            # it is here under the feature every project has rather than beside an adapter.
            "src/test/java/com/example/deliverystarter/projections/ProjectionsTest.java": (
                "../java/tests/projections_test.java"
            ),
        },
        "sqlite": {
            "src/main/java/com/example/deliverystarter/adapters/driven/checkpointstoresqlite/"
            "SqliteCheckpointStore.java": "../java/checkpoint_store_sqlite.java",
            "src/test/java/com/example/deliverystarter/adapters/driven/checkpointstoresqlite/"
            "SqliteCheckpointStoreTest.java": "../java/tests/checkpoint_store_sqlite_test.java",
        },
        "postgres": {
            # The unit of work, delegated to the framework that owns transactions. The port is
            # shared with the sibling framework; `SpringTransactions` is the one class in the project that
            # names a transaction API, which is why there is one per framework and no `ThreadLocal`
            # anywhere. It is here rather than in the write-side table because the seam exists for
            # the read side: an inline view and an async checkpoint both have to commit inside
            # somebody else's transaction, and the framework is what binds a connection to one.
            "src/main/java/com/example/deliverystarter/adapters/driven/sql/Transactions.java": (
                "../java/transactions.java"
            ),
            "src/main/java/com/example/deliverystarter/adapters/driven/sql/SpringTransactions.java": (
                "spring_transactions.java"
            ),
            "src/main/java/com/example/deliverystarter/adapters/driven/checkpointstorepostgres/"
            "PostgresCheckpointStore.java": "../java/checkpoint_store_postgres.java",
            # Flyway orders by the version in the name, so the shared `.sql` files arrive under its
            # convention rather than the numeric one the other backends' runners read.
            "src/main/resources/db/migration/V3__projection_checkpoints.sql": "../sql/003_projection_checkpoints.sql",
            "src/main/resources/db/migration/V4__event_tags.sql": "../sql/004_event_tags.sql",
            "src/test/java/com/example/deliverystarter/adapters/driven/checkpointstorepostgres/"
            "PostgresCheckpointStoreIT.java": "tests/checkpoint_store_postgres_it.java",
        },
    },

    # Go keeps a package's tests beside its code, so there is no separate tests/ tree here.
    "go": {
        "memory": {
            # The timer that drives an async projection. Go has no framework to own a loop, so this
            # is the loop and the context that ends it: `Ticker.Run` blocks like everything
            # long-running in the standard library, and `cmd/serve` starts it beside the server under
            # the same cancelled context. In the runner's own package, and importing no transport.
            "projections/ticker.go": "projections_ticker.go",
            "projections/ticker_test.go": "projections_ticker_test.go",
            "application/ports/readmodels/readmodels.go": "read_models.go",
            "projections/projections.go": "projections.go",
            "projections/projections_test.go": "projections_test.go",
            "adapters/driven/checkpointstorememory/store.go": "checkpoint_store_memory.go",
            "adapters/driven/checkpointstorememory/store_test.go": "checkpoint_store_memory_test.go",
            "checkpointstorecontract/contract.go": "checkpoint_store_contract.go",
        },
        "sqlite": {
            "adapters/driven/checkpointstoresqlite/store.go": "checkpoint_store_sqlite.go",
            "adapters/driven/checkpointstoresqlite/store_test.go": "checkpoint_store_sqlite_test.go",
        },
        "postgres": {
            "adapters/driven/checkpointstorepostgres/store.go": "checkpoint_store_postgres.go",
            "adapters/driven/checkpointstorepostgres/store_integration_test.go": (
                "checkpoint_store_postgres_integration_test.go"
            ),
            "migrations/003_projection_checkpoints.sql": "../sql/003_projection_checkpoints.sql",
            "migrations/004_event_tags.sql": "../sql/004_event_tags.sql",
        },
    },
    "typescript": {
        "memory": {
            # The timer that drives an async projection: a Fastify plugin, so the framework starts it
            # and `onClose` stops it. Beside the read side rather than under `adapters/driving/`, and
            # its host typed structurally rather than imported, for one reason: this ships with the
            # event store, and a project can have a store and no HTTP adapter at all — where an
            # import of `fastify` would not compile and everything under `adapters/driving/` is gone
            # with the transport that owned it.
            "src/projections-plugin.ts": "projections-plugin.ts",
            "tests/contract/projections-plugin.test.ts": "tests/projections-plugin.test.ts",
            "src/application/ports/read-models.ts": "read-models.ts",
            "src/projections.ts": "projections.ts",
            "src/adapters/driven/checkpoint-store-memory.ts": "checkpoint-store-memory.ts",
            "tests/contract/checkpoint-store-contract.ts": "tests/checkpoint-store-contract.ts",
            "tests/contract/checkpoint-store-memory.test.ts": "tests/checkpoint-store-memory.test.ts",
            # The runner has no I/O of its own, so its suite runs whatever the store is — which is why
            # it is here under the feature every project has rather than beside an adapter.
            "tests/contract/projections.test.ts": "tests/projections.test.ts",
        },
        "sqlite": {
            "src/adapters/driven/checkpoint-store-sqlite.ts": "checkpoint-store-sqlite.ts",
            "tests/contract/checkpoint-store-sqlite.test.ts": "tests/checkpoint-store-sqlite.test.ts",
        },
        "postgres": {
            # Beside the event store's own `index.ts`, because it is built from it and pruned with it.
            "src/adapters/driven/event-store-postgres/checkpoint-store-postgres.ts": "checkpoint-store-postgres.ts",
            "tests/integration/checkpoint-store-postgres.test.ts": "tests/checkpoint-store-postgres.test.ts",
            "migrations/003_projection_checkpoints.js": "migrations/003_projection_checkpoints.js",
            "migrations/004_event_tags.js": "migrations/004_event_tags.js",
        },
    },
    # Emitted under the template package name; `language_files` renames the directory after the
    # project and rewrites the imports, which is why every path here says `delivery_starter`.
    "python": {
        "memory": {
            # The timer that drives an async projection: a FastAPI lifespan, so the framework starts
            # it with the app and stops it with the app — and shutdown waits for the pass in flight
            # rather than killing it mid-transaction. Beside the read side, and importing FastAPI
            # nowhere, for the same reason as its TypeScript sibling: a project can have a store and
            # no HTTP adapter at all.
            "src/delivery_starter/projections_lifespan.py": "projections_lifespan.py",
            "tests/contract/test_projections_lifespan.py": "tests/test_projections_lifespan.py",
            "src/delivery_starter/application/ports/read_models.py": "read_models.py",
            "src/delivery_starter/projections.py": "projections.py",
            "src/delivery_starter/adapters/driven/checkpoint_store_memory.py": "checkpoint_store_memory.py",
            "tests/contract/checkpoint_store_contract.py": "tests/checkpoint_store_contract.py",
            "tests/contract/test_checkpoint_store_memory.py": "tests/test_checkpoint_store_memory.py",
            # The runner has no I/O of its own, so its suite runs whatever the store is — which is
            # why it is here under the feature every project has rather than beside an adapter.
            "tests/contract/test_projections.py": "tests/test_projections.py",
        },
        "sqlite": {
            "src/delivery_starter/adapters/driven/checkpoint_store_sqlite.py": "checkpoint_store_sqlite.py",
            "tests/contract/test_checkpoint_store_sqlite.py": "tests/test_checkpoint_store_sqlite.py",
        },
        "postgres": {
            "src/delivery_starter/adapters/driven/checkpoint_store_postgres.py": "checkpoint_store_postgres.py",
            "tests/integration/test_checkpoint_store_postgres.py": "tests/test_checkpoint_store_postgres.py",
            "migrations/003_projection_checkpoints.sql": "../sql/003_projection_checkpoints.sql",
            "migrations/004_event_tags.sql": "../sql/004_event_tags.sql",
        },
    },
}


def with_read_side(
    write_side: dict[str, dict[str, dict[str, str]]],
) -> dict[str, dict[str, dict[str, str]]]:
    """The write side's table with this one folded into it, feature by feature.

    A merge rather than one literal in `service_layouts.py` because each table is already most
    of a module's bytes, and interleaving them would put half of this file in the middle of that
    one. The keys cannot collide: a path names one file, and each side ships its own.
    """
    return {
        backend: {
            feature: {**files, **READ_SIDE_FILES.get(backend, {}).get(feature, {})}
            for feature, files in features.items()
        }
        for backend, features in write_side.items()
    }
