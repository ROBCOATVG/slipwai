"""What each backend's entry point writes for each event-store answer.

A table and none of the mechanism, split from `composition.py` for the reason `service_layouts.py` is split
from `backing_services.py`: this is most of that module's bytes and none of its behaviour, and a module
holding both outgrows what anybody wants to read at once. Every string below is read by `wire_store` there,
which is also where the three rules these all follow are written down.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntryStore:
    """One transport's entry point: where it is, and what each event-store answer writes into it.

    `imports` and `open` are keyed by the feature that answered the axis — `None` for the in-memory answer,
    which owns no feature and needs no marked region because nothing can ever prune it away. `absent` is
    what the whole file reads as in a project with no event store at all, which is every project on the
    standard profile: no import, nothing opened, and `readiness()` given nothing.
    """

    entry: str
    imports: dict[str | None, str]
    open: dict[str | None, str]
    argument: str
    absent: str = ""
    #: What the entry point's own import of the HTTP adapter names, where the answer changes it. Keyed
    #: like the two above, plus `"none"` for a project that has no event store at all.
    app_imports: dict[str | None, str] | None = None
    #: And of the module holding the checked environment, for a backend whose opener is annotated with its
    #: type. Keyed the same way; an answer with no opener names nothing extra, because an import nothing
    #: uses is what a generated project's own linter refuses first.
    settings_imports: dict[str | None, str] | None = None
    #: The blank lines this language wants between what was opened and what follows it — one everywhere,
    #: two in Python, where a top-level `def` is expected to have them.
    gap: str = "\n"


#: Every answer that opens a store: the in-memory one, which owns no feature, and each feature the axis
#: offers. `"none"` — the axis never asked — is the row the tables below spell out on its own.
STORED: tuple[str | None, ...] = (None, "sqlite", "postgres")

#: What the marker names until `wire_store` fills it in with the key the region was found under. The
#: feature is a *key* in every table below and never an argument: a feature name a function is called with
#: is one line away from one a branch tests for, the defect these tables exist to have stopped.
FEATURE = "__FEATURE__"


def marked(body: str, indent: str = "") -> str:
    """`body` inside its answer's marked region, so the pruner takes the two away together; `indent` is
    what a region inside a function needs, since a comment at column zero there reads as the end of it."""
    lines = "".join(f"{line}\n" for line in body.splitlines())
    return (
        f"{indent}// backing-service:{FEATURE}:begin\n{lines}"
        f"{indent}// backing-service:{FEATURE}:end\n"
    )


def hash_marked(body: str, indent: str = "") -> str:
    """The same, for a file whose comments start with `#`; `indent` is what a region inside a function
    needs, since a stray comment at column zero would close the block a reader sees."""
    lines = "".join(f"{line}\n" for line in body.splitlines())
    return (
        f"{indent}# backing-service:{FEATURE}:begin\n{lines}{indent}# backing-service:{FEATURE}:end\n"
    )


def tab_marked(body: str) -> str:
    """The same, for Go's tab-indented import block."""
    lines = "".join(f"{line}\n" for line in body.splitlines())
    return f"\t// backing-service:{FEATURE}:begin\n{lines}\t// backing-service:{FEATURE}:end\n"


# ── TypeScript ────────────────────────────────────────────────────────────────────────────────────────

TYPESCRIPT_MEMORY_IMPORT = (
    "import { createInMemoryEventStore } from './adapters/driven/event-store-memory.js';\n"
)
# Beside the store imports because Biome sorts the whole block, and its path falls between adapter and port.
TYPESCRIPT_APP_IMPORT = "import { buildApp, readiness } from './adapters/driving/http/app.js';\n"
TYPESCRIPT_PORT_IMPORT = (
    "import type { EventStore } from './application/ports/events.js';\nimport type { Config } from './config.js';\n"
)
TYPESCRIPT_OPEN_HEAD = """// The event store this project answered the event-store question with, opened once and handed to
// whatever needs it. Nothing else in this service constructs one.
//
// It takes the checked environment rather than reading `process.env`: `@fastify/env` populates
// `app.config` while the app boots, so `readiness` calls this once from inside `after`, which is where
// that exists — and `src/config.ts` stays the one place this service's variables are checked.
//
// The marked block is the answer; delete it — which is what `./init --event-store memory` does — and the
// in-memory store below is what is left. Both states are valid at once, which is what a prune needs,
// because pruning only ever subtracts.
function openEventStore(config: Config): EventStore {
  let store: EventStore | undefined;
"""
TYPESCRIPT_OR_MEMORY = """  store ??= createInMemoryEventStore();
  return store;
}
"""

