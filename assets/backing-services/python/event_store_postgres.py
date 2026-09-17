"""Postgres event-store adapter — the only file that knows the event log is SQL.

Two boundaries live here, and the second one is optional. `append` guards one stream with its
version and is what every generated slice uses; `append_if` guards a **tag query** and is how a
constraint that spans entities is held without a process manager. The factory's
`docs/adr/0001-a-dcb-capable-log.md` records why both are here.

Concurrency for `append` is enforced twice over, deliberately:

  1. Each insert carries a `WHERE (SELECT MAX(version) ...) = expected` guard, which catches a
     stale expectation — a caller that decided against version 3 while the stream moved to 5.
  2. The `(stream_id, version)` unique constraint catches the true race, where two
     transactions both pass the guard and then try to write the same version.

The guard alone is insufficient (two concurrent transactions see the same MAX under READ
COMMITTED), and the constraint alone is insufficient (a stale expectation could write a valid
*later* version without conflict). Both are needed.

`append_if` cannot use either of those, because there is no version to compare: what it must
prove is that *nothing matching a query* arrived since the caller read. It asks Postgres for
`SERIALIZABLE` and lets the database prove it. The cost is a real one and it is the caller's: a
serialisation failure is reported as a conflict, and the caller re-reads and re-decides exactly
as it does for a stale version.

This adapter takes one connection and owns its transactions **unless** a `unit_of_work` is open,
in which case it commits nothing and the block does. A pool belongs in the composition root,
which is the only place allowed to open connections — and a pool is what makes the concurrency
guarantee observable, since two simultaneous appends need two connections to race.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:  # pragma: no cover - typing only
    # Imported for typing only, so nothing loads the driver until a composition root actually
    # opens a connection. That is what keeps `make verify` free of infrastructure while this
    # file is still linted and byte-compiled.
    from psycopg import Connection

INSERT_GUARDED = """
  INSERT INTO events (
    stream_id, version, event_type, schema_version, payload, actor,
    correlation_id, causation_id, occurred_at
  )
  SELECT %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::uuid, %s::uuid, %s::timestamptz
  WHERE (SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = %s) = %s
  RETURNING global_position
"""

EVENT_COLUMNS = """
  global_position, stream_id, version, event_type, schema_version, payload, actor,
  correlation_id, causation_id, occurred_at, recorded_at
"""

READ_STREAM = f"SELECT {EVENT_COLUMNS} FROM events WHERE stream_id = %s ORDER BY version ASC"

READ_ALL_BATCH = f"""
  SELECT {EVENT_COLUMNS}
  FROM events
  WHERE global_position >= %s AND global_position <= %s
  ORDER BY global_position ASC
  LIMIT %s
"""

#: The log's own advisory lock, which is how a reader learns that a position is settled.
#:
#: A global position is assigned when a row is inserted and becomes visible when its transaction
#: commits, and those are not the same moment: two appends overlapping can take 5 and 6 and commit
#: 6 first. A reader that sees 6 and records "next is 7" has skipped 5 for good, because 5 arrives
#: behind a checkpoint that has already passed it. Nothing in the log is wrong afterwards, and the
#: view is missing a row nothing will ever put back.
#:
#: So an append takes this lock in **shared** mode before its first insert, which costs nothing
#: because shared holders do not block each other, and `read_all` takes it **exclusively** for one
#: `MAX(global_position)` query. Acquiring it exclusively means no append is between its insert and
#: its commit, so every position at or below that maximum is final: committed and visible, or
#: aborted and gone for good. Reading no further than that is what makes a single number a safe
#: place for a projection to resume from.
#:
#: The number is arbitrary and only has to be the same in every adapter that opens this log. It
#: must not be reused for anything else in the same database, which is why it lives here.
EVENTS_LOCK = 8_317_231

#: Take the log's lock in shared mode, so appends never block each other.
LOCK_SHARED = "SELECT pg_advisory_xact_lock_shared(%s)"

#: Take it exclusively, which waits for every append in flight to finish.
LOCK_EXCLUSIVE = "SELECT pg_advisory_xact_lock(%s)"

#: Wait for every append in flight, then report the position past which nothing can still arrive.
#:
#: Two statements rather than one, because the order in which Postgres evaluates a lock function
#: beside an aggregate is not something to rely on. The transaction ends immediately afterwards, so
#: the exclusive hold lasts microseconds — long enough to prove nothing is in flight, short enough
#: that the appends queueing behind it barely notice.
SETTLED_POSITION = "SELECT COALESCE(MAX(global_position), 0) FROM events"

CURRENT_VERSION = "SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = %s"

HEAD = "SELECT COALESCE(MAX(global_position), 0) FROM events"

INSERT_TAG = """
  INSERT INTO event_tags (tag, global_position) VALUES (%s, %s)
  ON CONFLICT DO NOTHING
