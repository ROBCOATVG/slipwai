```python
# gifting/hexagon/application/pledging.py — driving port + application result
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, Sequence

from gifting.hexagon.domain.types import (
    ContributorId,
    Money,
    Occasion,
    OccasionId,
    PledgeDecision,
    PledgeId,
    PledgeRecorded,
)


@dataclass(frozen=True)
class AuthenticatedPledger:
    """An opaque, provider-free principal. Only the authentication adapter
    constructs one in production; the request body cannot forge it."""

    contributor_id: ContributorId


ApplicationPledgeRejectionReason = Literal["not-found", "concurrent-change"]


@dataclass(frozen=True)
class PledgeNotFoundOrConflict:
    reason: ApplicationPledgeRejectionReason
    success: Literal[False] = False


# PledgeResult extends the domain decision with the two outcomes only the
# application layer can produce.
PledgeResult = PledgeDecision | PledgeNotFoundOrConflict


@dataclass(frozen=True)
class PledgeToOccasionCommand:
    pledge_id: PledgeId
    occasion_id: OccasionId
    principal: AuthenticatedPledger
    amount: Money


class ForPledgingToOccasions(Protocol):
    async def pledge_to_occasion(self, command: PledgeToOccasionCommand) -> PledgeResult: ...


# gifting/hexagon/application/pledge_persistence.py
@dataclass(frozen=True)
class StoredOccasion:
    value: Occasion
    version: int


class PledgePersistence(Protocol):
    async def find_occasion_by_id(self, occasion_id: OccasionId) -> StoredOccasion | None: ...

    async def save_with_outbox(
        self,
        occasion: Occasion,
        events: Sequence[PledgeRecorded],
        expected_version: int,
    ) -> Literal["saved", "conflict"]: ...


# gifting/hexagon/application/pledge_projection.py
class PledgeProjection(Protocol):
    async def record_from(self, event: PledgeRecorded) -> None:
        """event is a validated immutable log record: one ID permanently
        names one payload. Implementations must be safe against redelivery."""
        ...
```
