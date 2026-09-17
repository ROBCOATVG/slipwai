```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, Protocol, TypeVar

StreamId = str
E = TypeVar("E")

# One physical store holds many stream types; the adapter parses stored JSON
# into E on read, so each typed EventStore[E] is a view over the streams of
# that one aggregate family — like a repository.

AppendResult = Literal["ok", "version-conflict"]


@dataclass(frozen=True, slots=True)
class ReadStreamResult(Generic[E]):
    events: tuple[E, ...]
    version: int


class EventStore(Protocol[E]):
    async def read_stream(self, stream_id: StreamId) -> ReadStreamResult[E]: ...

    async def append_to_stream(
        self,
        stream_id: StreamId,
        events: tuple[E, ...],
        *,
        expected_version: int,
    ) -> AppendResult: ...
```
