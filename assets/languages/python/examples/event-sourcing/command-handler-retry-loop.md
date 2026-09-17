```python
from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Awaitable, Callable, Generic, TypeVar, Union

State = TypeVar("State")
Command = TypeVar("Command")
Event = TypeVar("Event")


@dataclass(frozen=True, slots=True)
class CommandAccepted(Generic[Event]):
    events: tuple[Event, ...]


@dataclass(frozen=True, slots=True)
class CommandRejected:
    reason: str


CommandResult = Union[CommandAccepted[Event], CommandRejected]


def make_command_handler(
    decider: Decider[State, Command, Event],
    store: EventStore[Event],
    max_attempts: int = 3,
) -> Callable[[StreamId, Command], Awaitable[CommandResult]]:
    async def handle(stream_id: StreamId, command: Command) -> CommandResult:
        for _ in range(max_attempts):
            stream = await store.read_stream(stream_id)                          # load
            state = reduce(decider.evolve, stream.events, decider.initial_state)  # rehydrate (pure)

            decision = decider.decide(command, state)                            # decide (pure)
            if isinstance(decision, Rejected):
                return CommandRejected(decision.reason)

            outcome = await store.append_to_stream(
                stream_id, decision.events, expected_version=stream.version
            )
            if outcome == "ok":
                return CommandAccepted(decision.events)
            # version-conflict: the stream moved under us — loop to reload and re-decide against fresh state

        return CommandRejected("concurrent-modification")

    return handle
```
