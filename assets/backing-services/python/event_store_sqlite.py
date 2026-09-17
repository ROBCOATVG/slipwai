"""SQLite event-store adapter — a real append-only log in one file, no container to run.

Chosen when durability matters and infrastructure does not: a single-process service, a CLI, a
long-running worker, or a demo that must survive a restart.

Understand the one thing it cannot do before adopting it: **SQLite serialises writers**. It
proves durability and it proves the append-only rule, but it CANNOT prove concurrent
behaviour, because it never genuinely races. If the never-write-the-same-version-twice
guarantee matters to your product, prove it on Postgres — `make test-integration` there races
two appends at one version and requires exactly one winner.

`sqlite3` is the standard library, so this adapter adds no dependency and no build step.

Unlike Postgres, the schema ships with the adapter rather than as a migration: an embedded
database is created by the process that opens it, so there is no separate `make migrate` step
and nothing to run before the first test. The first schema change you make in anger is the
moment to add a real migration tool. The three tables below are the same three the Postgres
migrations create — the log, the projection checkpoints, and the derived tag index — because two
spellings of one schema drift and nothing notices.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from delivery_starter.application.ports.events import (
    Actor,
    Appended,
    AppendResult,
    CommittedEvent,
    Condition,
    ConditionalAppendResult,
    ConditionConflict,
    DomainEvent,
    EventStore,
    Recorded,
    TaggedRead,
    TagQuery,
    TagsOf,
    VersionConflict,
    create_causation_id,
    create_correlation_id,
    default_tags_of,
)

# `global_position` is INTEGER PRIMARY KEY, which in SQLite aliases the monotonic rowid — the
# read_all ordering the port promises. The append-only guarantee is enforced in the database
# rather than in this file, because a rule the application enforces is a rule the next process
# to open the file will not.
SCHEMA = """
  CREATE TABLE IF NOT EXISTS events (
    global_position INTEGER PRIMARY KEY,
    stream_id       TEXT    NOT NULL,
    version         INTEGER NOT NULL,
    event_type      TEXT    NOT NULL,
    schema_version  INTEGER NOT NULL,
    payload         TEXT    NOT NULL,
    actor           TEXT    NOT NULL,
    -- SQLite has no UUID type, so the canonical text form is what is stored. Postgres uses a
    -- real `uuid` column; both round-trip through the same value type, and the adapter is where
    -- that difference stops.
    correlation_id  TEXT    NOT NULL,
    causation_id    TEXT,
    occurred_at     TEXT    NOT NULL,
    recorded_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CONSTRAINT events_stream_version_unique UNIQUE (stream_id, version),
    CONSTRAINT events_version_non_negative CHECK (version >= 0)
  );

  CREATE INDEX IF NOT EXISTS events_stream_id_version ON events (stream_id, version);

  CREATE TRIGGER IF NOT EXISTS events_reject_update
  BEFORE UPDATE ON events
  BEGIN
    SELECT RAISE(ABORT, 'events is append-only: UPDATE is rejected');
  END;

  CREATE TRIGGER IF NOT EXISTS events_reject_delete
  BEFORE DELETE ON events
  BEGIN
    SELECT RAISE(ABORT, 'events is append-only: DELETE is rejected');
  END;

  -- Where each projection has got to. Mutable by design, and deliberately with no trigger: a
  -- checkpoint is a position that moves, and everything derived from the log can be thrown away
  -- and rebuilt. The lease columns are how exactly one worker advances it, with an expiry so
  -- that survives the worker dying.
  CREATE TABLE IF NOT EXISTS projection_checkpoints (
    projection        TEXT    PRIMARY KEY,
    position          INTEGER NOT NULL DEFAULT 0,
    lease_owner       TEXT,
    lease_expires_at  TEXT,
    updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    CONSTRAINT projection_checkpoints_position_non_negative CHECK (position >= 0),
    CONSTRAINT projection_checkpoints_lease_is_whole CHECK (
      (lease_owner IS NULL) = (lease_expires_at IS NULL)
    )
  );

  -- The tag index — the Dynamic Consistency Boundary's half of the log. Derived from the events
  -- by this project's tagging function, written inside the append's own transaction, and
  -- rebuildable at any time, which is what lets a running project adopt tags without rewriting
  -- a log it is forbidden to rewrite.
  CREATE TABLE IF NOT EXISTS event_tags (
    tag             TEXT    NOT NULL,
    global_position INTEGER NOT NULL REFERENCES events (global_position),
    PRIMARY KEY (tag, global_position)
  );

  CREATE INDEX IF NOT EXISTS event_tags_global_position ON event_tags (global_position);
