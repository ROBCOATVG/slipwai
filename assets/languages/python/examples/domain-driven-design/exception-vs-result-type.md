```python
from dataclasses import dataclass
from typing import Literal


# Exception — an invariant violation means a bug, not a business outcome.
def create_money(minor_units: int, currency: str) -> "Money":
    if minor_units < 0:
        raise ValueError("Money cannot be negative")
    return Money(minor_units=minor_units, currency=currency)


@dataclass(frozen=True)
class PledgeAccepted:
    occasion: "Occasion"
    events: tuple["PledgeRecorded", ...]


@dataclass(frozen=True)
class PledgeRejected:
    reason: Literal["contributor-ineligible"]


PledgeDecision = PledgeAccepted | PledgeRejected


# Result type — an expected business outcome, not a bug.
def pledge_contribution(
    occasion: "Occasion", eligibility: "Eligibility", pledge: "NewPledge"
) -> PledgeDecision:
    if not eligibility.may_pledge:
        return PledgeRejected(reason="contributor-ineligible")
    ...
```