"""

DELETE_TAGS = "DELETE FROM event_tags"

UNINDEXED_EVENTS = f"""
  SELECT {EVENT_COLUMNS}
  FROM events
  WHERE global_position >= %s
    AND NOT EXISTS (SELECT 1 FROM event_tags WHERE global_position = events.global_position)
  ORDER BY global_position ASC
  LIMIT %s
"""

#: Batched so a rebuild over a long log does not materialise the whole thing in memory.
READ_ALL_BATCH_SIZE = 500


def _instant(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _to_committed_event(row: Sequence[Any]) -> CommittedEvent:
    """Parse a stored row back into a CommittedEvent.

    Events are validated on read as well as on write, because stored events outlive the code
    that wrote them.

    A *tolerant* reader on purpose: unknown payload fields written by a newer version are
    carried through rather than rejected, which is what makes a rolling deploy possible. Only
    the envelope is required. The `uuid` columns come back as `uuid.UUID` already, and are still
    put through the same value-type factory the other adapters use — one parse point, so a
    driver that decides to hand back text instead changes nothing above this line.
    """
    (
        position,
        stream_id,
        version,
        event_type,
        schema_version,
        payload,
        actor,
        correlation_id,
        causation_id,
        occurred_at,
        recorded_at,
    ) = row
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(actor, str):
        actor = json.loads(actor)
    if not isinstance(payload, dict):
        raise ValueError(f"event at global_position {position} has a non-object payload")
    if schema_version != 1:
        raise ValueError(
            f"event at global_position {position} is schema version {schema_version}; "
            "add an upcaster for it before reading it as version 1"
        )
    if not isinstance(actor, dict) or "kind" not in actor or "id" not in actor:
        raise ValueError(f"event at global_position {position} has no usable actor")
    return CommittedEvent(
        type=event_type,
        schema_version=1,
        stream_id=stream_id,
        payload=payload,
        occurred_at=_instant(occurred_at),
        actor=Actor(kind=str(actor["kind"]), id=str(actor["id"])),
        correlation_id=create_correlation_id(correlation_id),
        causation_id=None if causation_id is None else create_causation_id(causation_id),
        version=version,
        global_position=int(position),
        recorded_at=_instant(recorded_at),
    )


def _tag_query_sql(query: TagQuery) -> tuple[str, list[object]]:
    """A `TagQuery` as a SQL predicate over `e`, plus its parameters.

    `TagQuery.matches` in the port is the definition; this is its translation, and the contract
    suite is what holds the two to each other. Every SQL adapter carries its own copy of this
    translation, in whatever placeholder syntax its driver wants, deliberately duplicated rather
    than shared: an adapter that imports another adapter is two adapters that cannot be pruned
    apart.

      * a filter's tags are a **conjunction** — the number of its tags found against the event
        must equal how many it named, because `IN` on its own is an "any of" and a much weaker
        guard than the caller asked for;
      * its types narrow within that filter only;
      * a filter naming neither, and a query with no filters at all, match nothing: `1 = 0`
        rather than a missing predicate, because an absent guard matches everything and a
        conditional append that matched everything would refuse every write in the system.
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
            parts.append(
                "(SELECT COUNT(*) FROM event_tags t WHERE t.global_position = e.global_position"
                " AND t.tag = ANY(%s)) = %s"
            )
            parameters.append(list(one.tags))
            parameters.append(len(set(one.tags)))
        if one.types:
            parts.append("e.event_type = ANY(%s)")
            parameters.append(list(one.types))
        predicates.append("(" + " AND ".join(parts) + ")")
    return "(" + " OR ".join(predicates) + ")", parameters


