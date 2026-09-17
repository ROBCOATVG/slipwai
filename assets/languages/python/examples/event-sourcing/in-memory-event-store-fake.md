```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

import pytest

E = TypeVar("E")


# A real implementation of the port backed by a dict — not a mock. Because the
# port is typed EventStore[E], the fake needs no casts anywhere.
@dataclass(slots=True)
class InMemoryEventStore(Generic[E]):
    _streams: dict[StreamId, list[E]] = field(default_factory=dict)

    async def read_stream(self, stream_id: StreamId) -> ReadStreamResult[E]:
        events = tuple(self._streams.get(stream_id, ()))
        return ReadStreamResult(events, version=len(events))

    async def append_to_stream(
        self, stream_id: StreamId, events: tuple[E, ...], *, expected_version: int
    ) -> AppendResult:
        current = self._streams.get(stream_id, [])
        if len(current) != expected_version:
            return "version-conflict"
        self._streams[stream_id] = [*current, *events]
        return "ok"


@pytest.mark.asyncio
async def test_should_persist_a_deposit_so_a_later_withdrawal_sees_the_funds() -> None:
    handle = make_command_handler(account_decider, InMemoryEventStore[AccountEvent]())
    await handle(stream_id, OpenAccount("GBP"))
    await handle(stream_id, Deposit(money(10_000)))

    result = await handle(stream_id, Withdraw(money(6_000)))

    assert result == CommandAccepted((MoneyWithdrawn(money(6_000)),))


@pytest.mark.asyncio
async def test_should_reject_a_concurrent_append_made_against_a_stale_version() -> None:
    store: InMemoryEventStore[AccountEvent] = InMemoryEventStore()
    await store.append_to_stream(stream_id, (opened(),), expected_version=0)

    outcome = await store.append_to_stream(stream_id, (deposited(10),), expected_version=0)  # stale

    assert outcome == "version-conflict"
```