TYPESCRIPT = EntryStore(
    entry="src/main.ts",
    imports={
        # No event-store axis, and the adapter import still has to land: without this row `tsc` saw
        # neither `buildApp` nor `readiness`.
        "none": TYPESCRIPT_APP_IMPORT,
        None: TYPESCRIPT_MEMORY_IMPORT + TYPESCRIPT_APP_IMPORT,
        "sqlite": TYPESCRIPT_MEMORY_IMPORT
        + marked(
            "import { openSqliteEventStore } from './adapters/driven/event-store-sqlite.js';",
        )
        + TYPESCRIPT_APP_IMPORT
        + TYPESCRIPT_PORT_IMPORT,
        "postgres": marked("import { Pool } from 'pg';")
        + TYPESCRIPT_MEMORY_IMPORT
        + marked(
            "import { createPostgresEventStore } from "
            "'./adapters/driven/event-store-postgres/index.js';",
        )
        + TYPESCRIPT_APP_IMPORT
        + TYPESCRIPT_PORT_IMPORT,
    },
    open={
        None: (
            "// The event store this project answered the event-store question with, opened once and\n"
            "// handed to whatever needs it. Nothing else in this service constructs one — and it is\n"
            "// `readiness` that calls this, once, as the app boots.\n"
            "function openEventStore() {\n"
            "  return createInMemoryEventStore();\n"
            "}\n"
        ),
        "sqlite": TYPESCRIPT_OPEN_HEAD
        + marked(
            "  store = openSqliteEventStore(config.EVENT_STORE_PATH);",
            indent="  ",
        )
        + TYPESCRIPT_OR_MEMORY,
        "postgres": TYPESCRIPT_OPEN_HEAD
        + marked(
            "  // `pg` connects lazily, so this opens no socket while the app is booting: an\n"
            "  // unreachable database shows up as `/ready` answering 503, which is what it is.\n"
            "  const pool = new Pool({ connectionString: config.DATABASE_URL });\n"
            "  // A pool emits `error` when an *idle* client's connection dies — the database\n"
            "  // restarted, a failover, somebody stopped the container. That is an EventEmitter\n"
            "  // error, so leaving it unhandled takes this process down with it, and a service that\n"
            "  // dies when its database blinks is one a platform crash-loops instead of taking out\n"
            "  // of the pool for a moment. The pool discards that client and opens another by\n"
            "  // itself; all this owes is somewhere to say so, and `/ready` reports the rest.\n"
            "  pool.on('error', (failure) => {\n"
            "    const line = { level: 50, msg: 'the event store connection failed', "
            "err: String(failure) };\n"
            "    process.stderr.write(`${JSON.stringify(line)}\\n`);\n"
            "  });\n"
            "  store = createPostgresEventStore(pool);",
            indent="  ",
        )
        + TYPESCRIPT_OR_MEMORY,
    },
    argument="openEventStore",
)


# ── Python ────────────────────────────────────────────────────────────────────────────────────────────

PYTHON_MEMORY_IMPORT = (
    "from .adapters.driven.event_store_memory import create_in_memory_event_store\n"
)
PYTHON_OPEN_HEAD = "def open_event_store(settings: Settings) -> ReadinessProbe:\n"
PYTHON_OPENER_DOC = '''    """The event store this project answered the event-store question with, opened once, here,
    and handed to whatever needs it. Nothing else in this service constructs one.

    It takes the checked environment rather than reading `os.environ`: `settings.py` is where
    this service's variables are held to a shape, and a store reading the environment itself
    would be a second place they are read from.
'''
PYTHON_PRUNE_DOC = """
    The marked block is the answer; delete it — which is what `./init --event-store memory`
    does — and the in-memory store below is what is left, so both states are valid at once.

    The adapter is imported inside that block rather than at the top of this module — the one
    import in this project that is not at the top. A marked region in the import block is a pair
    of comments the import sorter will not leave where they were put, and an import `ruff --fix`
    has moved out of its region is one a prune leaves behind naming a file it just deleted.
"""
PYTHON_DECLARE = "    store: ReadinessProbe | None = None\n"
PYTHON_OR_MEMORY = """    if store is None:
        store = create_in_memory_event_store()
    return store
"""
PYTHON_ON_DEMAND = '''class _PostgresOnDemand:
    """The Postgres store, opened on the first probe rather than as this process starts.

    psycopg connects while the connection object is being built, so opening the store as this
    service starts would take the process down whenever the database is not up yet — a crash
    loop where a platform wanted a task that reports "not ready" and joins the pool when the
    database comes back, and an image `make smoke-image` could never start on its own. This
    moves *when* the store is opened and nothing else: it is still opened once, by this
    composition root, and kept.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._store: ReadinessProbe | None = None

    def head(self) -> int:
        if self._store is None:
            import psycopg

            from .adapters.driven.event_store_postgres import create_postgres_event_store

            self._store = create_postgres_event_store(psycopg.connect(self._url))
        try:
            return self._store.head()
        except Exception:
            # A connection that has died stays dead — psycopg does not reconnect one — so it is
            # dropped here and the next probe opens another. Without this, a database that came
            # back would leave the service reporting not ready until somebody restarted it.
            self._store = None
            raise
'''

