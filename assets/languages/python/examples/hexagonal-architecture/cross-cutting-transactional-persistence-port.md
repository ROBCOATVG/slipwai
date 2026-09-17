```python
from dataclasses import dataclass
from typing import Literal, Protocol

import asyncpg

SaveOutcome = Literal["saved", "conflict"]


@dataclass(frozen=True)
class StoredOccasion:
    value: "Occasion"
    version: int


# Application-owned driven port: one semantic operation must save both or neither.
class PledgePersistence(Protocol):
    async def find_occasion_by_id(self, occasion_id: "OccasionId") -> StoredOccasion | None: ...

    async def save_with_outbox(
        self,
        occasion: "Occasion",
        events: tuple["PledgeRecorded", ...],
        expected_version: int,
    ) -> SaveOutcome: ...


class _ConcurrentChange(Exception):
    """Internal control-flow signal; never escapes this adapter."""


def _rows_affected(command_tag: str) -> int:
    # asyncpg command tags look like "UPDATE 1".
    return int(command_tag.rsplit(" ", 1)[-1])


class PostgresPledgePersistence:
    """Driven adapter: owns the database transaction mechanics behind the
    atomic compare-and-save-with-outbox contract."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_occasion_by_id(self, occasion_id: "OccasionId") -> StoredOccasion | None:
        row = await self._pool.fetchrow(
            "select id, name, budget_minor_units, budget_currency, "
            "total_pledged_minor_units, total_pledged_currency, "
            "is_funding_closed, version from occasions where id = $1",
            occasion_id,
        )
        return StoredOccasion(value=to_occasion(row), version=row["version"]) if row else None

    async def save_with_outbox(
        self,
        occasion: "Occasion",
        events: tuple["PledgeRecorded", ...],
        expected_version: int,
    ) -> SaveOutcome:
        try:
            async with self._pool.acquire() as conn, conn.transaction():
                # The version predicate prevents two readers from overwriting
                # each other; a conflict inserts no outbox row.
                tag = await conn.execute(
                    "update occasions set name = $2, budget_minor_units = $3, "
                    "budget_currency = $4, total_pledged_minor_units = $5, "
                    "total_pledged_currency = $6, is_funding_closed = $7, version = $8 "
                    "where id = $1 and version = $9",
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
                    raise _ConcurrentChange
                await conn.executemany(
                    "insert into outbox (event_id, occasion_id, contributor_id, "
                    "amount_minor_units, amount_currency) values ($1, $2, $3, $4, $5)",
                    [
                        (e.id, e.occasion_id, e.contributor_id, e.amount.minor_units, e.amount.currency)
                        for e in events
                    ],
                )
        except _ConcurrentChange:
            return "conflict"
        return "saved"
```
