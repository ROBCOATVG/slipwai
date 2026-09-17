"""The shared contract, against SQLite, plus the two things only a file can prove.

This runs in `make verify` and needs no Docker — an embedded database is created by the process that
opens it, so there is nothing to start and nothing to migrate.

`:memory:` for the contract, because the contract is about behaviour and a fresh database per test
is what keeps its cases independent. That the log survives the process, and that the database itself
refuses to be rewritten, need a real file and are below.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest
from contract.event_store_contract import EventStoreContract

from delivery_starter.adapters.driven.event_store_sqlite import (
    open_sqlite_event_store,
)
from delivery_starter.application.ports.events import (
    NO_STREAM,
    Actor,
    Appended,
    DomainEvent,
    EventStore,
    TagsOf,
    VersionConflict,
    create_correlation_id,
    default_tags_of,
)


class TestSqliteEventStore(EventStoreContract):
    def make_store(self, tags_of: TagsOf = default_tags_of) -> EventStore:
        return open_sqlite_event_store(":memory:", tags_of)


#: One id for the whole file: these writes are about durability, and a correlation id that changed
#: per event would say they belonged to different business transactions, which they do not.
CORRELATION_ID = create_correlation_id(uuid.uuid4())


def _event(stream_id: str, event_type: str) -> DomainEvent:
    return DomainEvent(
        type=event_type,
        schema_version=1,
        stream_id=stream_id,
        payload={"step": event_type},
        occurred_at="2024-01-01T00:00:00+00:00",
        actor=Actor(kind="test", id="durability"),
        correlation_id=CORRELATION_ID,
    )


@pytest.fixture
def location(tmp_path: Path) -> str:
    return str(tmp_path / "events.sqlite3")


def test_keeps_the_log_across_a_close_and_reopen(location: str) -> None:
    """The whole reason to choose SQLite over the in-memory adapter."""
    first = open_sqlite_event_store(location)
    first.append("order-1", NO_STREAM, [_event("order-1", "Placed")])
    first.close()

    reopened = open_sqlite_event_store(location)
    try:
        events = reopened.read("order-1")
        assert [event.type for event in events] == ["Placed"]
        assert events[0].version == 0
    finally:
        reopened.close()


def test_continues_the_stream_at_the_right_version_after_a_restart(location: str) -> None:
    first = open_sqlite_event_store(location)
    first.append("order-1", NO_STREAM, [_event("order-1", "Placed")])
    first.close()

    reopened = open_sqlite_event_store(location)
    try:
        assert reopened.append("order-1", 0, [_event("order-1", "Paid")]) == Appended(1)
        # A caller that has not noticed the restart is still refused, by the same rule as
        # before it.
        raced = reopened.append("order-1", NO_STREAM, [_event("order-1", "Raced")])
        assert raced == VersionConflict(1)
    finally:
        reopened.close()


def test_refuses_to_rewrite_or_erase_what_has_been_recorded(location: str) -> None:
    """The append-only rule lives in the database, not in the adapter.

    A rule the application enforces is a rule the next process to open the file — a migration
    script, a `sqlite3` shell, a well-meaning fix in production — will not.
    """
    store = open_sqlite_event_store(location)
    store.append("order-1", NO_STREAM, [_event("order-1", "Placed")])
    store.close()

    connection = sqlite3.connect(location)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE events SET event_type = 'Rewritten'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM events")
        remaining = connection.execute("SELECT event_type FROM events").fetchall()
        assert [row[0] for row in remaining] == ["Placed"]
    finally:
        connection.close()
