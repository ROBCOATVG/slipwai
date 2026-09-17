```python
# gifting/hexagon/domain/types.py — domain types and branded IDs
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NewType

OccasionId = NewType("OccasionId", str)
ContributorId = NewType("ContributorId", str)
PledgeId = NewType("PledgeId", str)

Currency = Literal["GBP", "USD", "EUR"]


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: Currency


def make_money(minor_units: int, currency: Currency) -> Money:
    if minor_units < 0:
        raise ValueError(f"invalid money: minor_units must not be negative, got {minor_units}")
    return Money(minor_units=minor_units, currency=currency)


@dataclass(frozen=True)
class Occasion:
    id: OccasionId
    name: str
    budget: Money
    total_pledged: Money
    is_funding_closed: bool


@dataclass(frozen=True)
class PledgeRecorded:
    id: PledgeId
    occasion_id: OccasionId
    contributor_id: ContributorId
    amount: Money


RecordPledgeRejectionReason = Literal[
    "non-positive-amount", "currency-mismatch", "exceeds-budget", "funding-closed"
]


@dataclass(frozen=True)
class PledgeAccepted:
    occasion: Occasion
    events: tuple[PledgeRecorded, ...]
    success: Literal[True] = True


@dataclass(frozen=True)
class PledgeRejected:
    reason: RecordPledgeRejectionReason
    success: Literal[False] = False


# The aggregate operation returns one of these two shapes; callers narrow on
# `.success` exactly as they would on a discriminated union.
PledgeDecision = PledgeAccepted | PledgeRejected
```
