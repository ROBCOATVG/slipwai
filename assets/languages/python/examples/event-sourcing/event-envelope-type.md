```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Generic, NewType, TypeVar

TEventType = TypeVar("TEventType", bound=str)
TData = TypeVar("TData")

# Correlation and causation are UUIDs, and two types rather than one alias used twice: they sit
# side by side below and are the same shape underneath, so swapping them is invisible at runtime
# -- and it destroys the one thing they exist for. NewType erases to uuid.UUID, so the
# distinction costs nothing at runtime and the type checker is what enforces it.
CorrelationId = NewType("CorrelationId", uuid.UUID)
CausationId = NewType("CausationId", uuid.UUID)


@dataclass(frozen=True, slots=True)
class EventMetadata:
    correlation_id: CorrelationId       # ties one whole business transaction together
    causation_id: CausationId | None    # the message that directly caused this event
    # + optional: user_id, tenant_id, schema_version


@dataclass(frozen=True, slots=True)
class EventEnvelope(Generic[TEventType, TData]):
    id: uuid.UUID          # unique event id — idempotency + causation target
    type: TEventType       # event type name (a string, for tolerant deserialization)
    stream_id: str         # the aggregate instance
    version: int           # per-stream position (optimistic concurrency)
    global_position: int   # store-wide order (subscriptions/projections)
    timestamp: str         # ISO-8601, assigned by the store
    data: TData            # the domain payload
    metadata: EventMetadata
```
