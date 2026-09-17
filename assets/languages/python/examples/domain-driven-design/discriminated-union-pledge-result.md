```python
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PledgeAccepted:
    occasion: "Occasion"
    events: tuple["PledgeRecorded", ...]


@dataclass(frozen=True)
class PledgeRejected:
    reason: Literal[
        "contributor-ineligible",
        "non-positive-amount",
        "currency-mismatch",
        "exceeds-budget",
        "funding-closed",
    ]


PledgeDecision = PledgeAccepted | PledgeRejected


@dataclass(frozen=True)
class PledgeNotFound:
    reason: Literal["not-found"] = "not-found"


@dataclass(frozen=True)
class PledgeConcurrentChange:
    reason: Literal["concurrent-change"] = "concurrent-change"


# Application-level outcomes join the business decision into one result type.
PledgeResult = PledgeDecision | PledgeNotFound | PledgeConcurrentChange
```
