"""Postgres checkpoint adapter, on the event store's own connection.

Built from the store rather than from a DSN, and that is the point: `record` has to commit in the
same transaction as the view rows it accounts for, so it has to be the same connection. Two
adapters on two connections are two transactions, and a checkpoint in its own transaction is a
race with a number in it — either the view is written and the checkpoint is lost, or the
checkpoint moves past rows that were rolled back.

The claim is **one statement**. An `INSERT ... ON CONFLICT DO UPDATE ... WHERE` decides whether
the lease is takeable and takes it in the same breath, so there is no window between reading who
holds it and writing that you do. `make test-integration` is where two connections race for it
for real, which is the one thing no single-writer store — an in-memory fake, a file-backed
one — can prove.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from delivery_starter.adapters.driven.event_store_postgres import (
    PostgresEventStore,
)
from delivery_starter.application.ports.read_models import (
    FROM_THE_BEGINNING,
    CheckpointStore,
    Lease,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from psycopg import Connection

POSITION_OF = "SELECT position FROM projection_checkpoints WHERE projection = %s"

#: `updated_at` moves with the position, so "is this projection stuck" is answerable from the
#: table rather than from a log somewhere.
RECORD = """
  INSERT INTO projection_checkpoints (projection, position)
  VALUES (%s, %s)
  ON CONFLICT (projection) DO UPDATE
    SET position = EXCLUDED.position, updated_at = now()
"""

#: Take the lease when nobody holds it, when this owner already holds it (which is how a long
#: catch-up renews), or when the holder's has lapsed. Refuse otherwise — and the refusal is the
#: `WHERE` on the update, so the whole decision is one statement and cannot be split by another
#: worker doing the same thing a microsecond later.
CLAIM = """
  INSERT INTO projection_checkpoints (projection, position, lease_owner, lease_expires_at)
  VALUES (%s, 0, %s, %s)
  ON CONFLICT (projection) DO UPDATE
    SET lease_owner = EXCLUDED.lease_owner,
        lease_expires_at = EXCLUDED.lease_expires_at
    WHERE projection_checkpoints.lease_owner IS NULL
       OR projection_checkpoints.lease_owner = EXCLUDED.lease_owner
       OR projection_checkpoints.lease_expires_at <= %s
  RETURNING position
"""

RELEASE = """
  UPDATE projection_checkpoints
  SET lease_owner = NULL, lease_expires_at = NULL
  WHERE projection = %s AND lease_owner = %s
"""


class PostgresCheckpointStore(CheckpointStore):
    def __init__(self, store: PostgresEventStore) -> None:
        self._store = store
        self._connection: Connection[Any] = store.connection

    def position_of(self, projection: str) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute(POSITION_OF, (projection,))
            row = cursor.fetchone()
        position = FROM_THE_BEGINNING if row is None else int(row[0])
        self._finish()
        return position

    def record(self, projection: str, position: int) -> None:
        """No commit here. Call it inside the store's `unit_of_work`, with the writes it accounts
        for; outside one it is left uncommitted on the connection, which is the mistake this line
        exists to name."""
        with self._connection.cursor() as cursor:
            cursor.execute(RECORD, (projection, position))

    def claim(
        self,
        projection: str,
        owner: str,
        now: datetime,
        ttl: timedelta,
    ) -> Lease | None:
        expires_at = now + ttl
        with self._store.unit_of_work(), self._connection.cursor() as cursor:
            cursor.execute(CLAIM, (projection, owner, expires_at, now))
            taken = cursor.rowcount != 0
        if not taken:
            return None
        return Lease(projection=projection, owner=owner, expires_at=expires_at)

    def release(self, lease: Lease) -> None:
        with self._store.unit_of_work(), self._connection.cursor() as cursor:
            cursor.execute(RELEASE, (lease.projection, lease.owner))

    def _finish(self) -> None:
        """End a read's transaction unless a unit of work owns it. The store's own reads do the
        same thing for the same reason: an idle-in-transaction connection holds its snapshot
        open and blocks vacuum."""
        self._store.finish_a_read()


def create_postgres_checkpoint_store(store: PostgresEventStore) -> PostgresCheckpointStore:
    """Take the store's own connection, so both adapters are inside one `unit_of_work`."""
    return PostgresCheckpointStore(store)
