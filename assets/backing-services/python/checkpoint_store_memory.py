"""In-memory checkpoint adapter, on the same "connection" as the in-memory event store.

Built from the store rather than standing alone, which is the rule every checkpoint adapter here
follows: `record` has to land in the same transaction as the view write it accounts for, and an
adapter that does not share the store's unit of work cannot do that however carefully it is
called.

What it can prove: that a projection resumes from where it stopped, that one worker at a time
advances it, that a lease expires, and that a batch which fails leaves both the view and the
checkpoint where they were. What it cannot prove is a genuine race between two workers, because
nothing here runs concurrently — `make test-integration` is where two connections contend for
one lease.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from delivery_starter.adapters.driven.event_store_memory import (
    InMemoryDatabase,
    InMemoryEventStore,
)
from delivery_starter.application.ports.read_models import (
    FROM_THE_BEGINNING,
    CheckpointStore,
    Lease,
)


class InMemoryCheckpointStore(CheckpointStore):
    def __init__(self, database: InMemoryDatabase) -> None:
        self._database = database

    def position_of(self, projection: str) -> int:
        return self._database.checkpoints.get(projection, FROM_THE_BEGINNING)

    def record(self, projection: str, position: int) -> None:
        self._database.checkpoints[projection] = position

    def claim(
        self,
        projection: str,
        owner: str,
        now: datetime,
        ttl: timedelta,
    ) -> Lease | None:
        held = self._database.leases.get(projection)
        if held is not None and held[0] != owner and held[1] > now:
            return None
        expires_at = now + ttl
        self._database.leases[projection] = (owner, expires_at)
        return Lease(projection=projection, owner=owner, expires_at=expires_at)

    def release(self, lease: Lease) -> None:
        held = self._database.leases.get(lease.projection)
        if held is not None and held[0] == lease.owner:
            del self._database.leases[lease.projection]


def create_in_memory_checkpoint_store(store: InMemoryEventStore) -> InMemoryCheckpointStore:
    """Take the store's own database, so both adapters are inside one `unit_of_work`."""
    return InMemoryCheckpointStore(store.database)
