```python
from dataclasses import dataclass
from typing import Literal, Sequence, Union


# Minimal stand-ins; the full aggregate and event are defined alongside
# the rest of the domain model.
@dataclass(frozen=True)
class Occasion:
    id: str
    total_pledged_minor_units: int
    budget_minor_units: int


@dataclass(frozen=True)
class PledgeRecorded:
    pledge_id: str
    occasion_id: str
    contributor_id: str
    amount_minor_units: int


DomainRejectionReason = Literal[
    "contributor-ineligible",
    "non-positive-amount",
    "currency-mismatch",
    "exceeds-budget",
    "funding-closed",
]

# Outcomes only the surrounding use case can detect -- e.g. the aggregate
# did not exist, or changed concurrently since it was loaded.
ApplicationRejectionReason = Literal["not-found", "concurrent-change"]


@dataclass(frozen=True)
class PledgeAccepted:
    occasion: Occasion
    events: Sequence[PledgeRecorded]
    success: Literal[True] = True


@dataclass(frozen=True)
class PledgeRejected:
    reason: DomainRejectionReason
    success: Literal[False] = False


# Domain-level decision: everything a pure domain service can determine.
PledgeDecision = Union[PledgeAccepted, PledgeRejected]


@dataclass(frozen=True)
class PledgeApplicationRejected:
    reason: ApplicationRejectionReason
    success: Literal[False] = False


# Application-level result: the domain decision, widened with outcomes
# that only the use case orchestrating persistence can detect.
PledgeResult = Union[PledgeDecision, PledgeApplicationRejected]
```