"""

INSERT_GUARDED = """
  INSERT INTO events (
    stream_id, version, event_type, schema_version, payload, actor,
    correlation_id, causation_id, occurred_at
  )
  SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
  WHERE (SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = ?) = ?
"""

EVENT_COLUMNS = """
  global_position, stream_id, version, event_type, schema_version, payload, actor,
  correlation_id, causation_id, occurred_at, recorded_at
"""

READ_STREAM = f"SELECT {EVENT_COLUMNS} FROM events WHERE stream_id = ? ORDER BY version ASC"

READ_ALL_BATCH = f"""
  SELECT {EVENT_COLUMNS}
  FROM events
  WHERE global_position >= ?
  ORDER BY global_position ASC
  LIMIT ?
"""

CURRENT_VERSION = "SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = ?"

HEAD = "SELECT COALESCE(MAX(global_position), 0) FROM events"

INSERT_TAG = "INSERT OR IGNORE INTO event_tags (tag, global_position) VALUES (?, ?)"

DELETE_TAGS = "DELETE FROM event_tags"

UNINDEXED_EVENTS = f"""
  SELECT {EVENT_COLUMNS}
  FROM events
  WHERE global_position >= ?
    AND NOT EXISTS (SELECT 1 FROM event_tags WHERE global_position = events.global_position)
  ORDER BY global_position ASC
