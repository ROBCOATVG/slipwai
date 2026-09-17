```python
from __future__ import annotations

from typing import Protocol


class Transaction(Protocol):
    """A unit-of-work boundary — commits on clean exit, rolls back on exception."""

    async def acquire_exclusive_projection_lease(self, projection_name: str) -> None: ...
    async def load_checkpoint(self, projection_name: str) -> int | None: ...
    async def save_checkpoint(self, projection_name: str, global_position: int) -> None: ...
    async def load_balance_view(self, stream_id: StreamId) -> BalanceView | None: ...
    async def upsert_balance_view(self, view: BalanceView) -> None: ...


class Database(Protocol):
    def transaction(self) -> "AsyncContextManager[Transaction]": ...


class ProjectionGapError(RuntimeError):
    """The next expected position is missing — retry after the missing position."""


# one event, applied and its checkpoint advanced atomically
async def apply_one_checkpointed(
    db: Database,
    projection_name: str,
    envelope: AccountProjectionEnvelope,
) -> None:
    async with db.transaction() as tx:
        await tx.acquire_exclusive_projection_lease(projection_name)
        applied_through = await tx.load_checkpoint(projection_name) or 0
        if envelope.global_position <= applied_through:
            return  # exact redelivery
        if envelope.global_position != applied_through + 1:
            raise ProjectionGapError("Projection gap: retry after the missing position")

        current = await tx.load_balance_view(envelope.stream_id) or empty_balance_view
        await tx.upsert_balance_view(apply(current, envelope))
        await tx.save_checkpoint(projection_name, envelope.global_position)  # same transaction
```
