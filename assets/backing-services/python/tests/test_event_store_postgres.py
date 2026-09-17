"""The event store against real Postgres.

Deliberately NOT part of `make verify`: the repository gate stays runnable with no
infrastructure, and this is the target that needs a database.

    make services-up migrate test-integration

It runs the same contract the infrastructure-free adapters pass, plus the four things only a
real store can prove: that two appends at one version produce exactly one winner, that two
conditional appends against one *boundary* do the same, that the log refuses to be rewritten, and
that a replay never runs past a position an earlier event could still commit behind.
"""

from __future__ import annotations

import os
import threading
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from contract.event_store_contract import EventStoreContract

from delivery_starter.adapters.driven.event_store_postgres import (
    create_postgres_event_store,
)
from delivery_starter.application.ports.events import (
    NO_STREAM,
    Actor,
    Appended,
    AppendResult,
    Condition,
    DomainEvent,
    EventStore,
    Recorded,
    TagFilter,
    TagQuery,
    TagsOf,
    create_correlation_id,
    default_tags_of,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def _connect() -> psycopg.Connection:
    """Open a connection, turning a refused one into the instruction that fixes it.

    Without this the first failure is a driver error, and the reader has to already know that
    the schema is applied by a separate target.
    """
    if not DATABASE_URL.strip():
        raise RuntimeError(
            "DATABASE_URL is unset, so there is no database to test against. Run "
            "`make test-integration`, which sets it, after `make services-up migrate`."
        )
    try:
        connection = psycopg.connect(DATABASE_URL)
    except psycopg.OperationalError as error:  # pragma: no cover - environment failure
        raise RuntimeError(
            f"Cannot reach the database at {DATABASE_URL}. Start it and apply the schema "
            "first:  make services-up migrate"
        ) from error
    with connection.cursor() as cursor:
        try:
            cursor.execute("SELECT 1 FROM events LIMIT 1")
        except psycopg.errors.UndefinedTable as error:  # pragma: no cover - environment
            connection.close()
            raise RuntimeError(
                "The events table does not exist. Apply the schema first:  make services-up migrate"
            ) from error
    connection.commit()
    return connection


#: One id for the whole file: these appends race each other inside one business transaction.
CORRELATION_ID = create_correlation_id(uuid.uuid4())


def _event(
    stream_id: str,
    event_type: str,
    payload: dict[str, object] | None = None,
) -> DomainEvent:
    return DomainEvent(
        type=event_type,
        schema_version=1,
        stream_id=stream_id,
        payload=payload or {},
        occurred_at="2024-01-01T00:00:00+00:00",
        actor=Actor(kind="test", id="contention"),
        correlation_id=CORRELATION_ID,
    )


def _tags(event: DomainEvent) -> tuple[str, ...]:
    """Tag an event by the seat it is claiming, which is what the boundary below is drawn out
    of. A real project's tagging function is this shape: the identifying attributes, derived."""
    seat = event.payload.get("seatId")
    return () if seat is None else (f"seat:{seat}",)


class TestPostgresEventStore(EventStoreContract):
    """The shared contract, against the real thing."""

    def make_store(self, tags_of: TagsOf = default_tags_of) -> EventStore:
        return create_postgres_event_store(_connect(), tags_of)


@pytest.fixture
def connection() -> Iterator[psycopg.Connection]:
    handle = _connect()
    try:
        yield handle
    finally:
        handle.close()


def test_exactly_one_of_many_simultaneous_first_writes_wins() -> None:
    """The assertion no infrastructure-free store can make.

    Being single-threaded, the in-memory fake serialises these calls and can never produce two
    winners, so it would pass this test while proving nothing. SQLite serialises writers for
    the same reason. Only a real store genuinely races, which is why this guarantee is proved
    here and nowhere else.
    """
    stream = f"race-{uuid.uuid4()}"
    attempts = 8

    def attempt(index: int) -> AppendResult:
        # One connection per worker: two appends on one connection cannot race, they queue.
        with psycopg.connect(DATABASE_URL) as handle:
            store = create_postgres_event_store(handle)
            return store.append(stream, NO_STREAM, [_event(stream, f"Attempt{index}")])

    with ThreadPoolExecutor(max_workers=attempts) as pool:
        results = list(pool.map(attempt, range(attempts)))

    assert [result for result in results if isinstance(result, Appended)] == [Appended(0)]
    with psycopg.connect(DATABASE_URL) as handle:
        assert len(create_postgres_event_store(handle).read(stream)) == 1
    for result in results:
        if not isinstance(result, Appended):
            assert result.actual_version == 0


def test_exactly_one_of_many_simultaneous_conditional_appends_wins() -> None:
    """The Dynamic Consistency Boundary, raced for real — and the case `expected_version` cannot
    express, because each attempt writes to a *different* stream and the thing they contend for
    is a tag they share.

    The boundary is read **once**, and all eight attempts are guarded by that one position: eight
    workers who each decided, from the same facts, that the seat was free. Exactly one may record
    it. Some lose because the winner's event is already there when they check; the rest lose to
    `SERIALIZABLE` at commit, which is reported as the same conflict and needs the same next move
    from the caller. No single-writer store can produce this situation at all, which is why the
    guarantee is proved here and nowhere else.

    Reading the head inside each worker would test something else entirely — whichever worker
    happened to read *after* the winner committed would be guarded from a position past the
    winner's event, and would rightly be allowed to write. A caller that re-reads has re-decided,
    and this test is about callers that have not.
    """
    seat = f"seat-{uuid.uuid4()}"
    query = TagQuery((TagFilter(tags=(f"seat:{seat}",)),))
    attempts = 8
    with psycopg.connect(DATABASE_URL) as handle:
        decided_at = create_postgres_event_store(handle, _tags).read_tagged(query).head

    def attempt(index: int) -> object:
        # One connection per worker: two conditional appends on one connection cannot race.
        with psycopg.connect(DATABASE_URL) as handle:
            store = create_postgres_event_store(handle, _tags)
            claim = f"claim-{seat}-{index}"
            return store.append_if(
                Condition(query, decided_at),
                [_event(claim, "SeatClaimed", {"seatId": seat})],
            )

    with ThreadPoolExecutor(max_workers=attempts) as pool:
        results = list(pool.map(attempt, range(attempts)))

    assert len([one for one in results if isinstance(one, Recorded)]) == 1
    with psycopg.connect(DATABASE_URL) as handle:
        store = create_postgres_event_store(handle, _tags)
        assert len(store.read_tagged(query).events) == 1


def test_a_replay_stops_short_of_a_position_an_earlier_event_could_still_arrive_behind() -> None:
    """The guarantee a projection's single-number checkpoint rests on, and the one bug in this
    design that leaves no trace.

    A position is assigned when a row is inserted and becomes visible when its transaction
    commits, and those are two different moments: two appends overlapping take 5 and 6, and 6 can
    commit first. A replay that hands out 6 while 5 is still in flight makes the projection record
    "next is 7", and 5 then arrives behind a checkpoint that has already passed it — a view
    missing a row, permanently, with a log that is perfectly correct and nothing anywhere
    complaining.

    So `read_all` waits for the appends in flight and stops at the last settled position. The
    reader below finishes only *after* the slow append commits, and then it sees both events in
    order. Without the protocol it would finish at once, holding the second event and not the
    first.

    Only a real store can produce this at all: the in-memory adapter is one lock and SQLite
    serialises its writers, so in neither can a position be taken and committed out of order.
    """
    slow, fast, reader = (
        create_postgres_event_store(_connect()),
        create_postgres_event_store(_connect()),
        create_postgres_event_store(_connect()),
    )
    first, second = f"slow-{uuid.uuid4()}", f"fast-{uuid.uuid4()}"
    # Where this case's own events begin: the log is shared with every other case and every
    # previous run, so a replay from zero would read all of them.
    start = reader.read_tagged(TagQuery(())).head + 1

    replayed: list[str] = []
    finished = threading.Event()

    def replay() -> None:
        replayed.extend(event.type for event in reader.read_all(start))
        finished.set()

    with slow.unit_of_work():
        slow.append(first, NO_STREAM, [_event(first, "Slow")])
        # Its position is taken; its commit is not. This one takes the next position and commits.
        fast.append(second, NO_STREAM, [_event(second, "Fast")])

        threading.Thread(target=replay, daemon=True).start()
        assert not finished.wait(timeout=1.0), (
            f"a replay finished while an append was in flight, and read {replayed}"
        )

    assert finished.wait(timeout=10), "a replay never finished after the append committed"
    assert replayed == ["Slow", "Fast"]


def test_a_conditional_append_is_refused_by_an_event_in_flight_when_the_boundary_was_read() -> None:
    """The same gap as the replay's, on the write path, where it breaks the constraint instead of a
    view — and this is the case the whole tag boundary rests on.

    Two appends take 5 and 6; 6 commits first. A decision reading a head of 6 while 5 is still
    invisible would be guarded from *after* 6 — and 5, the very event that should refuse it, sits
    below its own boundary where the guard never looks. The append is allowed, the seat is claimed
    twice, and the log looks perfectly correct afterwards.

    So a boundary is only ever a settled position: `head` waits for the appends in flight, which
    makes the read that follows see the event as well. The claim below is therefore refused, and it
    is refused by the *condition* rather than by chance.
    """
    slow, fast, decider = (
        create_postgres_event_store(_connect(), _tags),
        create_postgres_event_store(_connect(), _tags),
        create_postgres_event_store(_connect(), _tags),
    )
    seat = f"seat-{uuid.uuid4()}"
    query = TagQuery((TagFilter(tags=(f"seat:{seat}",)),))

    decided: dict[str, object] = {}
    read = threading.Event()

    def decide() -> None:
        # A decision, drawn the way every DCB caller draws one: pin the boundary, then read it.
        boundary = decider.head()
        decided["boundary"] = boundary
        decided["events"] = decider.read_tagged(query, until=boundary).events
        read.set()

    with slow.unit_of_work():
        first = f"claim-{seat}-1"
        slow.append(first, NO_STREAM, [_event(first, "SeatClaimed", {"seatId": seat})])
        # Its position is taken; its commit is not. This one takes the next position and commits.
        fast.append(f"other-{uuid.uuid4()}", NO_STREAM, [_event("other", "Unrelated")])

        threading.Thread(target=decide, daemon=True).start()
        assert not read.wait(timeout=1.0), (
            f"a boundary was drawn while an append was in flight, at {decided.get('boundary')}"
        )

    assert read.wait(timeout=10), "a boundary was never drawn after the append committed"
    # The decision now knows about the claim, which is the whole point of waiting.
    found = decided["events"]
    assert isinstance(found, list)
    assert [event.type for event in found] == ["SeatClaimed"]

    # And a caller that decided anyway is refused by the condition rather than by luck.
    refused = decider.append_if(
        Condition(query=query, after=0),
        [_event(f"claim-{seat}-2", "SeatClaimed", {"seatId": seat})],
    )
    assert not isinstance(refused, Recorded), f"expected the claim refused, got {refused}"


def test_refuses_to_let_a_committed_event_be_rewritten_or_removed(
    connection: psycopg.Connection,
) -> None:
    stream = f"append-only-{uuid.uuid4()}"
    store = create_postgres_event_store(connection)
    store.append(stream, NO_STREAM, [_event(stream, "Recorded")])

    statements = (
        ("UPDATE events SET event_type = %s WHERE stream_id = %s", ("Rewritten", stream)),
        ("DELETE FROM events WHERE stream_id = %s", (stream,)),
    )
    for statement, parameters in statements:
        with (
            pytest.raises(psycopg.errors.InsufficientPrivilege, match="append-only"),
            connection.cursor() as cursor,
        ):
            cursor.execute(statement, parameters)
        connection.rollback()

    assert [event.type for event in store.read(stream)] == ["Recorded"]