"""

#: Batched so a rebuild over a long log does not materialise the whole thing in memory.
READ_ALL_BATCH_SIZE = 500


def _to_committed_event(row: sqlite3.Row) -> CommittedEvent:
    """Parse a stored row back into a CommittedEvent.

    Events are validated on read as well as on write, because stored events outlive the code
    that wrote them — a type annotation says nothing about a row written eighteen months ago.

    This is a *tolerant* reader on purpose: unknown payload fields written by a newer version
    are carried through rather than rejected, which is what makes a rolling deploy possible.
    Only the envelope itself is required — and the envelope's ids are parsed as UUIDs here
    rather than passed through as text, so a row that SQLite was happy to store cannot enter the
    domain as an identifier nothing can correlate.
    """
    position = row["global_position"]
    payload = json.loads(row["payload"])
    if not isinstance(payload, dict):
        raise ValueError(f"event at global_position {position} has a non-object payload")
    if row["schema_version"] != 1:
        raise ValueError(
            f"event at global_position {position} is schema version {row['schema_version']}; "
            "add an upcaster for it before reading it as version 1"
        )
    actor = json.loads(row["actor"])
    if not isinstance(actor, dict) or "kind" not in actor or "id" not in actor:
        raise ValueError(f"event at global_position {position} has no usable actor")
    return CommittedEvent(
        type=row["event_type"],
        schema_version=1,
        stream_id=row["stream_id"],
        payload=payload,
        occurred_at=row["occurred_at"],
        actor=Actor(kind=str(actor["kind"]), id=str(actor["id"])),
        correlation_id=create_correlation_id(row["correlation_id"]),
        causation_id=(
            None if row["causation_id"] is None else create_causation_id(row["causation_id"])
        ),
        version=row["version"],
        global_position=position,
        recorded_at=row["recorded_at"],
    )


def _tag_query_sql(query: TagQuery) -> tuple[str, list[object]]:
    """A `TagQuery` as a SQL predicate over `e`, plus its parameters.

    The port's `TagQuery.matches` is the definition; this is a translation of it, and the
    contract suite is what holds the two to each other. Every branch here has a case there:

      * a filter's tags are a **conjunction**, so the count of its tags found against the event
        must equal how many it named — `IN` alone would be an "any of", which is a different and
        much weaker guard;
      * a filter's types narrow within that filter, never across the query;
      * a filter naming neither matches nothing, and a query with no filters matches nothing.
        `1 = 0` rather than an omitted predicate, because an absent guard would match everything
        and a conditional append that matched everything would refuse every write in the system.
    """
    if not query.filters:
        return "1 = 0", []
    predicates: list[str] = []
    parameters: list[object] = []
    for one in query.filters:
        if not one.tags and not one.types:
            predicates.append("1 = 0")
            continue
        parts: list[str] = []
        if one.tags:
            placeholders = ", ".join("?" for _ in one.tags)
            parts.append(
                f"(SELECT COUNT(*) FROM event_tags t WHERE t.global_position = e.global_position"
                f" AND t.tag IN ({placeholders})) = ?"
            )
            parameters.extend(one.tags)
            parameters.append(len(set(one.tags)))
        if one.types:
            placeholders = ", ".join("?" for _ in one.types)
            parts.append(f"e.event_type IN ({placeholders})")
            parameters.extend(one.types)
        predicates.append("(" + " AND ".join(parts) + ")")
    return "(" + " OR ".join(predicates) + ")", parameters


class _Stale(Exception):
    """The stream is not where the caller thought it was.

    Raised inside the unit of work so the transaction unwinds, caught immediately outside it and
    turned back into a `VersionConflict` value. A `return` from inside the block would commit the
    half-written append it is refusing.
    """


class _ConditionBroken(Exception):
    """The same, for a conditional append: something matching the condition arrived since."""


class SqliteEventStore(EventStore):
    def __init__(self, location: str, tags_of: TagsOf = default_tags_of) -> None:
        # `isolation_level=None` hands transaction control to this adapter: the driver's
        # implicit BEGIN/COMMIT would wrap each statement separately, and an append of several
        # events has to be one transaction or a stale expectation could leave half a decision
        # written.
        self._connection = sqlite3.connect(location, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        # WAL lets readers run while a writer holds the write lock, and is a no-op for
        # ':memory:'. FULL synchronous is the default and is what makes a committed append
        # survive a power loss; anything weaker trades the D in ACID for throughput, which an
        # event log cannot afford.
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(SCHEMA)
        self._tags_of = tags_of
        self._depth = 0

    @property
    def connection(self) -> sqlite3.Connection:
        """The one connection, for a sibling adapter to write through.

        Public deliberately: an `inline` read model and a projection's checkpoint have to land in
        the same transaction as the append, and a second connection cannot do that however
        carefully it is called. `create_sqlite_checkpoint_store(store)` takes this.
        """
        return self._connection

    def close(self) -> None:
        self._connection.close()

    @contextmanager
    def unit_of_work(self) -> Iterator[None]:
        """One transaction, shared by this store and anything else on its connection.

        Outside one, `append` commits itself exactly as it always has. Inside one, it does not,
        and leaving the block commits everything once.

        Nesting uses a SAVEPOINT rather than a counter that shrugs: an inner block that fails has
        to undo its own writes and no more, and the alternative — leaving them in the outer
        transaction — would let a refused append pollute a transaction that goes on to commit.
        """
        if self._depth:
            self._depth += 1
            name = f"uow_{self._depth}"
            self._connection.execute(f"SAVEPOINT {name}")
            try:
                yield
            except BaseException:
                self._connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
                raise
            else:
                self._connection.execute(f"RELEASE SAVEPOINT {name}")
            finally:
                self._depth -= 1
            return
        self._connection.execute("BEGIN IMMEDIATE")
        self._depth = 1
        try:
            yield
        except BaseException:
            self._connection.execute("ROLLBACK")
            raise
        else:
            self._connection.execute("COMMIT")
        finally:
            self._depth = 0

    def _current_version(self, stream_id: str) -> int:
        row = self._connection.execute(CURRENT_VERSION, (stream_id,)).fetchone()
        return int(row[0]) if row is not None else -1

    def read(self, stream_id: str) -> tuple[CommittedEvent, ...]:
        rows = self._connection.execute(READ_STREAM, (stream_id,)).fetchall()
        return tuple(_to_committed_event(row) for row in rows)

    def append(
        self,
        stream_id: str,
        expected_version: int,
        events: Sequence[DomainEvent],
    ) -> AppendResult:
        if not events:
            return Appended(expected_version)

        try:
            with self.unit_of_work():
                version = expected_version
                for event in events:
                    guard_against = version
                    version += 1
                    self._insert(event, stream_id, version, guard_against)
                return Appended(version)
        except _Stale:
            # A conflict is a return value rather than a raised exception, because contention is
            # expected under load, not exceptional. The transaction has already unwound.
            return VersionConflict(self._current_version(stream_id))
        except sqlite3.IntegrityError:
            # The unique constraint caught what the guard could not. On SQLite this is close to
            # unreachable — `BEGIN IMMEDIATE` takes the write lock for the whole append, so two
            # appends cannot interleave between guard and insert. It is handled anyway, and
            # reported the way Postgres reports it, so moving to Postgres is a change of
            # adapter rather than a change of caller.
            return VersionConflict(self._current_version(stream_id))

    def _insert(
        self,
        event: DomainEvent,
        stream_id: str,
        version: int,
        guard_against: int,
    ) -> None:
        """One event, plus its tags, inside whatever transaction is open.

        The tags go in here rather than in a pass of their own, which is the whole design: an
        index written after the append could be missing when the next conditional append checks
        it, and that append would then be guarded by a boundary with a hole in it.
        """
        cursor = self._connection.execute(
            INSERT_GUARDED,
            (
                stream_id,
                version,
                event.type,
                event.schema_version,
                json.dumps(dict(event.payload)),
                json.dumps({"kind": event.actor.kind, "id": event.actor.id}),
                str(event.correlation_id),
                None if event.causation_id is None else str(event.causation_id),
                event.occurred_at,
                stream_id,
                guard_against,
            ),
        )
        if cursor.rowcount == 0:
            raise _Stale
        position = cursor.lastrowid
        for tag in self._tags_of(event):
            self._connection.execute(INSERT_TAG, (tag, position))

    def read_all(self, from_position: int) -> Iterator[CommittedEvent]:
        position = from_position
        while True:
            rows = self._connection.execute(
                READ_ALL_BATCH, (position, READ_ALL_BATCH_SIZE)
            ).fetchall()
            if not rows:
                return
            for row in rows:
                yield _to_committed_event(row)
            position = int(rows[-1]["global_position"]) + 1

    def _head(self) -> int:
        row = self._connection.execute(HEAD).fetchone()
        return int(row[0]) if row is not None else 0

    def head(self) -> int:
        return self._head()

    def read_tagged(self, query: TagQuery, after: int = 0, until: int = 0) -> TaggedRead:
        predicate, parameters = _tag_query_sql(query)
        ceiling = until or self._head()
        rows = self._connection.execute(
            f"SELECT {EVENT_COLUMNS} FROM events e"
            f" WHERE e.global_position > ? AND e.global_position <= ? AND {predicate}"
            " ORDER BY e.global_position ASC",
            [after, ceiling, *parameters],
        ).fetchall()
        return TaggedRead(
            events=tuple(_to_committed_event(row) for row in rows),
            head=ceiling,
        )

    def append_if(
        self,
        condition: Condition,
        events: Sequence[DomainEvent],
    ) -> ConditionalAppendResult:
        """The conditional append. SQLite gives the isolation for free.

        `BEGIN IMMEDIATE` takes the write lock before the condition is checked and holds it
        through the inserts, and SQLite has one writer at a time, so the check and the write
        cannot be split by another transaction. Postgres has to ask for `SERIALIZABLE` to get
        the same thing, and pays for it with a retry path; here there is nothing to retry.
        """
        try:
            with self.unit_of_work():
                if self._matching(condition):
                    raise _ConditionBroken
                for event in events:
                    # Each event still lands at the next version of the stream it names, so
                    # everything written against `read` and `append` keeps working: what the
                    # condition replaced is the *guard*, not the shape of the log.
                    at = self._current_version(event.stream_id)
                    self._insert(event, event.stream_id, at + 1, at)
                return Recorded(self._head())
        except _ConditionBroken:
            return ConditionConflict(self._head())

    def _matching(self, condition: Condition) -> bool:
        predicate, parameters = _tag_query_sql(condition.query)
        row = self._connection.execute(
            f"SELECT 1 FROM events e WHERE e.global_position > ? AND {predicate} LIMIT 1",
            [condition.after, *parameters],
        ).fetchone()
        return row is not None

    def reindex_tags(self, from_position: int = 0) -> int:
        indexed = 0
        with self.unit_of_work():
            for row in self._connection.execute(UNINDEXED_EVENTS, (from_position,)).fetchall():
                event = _to_committed_event(row)
                tags = self._tags_of(_as_domain(event))
                if not tags:
                    # Counted only when it made the event findable. An event this project's tagging
                    # function has nothing to say about stays unindexed for good, so a run that
                    # counted it would promise an index with nothing in it and never settle at zero.
                    continue
                for tag in tags:
                    self._connection.execute(INSERT_TAG, (tag, event.global_position))
                indexed += 1
        return indexed

    def retag(self, tags_of: TagsOf) -> int:
        with self.unit_of_work():
            self._tags_of = tags_of
            self._connection.execute(DELETE_TAGS)
            return self.reindex_tags()


def _as_domain(event: CommittedEvent) -> DomainEvent:
    """A stored event as the tagging function sees it.

    `tags_of` is written against `DomainEvent`, so it can be called on an event on its way in
    *and* on one read back out during a reindex. The two have to agree, or an index built by a
    rebuild would differ from the one built by appends and nothing would notice.
    """
    return DomainEvent(
        type=event.type,
        schema_version=event.schema_version,
        stream_id=event.stream_id,
        payload=event.payload,
        occurred_at=event.occurred_at,
        actor=event.actor,
        correlation_id=event.correlation_id,
        causation_id=event.causation_id,
    )


def open_sqlite_event_store(
    location: str,
    tags_of: TagsOf = default_tags_of,
) -> SqliteEventStore:
    """Open (or create) a SQLite-backed event store.

    `location` is a file path, or `':memory:'` for a store that exists only as long as the
    process — which is what the contract suite uses, so the same SQL runs in `make verify`
    with nothing installed.

    `tags_of` is what this project's events are findable by; the default is the event's own
    stream, which is what makes the tag index a superset of what the log already had.
    """
    return SqliteEventStore(location, tags_of)
