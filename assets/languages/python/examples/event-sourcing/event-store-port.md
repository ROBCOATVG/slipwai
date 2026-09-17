```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, Protocol, TypeVar

StreamId = str
E = TypeVar("E")

AppendOutcome = Literal["ok", "version-conflict"]


@dataclass(frozen=True, slots=True)
class StreamSlice(Generic[E]):
    events: tuple[E, ...]
    version: int


# Port (application layer) — owned by the command handler that consumes it.
# Typed to one aggregate's event family, like a repository (the underlying
# adapter can hold many streams; it parses stored JSON into E on read).
class EventStore(Protocol[E]):
    async def read_stream(self, stream_id: StreamId) -> StreamSlice[E]: ...

    async def append_to_stream(
        self,
        stream_id: StreamId,
        events: tuple[E, ...],
        *,
        expected_version: int,
    ) -> AppendOutcome: ...
```