class _Stale(Exception):
    """The stream is not where the caller thought it was.

    Raised inside the unit of work so the transaction unwinds, and turned straight back into a
    `VersionConflict` value outside it. A `return` from inside the block would commit the
    half-written append it is refusing.
    """


class _ConditionBroken(Exception):
    """The same, for a conditional append: something matching the condition arrived since."""


class PostgresEventStore(EventStore):
    def __init__(
        self,
        connection: Connection[Any],
        tags_of: TagsOf = default_tags_of,
    ) -> None:
        self._connection = connection
        self._tags_of = tags_of
        self._depth = 0

    @property
    def connection(self) -> Connection[Any]:
        """The composition root's connection, for a sibling adapter to write through.

        An `inline` read model and a projection's checkpoint have to land in the same transaction
        as the append, and a second connection cannot do that however carefully it is called.
        `create_postgres_checkpoint_store(store)` takes this.
        """
        return self._connection

    @contextmanager
    def unit_of_work(self, serializable: bool = False) -> Iterator[None]:
        """One transaction, shared by this store and anything else on its connection.

        Outside one, every method here commits itself exactly as it always has. Inside one,
        none of them does, and leaving the block commits once.

        Nesting uses a SAVEPOINT rather than a counter that shrugs: an inner block that fails has
        to undo its own writes and no more. In Postgres it also has to, and not only ought to —
        a failed statement poisons the whole transaction until something rolls back to a
        savepoint, so without this an inner failure would take the outer commit with it.

        `serializable` asks for the isolation `append_if` needs. It can only be set as the
        transaction opens, so an `append_if` called *inside* somebody else's unit of work runs at
        that transaction's isolation level — open it with `serializable=True` when a conditional
        append is going to happen inside it.
        """
        if self._depth:
            self._depth += 1
            name = f"uow_{self._depth}"
            self._execute(f"SAVEPOINT {name}")
            try:
                yield
            except BaseException:
                self._execute(f"ROLLBACK TO SAVEPOINT {name}")
                raise
            else:
                self._execute(f"RELEASE SAVEPOINT {name}")
            finally:
                self._depth -= 1
            return
        if serializable:
            # The first statement of the transaction, which is the only place Postgres accepts
            # it. `psycopg` opens the transaction with it.
            self._execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        self._depth = 1
        try:
            yield
        except BaseException:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()
        finally:
            self._depth = 0

    def _execute(self, statement: str, parameters: Sequence[Any] = ()) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(statement, tuple(parameters))

    def finish_a_read(self) -> None:
        """End a read's transaction — unless a unit of work owns it, in which case it ends when
        the block does.

        Reads commit rather than leaving a transaction idle, which is what holds a connection's
        snapshot open and blocks vacuum. Public because the checkpoint adapter on this
        connection has reads of its own and has to make the same call.
        """
        if not self._depth:
            self._connection.commit()

    def _current_version(self, stream_id: str) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute(CURRENT_VERSION, (stream_id,))
            row = cursor.fetchone()
        return int(row[0]) if row is not None else -1

    def _hold_the_log(self) -> None:
        """Hold the log in shared mode until this transaction ends — see `EVENTS_LOCK`.

        Before the first insert, always, and re-entrant: taking it twice in one transaction is free.
        Shared, so two appends never wait for each other; what waits is a reader asking whether a
        position has settled.
        """
        with self._connection.cursor() as cursor:
            cursor.execute(LOCK_SHARED, (EVENTS_LOCK,))

    def _head(self) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute(HEAD)
            row = cursor.fetchone()
        return int(row[0]) if row is not None else 0

    def read(self, stream_id: str) -> tuple[CommittedEvent, ...]:
        with self._connection.cursor() as cursor:
            cursor.execute(READ_STREAM, (stream_id,))
            rows = cursor.fetchall()
        self.finish_a_read()
        return tuple(_to_committed_event(row) for row in rows)

    def append(
        self,
        stream_id: str,
        expected_version: int,
        events: Sequence[DomainEvent],
    ) -> AppendResult:
        if not events:
            return Appended(expected_version)

        # Imported here rather than at module scope for the same reason `Connection` above is a
        # typing-only import: the driver is loaded only by a process that talks to a database.
        from psycopg.errors import UniqueViolation

        try:
            with self.unit_of_work():
                self._hold_the_log()
                version = expected_version
                for event in events:
                    guard_against = version
                    version += 1
                    self._insert(event, stream_id, version, guard_against)
                return Appended(version)
        except _Stale:
            # The guard failed: the stream is not where the caller thought.
            return VersionConflict(self._version_after_a_conflict(stream_id))
        except UniqueViolation:
            # The true race: another transaction committed the same version between our guard
            # and our insert. Reported as a conflict, not raised — contention is expected.
            return VersionConflict(self._version_after_a_conflict(stream_id))

    def _version_after_a_conflict(self, stream_id: str) -> int:
        version = self._current_version(stream_id)
        self.finish_a_read()
        return version

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
        with self._connection.cursor() as cursor:
            cursor.execute(
                INSERT_GUARDED,
                (
                    stream_id,
                    version,
                    event.type,
                    event.schema_version,
                    json.dumps(dict(event.payload)),
                    json.dumps({"kind": event.actor.kind, "id": event.actor.id}),
                    event.correlation_id,
                    event.causation_id,
                    event.occurred_at,
                    stream_id,
                    guard_against,
                ),
            )
            if cursor.rowcount == 0:
                raise _Stale
            row = cursor.fetchone()
            position = int(row[0]) if row is not None else self._head()
            for tag in self._tags_of(event):
                cursor.execute(INSERT_TAG, (tag, position))

    def read_all(self, from_position: int) -> Iterator[CommittedEvent]:
        """Replay in global order, and never past a position that is not settled yet.

        The ceiling is taken once, at the start: an event appended while a long replay is running
        belongs to the next pass, and a checkpoint that stopped short of it loses nothing.
        """
        settled = self._settled_position()
        position = from_position
        while position <= settled:
            with self._connection.cursor() as cursor:
                cursor.execute(READ_ALL_BATCH, (position, settled, READ_ALL_BATCH_SIZE))
                rows = cursor.fetchall()
            self.finish_a_read()
            if not rows:
                return
            for row in rows:
                yield _to_committed_event(row)
            position = int(rows[-1][0]) + 1

    def _settled_position(self) -> int:
        """The highest position nothing earlier can still be committed behind — see `EVENTS_LOCK`.

        Read at this connection's default isolation on purpose: the lock has to be taken *before*
        the snapshot that reads the maximum, and under REPEATABLE READ or SERIALIZABLE the snapshot
        would predate it. Neither this nor `read_all` runs inside a conditional append, which is the
        only thing here that raises the isolation level — and `head` does not ask for a settled
        position inside a unit of work at all, so this never waits on a lock its own transaction
        holds.
        """
        with self._connection.cursor() as cursor:
            cursor.execute(LOCK_EXCLUSIVE, (EVENTS_LOCK,))
            cursor.execute(SETTLED_POSITION)
            row = cursor.fetchone()
        self.finish_a_read()
        return int(row[0]) if row is not None else 0

    def head(self) -> int:
        """The last **settled** position, which is the only kind a decision may be guarded at.

        The same protocol `read_all` uses, and for a reason that took a reproduction to see: a
        boundary past an event that is still in flight is a boundary the guard cannot check. Two
        appends take 5 and 6, 6 commits first, a decision reads a head of 6 while 5 is invisible —
        and `append_if(condition, after=6)` then looks for anything matching *after* 6 and never
        sees 5, because 5 is below its own boundary. The append is allowed, and the constraint it
        was supposed to hold is broken with a correct-looking log to show for it.

        Waiting for the appends in flight fixes it twice over: the boundary is one nothing can
        arrive behind, and the read that follows sees the very events the decision has to know
        about.

        Inside a unit of work this connection already holds, the answer is this transaction's own
        view instead — a caller reading its own writes rather than drawing a boundary, which is what
        an inline read model does. Asking for the settled position there would wait on a lock this
        transaction is itself holding.
        """
        if self._depth:
            head = self._head()
            self.finish_a_read()
            return head
        return self._settled_position()

    def read_tagged(self, query: TagQuery, after: int = 0, until: int = 0) -> TaggedRead:
        predicate, parameters = _tag_query_sql(query)
        ceiling = until or self.head()
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {EVENT_COLUMNS} FROM events e"
                f" WHERE e.global_position > %s AND e.global_position <= %s AND {predicate}"
                " ORDER BY e.global_position ASC",
                (after, ceiling, *parameters),
            )
            rows = cursor.fetchall()
        self.finish_a_read()
        return TaggedRead(events=tuple(_to_committed_event(row) for row in rows), head=ceiling)

    def append_if(
        self,
        condition: Condition,
        events: Sequence[DomainEvent],
    ) -> ConditionalAppendResult:
        """Append only if nothing matching the condition arrived since the caller read.

        `SERIALIZABLE`, not a clever `WHERE NOT EXISTS`: the guard is the *absence* of rows, and
        absence is what no lock in a row-locking database can hold. Postgres detects the conflict
        at commit and raises a serialisation failure, which is reported here as a conflict —
        because for the caller it is the same fact and the same next move, re-read and re-decide.
        """
        from psycopg.errors import SerializationFailure

        try:
            with self.unit_of_work(serializable=True):
                self._hold_the_log()
                if self._matching(condition):
                    raise _ConditionBroken
                for event in events:
                    # Each event still lands at the next version of the stream it names, so
                    # everything written against `read` and `append` keeps working: what the
                    # condition replaced is the *guard*, not the shape of the log.
                    at = self._current_version(event.stream_id)
                    self._insert(event, event.stream_id, at + 1, at)
                return Recorded(self._head())
        except (_ConditionBroken, SerializationFailure):
            return ConditionConflict(self._head_after_a_conflict())

    def _head_after_a_conflict(self) -> int:
        head = self._head()
        self.finish_a_read()
        return head

    def _matching(self, condition: Condition) -> bool:
        predicate, parameters = _tag_query_sql(condition.query)
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT 1 FROM events e WHERE e.global_position > %s AND {predicate} LIMIT 1",
                (condition.after, *parameters),
            )
            return cursor.fetchone() is not None

    def reindex_tags(self, from_position: int = 0) -> int:
        """Index what this store's tagging function has not indexed yet, a batch at a time.

        Resumable on purpose: a project adopting tags runs this over a log that may be very long,
        and a run that dies halfway is continued by running it again rather than started over.
        """
        indexed = 0
        position = from_position
        while True:
            with self.unit_of_work():
                with self._connection.cursor() as cursor:
                    cursor.execute(UNINDEXED_EVENTS, (position, READ_ALL_BATCH_SIZE))
                    rows = cursor.fetchall()
                if not rows:
                    return indexed
                for row in rows:
                    event = _to_committed_event(row)
                    tags = self._tags_of(_as_domain(event))
                    if not tags:
                        # Counted only when it made the event findable. An event with no tags is
                        # re-read by every later run, which is a scan and not a rewrite, and the
                        # alternative is a count that never reaches zero.
                        continue
                    with self._connection.cursor() as cursor:
                        for tag in tags:
                            cursor.execute(INSERT_TAG, (tag, event.global_position))
                    indexed += 1
                position = int(rows[-1][0]) + 1

    def retag(self, tags_of: TagsOf) -> int:
        with self.unit_of_work():
            self._tags_of = tags_of
            self._execute(DELETE_TAGS)
            # Inside this unit of work, so the old index is never visible as gone: either the
            # whole re-index commits or the old one stands.
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


def create_postgres_event_store(
    connection: Connection[Any],
    tags_of: TagsOf = default_tags_of,
) -> PostgresEventStore:
    """`tags_of` is what this project's events are findable by; the default is the event's own
    stream, which is what makes the tag index a superset of what the log already had."""
    return PostgresEventStore(connection, tags_of)
