```python
# gifting/testing/fakes/fake_pledge_persistence.py
from __future__ import annotations

import asyncio
from typing import Iterable, Literal, Sequence

from gifting.hexagon.application.pledging import PledgePersistence, StoredOccasion
from gifting.hexagon.domain.types import Occasion, OccasionId, PledgeRecorded


class FakePledgePersistence:
    """In-memory PledgePersistence for use-case tests. It implements the real
    port and exposes extra observation state — saved_entities and
    outbox_events — for assertions. Lives outside the production hexagon,
    under testing/fakes/."""

    def __init__(self, initial: Iterable[Occasion] = ()) -> None:
        self._store: dict[OccasionId, StoredOccasion] = {
            occasion.id: StoredOccasion(value=occasion, version=0) for occasion in initial
        }
        self.saved_entities: list[Occasion] = []
        self.outbox_events: list[PledgeRecorded] = []

    async def find_occasion_by_id(self, occasion_id: OccasionId) -> StoredOccasion | None:
        stored = self._store.get(occasion_id)
        # Yield to the event loop, as a real I/O-bound adapter would, so that
        # concurrent pledges against the same starting version genuinely
        # interleave instead of one silently running to completion first.
        await asyncio.sleep(0)
        return stored

    async def save_with_outbox(
        self,
        occasion: Occasion,
        events: Sequence[PledgeRecorded],
        expected_version: int,
    ) -> Literal["saved", "conflict"]:
        current = self._store.get(occasion.id)
        if current is None or current.version != expected_version:
            return "conflict"
        self._store[occasion.id] = StoredOccasion(value=occasion, version=expected_version + 1)
        self.saved_entities.append(occasion)
        self.outbox_events.extend(events)
        return "saved"


# gifting/testing/fakes/fake_pledge_projection.py
class FakePledgeProjection:
    """In-memory PledgeProjection. Idempotent by event ID; exposes records
    for assertions."""

    def __init__(self) -> None:
        self._records: dict[str, PledgeRecorded] = {}

    async def record_from(self, event: PledgeRecorded) -> None:
        self._records.setdefault(event.id, event)

    @property
    def records(self) -> list[PledgeRecorded]:
        return list(self._records.values())
```