PYTHON = EntryStore(
    entry="src/delivery_starter/main.py",
    # Every answer imports the in-memory store: the marked region falls back to it, and it is the whole
    # of the answer where the axis was answered with `memory`.
    imports=dict.fromkeys(STORED, PYTHON_MEMORY_IMPORT),
    open={
        # The same head as every other answer — `main` opens the store one way — over an environment
        # the in-memory store needs nothing from.
        None: PYTHON_OPEN_HEAD
        + PYTHON_OPENER_DOC
        + '    """\n'
        + "    return create_in_memory_event_store()\n",
        "sqlite": PYTHON_OPEN_HEAD
        + PYTHON_OPENER_DOC
        + PYTHON_PRUNE_DOC
        + '    """\n'
        + PYTHON_DECLARE
        + hash_marked(
            "    from .adapters.driven.event_store_sqlite import open_sqlite_event_store\n"
            "\n"
            "    store = open_sqlite_event_store(settings.event_store_path)",
            indent="    ",
        )
        + PYTHON_OR_MEMORY,
        # The class in a region of its own above the opener, so the line inside the opener reads as the
        # one thing the answer contributes there. Two regions naming one feature is not nesting, and the
        # pair prunes as one. The two blank lines the opener wants above it are *inside* the region, so
        # the prune takes them with the class rather than leaving blank lines nothing put there.
        "postgres": hash_marked(PYTHON_ON_DEMAND.rstrip("\n") + "\n\n\n")
        + PYTHON_OPEN_HEAD
        + PYTHON_OPENER_DOC
        + PYTHON_PRUNE_DOC
        + '    """\n'
        + PYTHON_DECLARE
        + hash_marked(
            '    store = _PostgresOnDemand(settings.database_url or "")',
            indent="    ",
        )
        + PYTHON_OR_MEMORY,
    },
    argument="open_event_store(settings)",
    gap="\n\n",
    # Two rows each: all either turns on is whether there is an opener, whose return type is
    # `ReadinessProbe` and whose parameter is `Settings`, so both arrive with it and with nothing else.
    app_imports={
        "none": "SERVICE_NAME, build_app, readiness",
        **dict.fromkeys(STORED, "SERVICE_NAME, ReadinessProbe, build_app, readiness"),
    },
    settings_imports={
        "none": "ConfigurationError, load_settings",
        **dict.fromkeys(STORED, "ConfigurationError, Settings, load_settings"),
    },
)


# ── Go ────────────────────────────────────────────────────────────────────────────────────────────────

GO_MEMORY_IMPORT = '\t"example.com/delivery-starter/adapters/driven/eventstorememory"\n'
GO_PORT_IMPORT = '\t"example.com/delivery-starter/application/ports/events"\n'
GO_FALLBACK = """	// The event store this project answered the event-store question with, opened once and handed to
	// whatever needs it — from the checked environment rather than from os.Getenv, because `config` is
	// where this service's variables are held to a shape.
	//
	// The marked block is the answer; delete it — which is what `./init --event-store memory` does —
	// and the in-memory store it starts as is what is left — no nil check a marked block makes never-true (SA4023).
	var store events.Store = eventstorememory.New()
"""
# Go has no `*_OR_MEMORY` tail: its fallback is the declaration *above* the region, already assigned.

GO = EntryStore(
    entry="cmd/serve/main.go",
    imports={
        None: f"\n{GO_MEMORY_IMPORT}",
        "sqlite": "\n"
        + GO_MEMORY_IMPORT
        + tab_marked(
            '\t"example.com/delivery-starter/adapters/driven/eventstoresqlite"',
        )
        + GO_PORT_IMPORT,
        "postgres": "\n"
        + GO_MEMORY_IMPORT
        + tab_marked(
            '\t"example.com/delivery-starter/adapters/driven/eventstorepostgres"',
        )
        + GO_PORT_IMPORT
        + tab_marked('\t"github.com/jackc/pgx/v5/pgxpool"'),
    },
    open={
        None: (
            "\t// The event store this project answered the event-store question with, opened once, here,\n"
            "\t// and handed to whatever needs it. Nothing else in this service constructs one.\n"
            "\tstore := eventstorememory.New()\n\n"
        ),
        "sqlite": GO_FALLBACK
        + tab_marked(
            "\tsqliteStore, err := eventstoresqlite.Open(settings.EventStorePath)\n"
            "\tif err != nil {\n"
            "\t\treturn err\n"
            "\t}\n"
            "\tdefer sqliteStore.Close()\n"
            "\tstore = sqliteStore",
        ),
        "postgres": GO_FALLBACK
        + tab_marked(
            "\t// pgxpool connects lazily, so this opens no socket while the process is starting: an\n"
            "\t// unreachable database shows up as /ready answering 503, which is what it is. A bad\n"
            "\t// connection string is a different thing and does stop the process, because nothing\n"
            "\t// about it will get better on its own — though `config` has already refused the\n"
            "\t// shapes it can name.\n"
            "\tpool, err := pgxpool.New(ctx, settings.DatabaseURL)\n"
            "\tif err != nil {\n"
            "\t\treturn err\n"
            "\t}\n"
            "\tdefer pool.Close()\n"
            "\tstore = eventstorepostgres.New(pool)",
        ),
    },
    argument="store",
    absent="nil",
)


ENTRY_STORES: dict[str, EntryStore] = {
    "typescript": TYPESCRIPT,
    "python": PYTHON,
    "go": GO,
}
