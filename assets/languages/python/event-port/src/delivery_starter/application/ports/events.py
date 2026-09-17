from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class DomainEvent:
    type: str
    schema_version: Literal[1]
    stream_id: str
    payload: dict[str, object]


@dataclass(frozen=True)
class AppendResult:
    outcome: Literal["appended", "version-conflict"]
    version: int


class EventStore(Protocol):
    def read(self, stream_id: str) -> tuple[DomainEvent, ...]: ...

    def append(
        self,
        stream_id: str,
        expected_version: int,
        events: tuple[DomainEvent, ...],
    ) -> AppendResult: ...
