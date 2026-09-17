"""The checkpoint store against real Postgres, plus the one thing only a real store can prove.

Deliberately NOT part of `make verify`, like its sibling:

    make services-up migrate test-integration

The contract runs here as it does against the fakes. The test below it is the one that cannot
run anywhere else — two connections claiming one lease at the same instant, where exactly one
must win. That is the whole basis for running a projection on more than one replica.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import psycopg

# The same connection helper the event-store integration suite uses: both modules sit in this
# directory, so it is importable by name, and one helper means one set of instructions for a
# database that is not running.
from contract.checkpoint_store_contract import NOW, CheckpointStoreContract
from test_event_store_postgres import DATABASE_URL, _connect

from delivery_starter.adapters.driven.checkpoint_store_postgres import (
    create_postgres_checkpoint_store,
)
from delivery_starter.adapters.driven.event_store_postgres import (
    create_postgres_event_store,
)
from delivery_starter.application.ports.read_models import (
    CheckpointStore,
)


class TestPostgresCheckpointStore(CheckpointStoreContract):
    """The shared contract, against the real thing."""

    def make_stores(self) -> tuple[object, CheckpointStore]:
        store = create_postgres_event_store(_connect())
        return store, create_postgres_checkpoint_store(store)


def test_exactly_one_of_many_simultaneous_claims_wins() -> None:
    """The assertion no infrastructure-free adapter can make.

    The claim is one statement — an upsert whose `WHERE` decides whether the lease is takeable —
    so there is no window between reading who holds it and writing that you do. Being
    single-threaded, the in-memory adapter would pass this while proving nothing; SQLite
    serialises writers, so it would too.
    """
    projection = f"race-{uuid.uuid4()}"
    now = datetime.now(UTC)
    attempts = 8

    def attempt(index: int) -> object:
        # One connection per worker: two claims on one connection cannot race, they queue.
        with psycopg.connect(DATABASE_URL) as handle:
            store = create_postgres_event_store(handle)
            checkpoints = create_postgres_checkpoint_store(store)
            return checkpoints.claim(projection, f"worker-{index}", now, timedelta(seconds=30))

    with ThreadPoolExecutor(max_workers=attempts) as pool:
        results = list(pool.map(attempt, range(attempts)))

    assert len([result for result in results if result is not None]) == 1


def test_a_lease_is_visible_to_another_connection_at_once() -> None:
    """A lease that only one process can see is not a lease. It is committed on its own, unlike
    a position, because coordination has to be visible before the work it coordinates."""
    projection = f"visible-{uuid.uuid4()}"
    with psycopg.connect(DATABASE_URL) as one, psycopg.connect(DATABASE_URL) as other:
        first = create_postgres_checkpoint_store(create_postgres_event_store(one))
        second = create_postgres_checkpoint_store(create_postgres_event_store(other))

        assert first.claim(projection, "worker-1", NOW, timedelta(seconds=30)) is not None
        assert second.claim(projection, "worker-2", NOW, timedelta(seconds=30)) is None
