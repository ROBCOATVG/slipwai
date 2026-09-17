"""SQLite checkpoint adapter, on the event store's own connection.

Built from the store rather than from a location, and that is the point: `record` has to commit
in the same transaction as the view rows it accounts for, so it has to be the same connection.
Two adapters opening the same file are two connections and two transactions, and a checkpoint in
its own transaction is a race with a number in it.

The lease is claimed inside `BEGIN IMMEDIATE`, which takes SQLite's single write lock, so the
read-then-write is atomic without anything clever. What SQLite cannot do here is prove that two
*processes* contend correctly, because it serialises them; `make test-integration` proves that
against Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from delivery_starter.adapters.driven.event_store_sqlite import (
    SqliteEventStore,
)
from delivery_starter.application.ports.read_models import (
    FROM_THE_BEGINNING,
    CheckpointStore,
    Lease,
)

POSITION_OF = "SELECT position FROM projection_checkpoints WHERE projection = ?"

#: `updated_at` moves with the position, so "is this projection stuck" is answerable from the
#: table rather than from a log somewhere.
RECORD = """
  INSERT INTO projection_checkpoints (projection, position)
  VALUES (?, ?)
  ON CONFLICT (projection) DO UPDATE
    SET position = excluded.position,
        updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
"""

#: Take the lease when nobody holds it, when this owner already holds it (which is how a long
#: catch-up renews), or when the holder's lease has lapsed. Refuse otherwise — and the refusal is
#: the `WHERE` on the update, so the whole decision is one statement and cannot be split.
CLAIM = """
  INSERT INTO projection_checkpoints (projection, position, lease_owner, lease_expires_at)
  VALUES (?, 0, ?, ?)
  ON CONFLICT (projection) DO UPDATE
    SET lease_owner = excluded.lease_owner,
        lease_expires_at = excluded.lease_expires_at
    WHERE projection_checkpoints.lease_owner IS NULL
       OR projection_checkpoints.lease_owner = excluded.lease_owner
       OR projection_checkpoints.lease_expires_at <= ?
"""

RELEASE = """
  UPDATE projection_checkpoints
  SET lease_owner = NULL, lease_expires_at = NULL
  WHERE projection = ? AND lease_owner = ?
"""


def _as_text(instant: datetime) -> str:
    """A fixed-width UTC instant, because SQLite compares these as strings.

    Same width, same zone, always — that is what makes `lease_expires_at <= ?` a chronological
    comparison rather than an alphabetical one that is right until an offset or a shorter
    fraction turns up. Postgres has `timestamptz` and needs none of this; the adapter is where
    the difference stops.
    """
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


class SqliteCheckpointStore(CheckpointStore):
    def __init__(self, store: SqliteEventStore) -> None:
        self._store = store
        self._connection = store.connection

    def position_of(self, projection: str) -> int:
        row = self._connection.execute(POSITION_OF, (projection,)).fetchone()
        return FROM_THE_BEGINNING if row is None else int(row[0])

    def record(self, projection: str, position: int) -> None:
        """No commit here. Call it inside the store's `unit_of_work`, with the writes it accounts
        for; outside one, SQLite commits it on its own, which is the mistake this line names."""
        self._connection.execute(RECORD, (projection, position))

    def claim(
        self,
        projection: str,
        owner: str,
        now: datetime,
        ttl: timedelta,
    ) -> Lease | None:
        expires_at = now + ttl
        with self._store.unit_of_work():
            cursor = self._connection.execute(
                CLAIM,
                (projection, owner, _as_text(expires_at), _as_text(now)),
            )
            if cursor.rowcount == 0:
                return None
        return Lease(projection=projection, owner=owner, expires_at=expires_at)

    def release(self, lease: Lease) -> None:
        with self._store.unit_of_work():
            self._connection.execute(RELEASE, (lease.projection, lease.owner))


def create_sqlite_checkpoint_store(store: SqliteEventStore) -> SqliteCheckpointStore:
    """Take the store's own connection, so both adapters are inside one `unit_of_work`."""
    return SqliteCheckpointStore(store)
