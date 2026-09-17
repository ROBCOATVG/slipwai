```python
# gifting/adapters/driven/postgres/pledge_persistence.py
from __future__ import annotations

from typing import Literal, Sequence

import asyncpg

from gifting.hexagon.application.pledging import StoredOccasion
from gifting.hexagon.domain.types import Occasion, OccasionId, PledgeRecorded, make_money


class _ConcurrentChange(Exception):
    """Internal control-flow signal; never escapes this adapter."""


def _to_occasion(row: asyncpg.Record) -> Occasion:
    return Occasion(
        id=row["id"],
        name=row["name"],
        budget=make_money(row["budget_minor_units"], row["budget_currency"]),
        total_pledged=make_money(row["total_pledged_minor_units"], row["total_pledged_currency"]),
        is_funding_closed=row["is_funding_closed"],
    )


def _rows_affected(command_tag: str) -> int:
    # asyncpg command tags look like "UPDATE 1".
    return int(command_tag.rsplit(" ", 1)[-1])


class PostgresPledgePersistence:
    """Concrete PledgePersistence backed by Postgres. Translates domain types
    to/from rows and implements the atomic compare-and-save-with-outbox
    contract in one transaction."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_occasion_by_id(self, occasion_id: OccasionId) -> StoredOccasion | None:
        row = await self._pool.fetchrow(
            """
            select id, name, budget_minor_units, budget_currency,
                   total_pledged_minor_units, total_pledged_currency,
                   is_funding_closed, version
            from occasions where id = $1
            """,
            occasion_id,
        )
        return StoredOccasion(value=_to_occasion(row), version=row["version"]) if row else None

    async def save_with_outbox(
        self,
        occasion: Occasion,
        events: Sequence[PledgeRecorded],
        expected_version: int,
    ) -> Literal["saved", "conflict"]:
        try:
            async with self._pool.acquire() as conn, conn.transaction():
                # The version predicate prevents two readers from overwriting
                # each other; a conflict inserts no outbox row.
                tag = await conn.execute(
                    """
                    update occasions
                    set name = $2, budget_minor_units = $3, budget_currency = $4,
                        total_pledged_minor_units = $5, total_pledged_currency = $6,
                        is_funding_closed = $7, version = $8
                    where id = $1 and version = $9
                    """,
                    occasion.id,
                    occasion.name,
                    occasion.budget.minor_units,
                    occasion.budget.currency,
                    occasion.total_pledged.minor_units,
                    occasion.total_pledged.currency,
                    occasion.is_funding_closed,
                    expected_version + 1,
                    expected_version,
                )
                if _rows_affected(tag) != 1:
                    raise _ConcurrentChange()

                await conn.executemany(
                    """
                    insert into outbox (event_id, occasion_id, contributor_id,
                                         amount_minor_units, amount_currency)
                    values ($1, $2, $3, $4, $5)
                    """,
                    [
                        (
                            event.id,
                            event.occasion_id,
                            event.contributor_id,
                            event.amount.minor_units,
                            event.amount.currency,
                        )
                        for event in events
                    ],
                )
        except _ConcurrentChange:
            return "conflict"
        return "saved"


# gifting/adapters/driven/postgres/pledge_projection.py
class PostgresPledgeProjection:
    """Concrete PledgeProjection. Inserts on the event's unique ID and
    no-ops on conflict, so redelivery is idempotent and an existing
    projection is never overwritten with incoming data."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record_from(self, event: PledgeRecorded) -> None:
        await self._pool.execute(
            """
            insert into pledge_projection (event_id, occasion_id, contributor_id,
                                            amount_minor_units, amount_currency)
            values ($1, $2, $3, $4, $5)
            on conflict (event_id) do nothing
            """,
            event.id,
            event.occasion_id,
            event.contributor_id,
            event.amount.minor_units,
            event.amount.currency,
        )
```
