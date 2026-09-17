```python
from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Union


@dataclass(frozen=True, slots=True)
class CommandAccepted:
    events: tuple[AccountEvent, ...]


@dataclass(frozen=True, slots=True)
class CommandRejected:
    reason: str


CommandResult = Union[CommandAccepted, CommandRejected]


# Use-case: load -> decide -> append (with optimistic concurrency).
# `store`, `decide`, `evolve` and `initial_state` are the Account decider and
# its event-store port, as defined elsewhere in this bounded context.
async def handle_command(
    store: EventStore[AccountEvent],
    stream_id: StreamId,
    command: AccountCommand,
) -> CommandResult:
    # 1. LOAD the stream's events (and the version we read at)
    stream = await store.read_stream(stream_id)

    # 2. REHYDRATE current state by folding — pure
    state = reduce(evolve, stream.events, initial_state)

    # 3. DECIDE — pure business logic
    decision = decide(command, state)
    if isinstance(decision, Rejected):
        return CommandRejected(decision.reason)

    # 4. APPEND the new events, asserting the stream has not moved since we read it
    outcome = await store.append_to_stream(
        stream_id, decision.events, expected_version=stream.version
    )
    if outcome == "version-conflict":
        return CommandRejected("concurrent-modification")

    return CommandAccepted(decision.events)
```
