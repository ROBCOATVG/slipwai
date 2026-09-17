"""In-memory event-store adapter.

For a quickstart with no infrastructure, and for tests that do not need to prove concurrency.
`make verify` runs the shared contract suite against this one, which is why the repository gate
needs no Docker.

It satisfies the port's contract, but understand what it cannot do: being single-threaded, it
cannot genuinely race, so it CANNOT prove that two concurrent appends at the same version
produce exactly one winner — nor that two conditional appends against one boundary do. Those
guarantees live in a real store's unique constraint and isolation level, and
`make test-integration` is where they are proved. Ship on Postgres, demo on memory.

Data is lost when the process ends, which for an event-sourced system means the entire truth
is lost. Never production.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime

from delivery_starter.application.ports.events import (
    NO_STREAM,
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
    default_tags_of,
)


class InMemoryDatabase:
    """What a connection is, when there is no database.

    It exists so the in-memory adapters can do the one thing the real ones do that matters most
    to the read side: put an append, a view write and a checkpoint in **one transaction**. Build
    the event store and the checkpoint store from the same instance — which is what
    `create_in_memory_checkpoint_store(store)` does — and `unit_of_work` covers all of it.

    Rollback is a restore from a shallow copy taken on entry. That is honest for what this is
    for: it proves the *semantics* a test needs (a failed batch changes nothing) without
    pretending to be a transaction manager. Events are frozen, so copying the list is enough;
    nothing here is shared with anything that mutates it afterwards.
    """

    def __init__(self) -> None:
        self.log: list[CommittedEvent] = []
        #: Global position to the tags it was indexed by — the derived index, kept beside the log
        #: rather than on the event, exactly as the SQL adapters keep it in a table of its own.
        self.tags: dict[int, tuple[str, ...]] = {}
        self.checkpoints: dict[str, int] = {}
        self.leases: dict[str, tuple[str, datetime]] = {}
        self._depth = 0

    @contextmanager
    def unit_of_work(self) -> Iterator[None]:
        """Re-entrant: the outermost block is the one that can roll back."""
        if self._depth:
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return
        snapshot = (list(self.log), dict(self.tags), dict(self.checkpoints), dict(self.leases))
        self._depth = 1
        try:
            yield
        except BaseException:
            self.log, self.tags, self.checkpoints, self.leases = (
                snapshot[0],
                snapshot[1],
                snapshot[2],
                snapshot[3],
            )
            raise
        finally:
            self._depth = 0

    @property
    def head(self) -> int:
        return self.log[-1].global_position if self.log else 0


class InMemoryEventStore(EventStore):
    def __init__(
        self,
        database: InMemoryDatabase | None = None,
        tags_of: TagsOf = default_tags_of,
    ) -> None:
        #: Public, because the checkpoint-store adapter is built from it: two in-memory adapters
        #: sharing one of these is the equivalent of two SQL adapters sharing one connection.
        self.database = database if database is not None else InMemoryDatabase()
        self._tags_of = tags_of

    def _stream(self, stream_id: str) -> list[CommittedEvent]:
        return [event for event in self.database.log if event.stream_id == stream_id]

    def _next_position(self) -> int:
        return self.database.head + 1

    def _record(self, event: DomainEvent, stream_id: str, version: int) -> CommittedEvent:
        committed = CommittedEvent(
            type=event.type,
            schema_version=event.schema_version,
            stream_id=stream_id,
            payload=dict(event.payload),
            occurred_at=event.occurred_at,
            actor=event.actor,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            version=version,
            global_position=self._next_position(),
            recorded_at=datetime.now(UTC).isoformat(),
        )
        self.database.log.append(committed)
        tags = tuple(self._tags_of(event))
        if tags:
            # No entry at all when the tagging function returns nothing, rather than an empty one:
            # the SQL adapters give such an event no rows, and "indexed" has to mean the same thing
            # in every adapter or `reindex_tags` answers differently depending on the store.
            self.database.tags[committed.global_position] = tags
        return committed

    def read(self, stream_id: str) -> tuple[CommittedEvent, ...]:
        return tuple(self._stream(stream_id))

    def append(
        self,
        stream_id: str,
        expected_version: int,
        events: Sequence[DomainEvent],
    ) -> AppendResult:
        stream = self._stream(stream_id)
        actual_version = stream[-1].version if stream else NO_STREAM
        if actual_version != expected_version:
            return VersionConflict(actual_version)

        version = actual_version
        with self.database.unit_of_work():
            for event in events:
                version += 1
                self._record(event, stream_id, version)
        return Appended(version)

    def read_all(self, from_position: int) -> Iterator[CommittedEvent]:
        for event in self.database.log:
            if event.global_position >= from_position:
                yield event

    def unit_of_work(self) -> AbstractContextManager[None]:
        return self.database.unit_of_work()

    def head(self) -> int:
        return self.database.head

    def read_tagged(self, query: TagQuery, after: int = 0, until: int = 0) -> TaggedRead:
        ceiling = until or self.database.head
        return TaggedRead(
            events=tuple(
                event
                for event in self.database.log
                if after < event.global_position <= ceiling
                and query.matches(event, self.database.tags.get(event.global_position, ()))
            ),
            head=ceiling,
        )

    def append_if(
        self,
        condition: Condition,
        events: Sequence[DomainEvent],
    ) -> ConditionalAppendResult:
        if self.read_tagged(condition.query, condition.after).events:
            return ConditionConflict(self.database.head)
        if not events:
            return Recorded(self.database.head)
        with self.database.unit_of_work():
            for event in events:
                # Each event still lands at the next version of the stream it names, so a
                # conditionally appended event is readable by everything written against
                # `read` and `append`. The boundary changed; the log did not.
                stream = self._stream(event.stream_id)
                self._record(
                    event,
                    event.stream_id,
                    (stream[-1].version if stream else NO_STREAM) + 1,
                )
        return Recorded(self.database.head)

    def reindex_tags(self, from_position: int = 0) -> int:
        indexed = 0
        with self.database.unit_of_work():
            for event in self.database.log:
                if event.global_position < from_position:
                    continue
                if event.global_position in self.database.tags:
                    continue
                tags = tuple(self._tags_of(_as_domain(event)))
                if not tags:
                    continue
                self.database.tags[event.global_position] = tags
                indexed += 1
        return indexed

    def retag(self, tags_of: TagsOf) -> int:
        with self.database.unit_of_work():
            self._tags_of = tags_of
            self.database.tags.clear()
            return self.reindex_tags()


def _as_domain(event: CommittedEvent) -> DomainEvent:
    """A stored event as the tagging function sees it.

    `tags_of` is written against `DomainEvent`, so it can be called on an event before it is
    appended *and* on one read back out of the log during a reindex. The two must agree —
    otherwise an index built by a rebuild differs from the one built by appends, and nothing
    would notice.
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


def create_in_memory_event_store(
    tags_of: TagsOf = default_tags_of,
    database: InMemoryDatabase | None = None,
) -> InMemoryEventStore:
    """Both arguments are optional, and a call with neither is the quickstart it always was.

    Pass `tags_of` where this project's events are findable by more than their stream, and
    `database` to build a checkpoint store on the same "connection".
    """
    return InMemoryEventStore(database=database, tags_of=tags_of)
