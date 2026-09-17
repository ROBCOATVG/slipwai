```python
from dataclasses import dataclass, replace
from typing import Literal

MAX_SAFE_INTEGER = 2**53 - 1


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: str


def create_money(minor_units: int, currency: str) -> Money:
    return Money(minor_units, currency)


@dataclass(frozen=True)
class OccasionId:
    value: str


@dataclass(frozen=True)
class Occasion:
    id: OccasionId
    is_funding_closed: bool
    total_pledged: Money
    budget: Money


@dataclass(frozen=True)
class ContributorEligibility:
    may_pledge: bool


@dataclass(frozen=True)
class Pledge:
    amount: Money


@dataclass(frozen=True)
class PledgeAccepted:
    occasion: Occasion
    success: Literal[True] = True


@dataclass(frozen=True)
class PledgeRejected:
    reason: str
    success: Literal[False] = False


PledgeDecision = PledgeAccepted | PledgeRejected


# No events needed — explicit return value
def pledge_contribution(
    occasion: Occasion,
    eligibility: ContributorEligibility,
    pledge: Pledge,
) -> PledgeDecision:
    if not eligibility.may_pledge:
        return PledgeRejected(reason="contributor-ineligible")
    if occasion.is_funding_closed:
        return PledgeRejected(reason="funding-closed")
    if (
        pledge.amount.currency != occasion.total_pledged.currency
        or occasion.total_pledged.currency != occasion.budget.currency
    ):
        return PledgeRejected(reason="currency-mismatch")

    values = (occasion.total_pledged.minor_units, occasion.budget.minor_units, pledge.amount.minor_units)
    if any(abs(value) > MAX_SAFE_INTEGER for value in values):
        raise ValueError("Invalid Money invariant")
    if pledge.amount.minor_units <= 0:
        return PledgeRejected(reason="non-positive-amount")
    if occasion.total_pledged.minor_units > occasion.budget.minor_units:
        raise ValueError("Invalid Occasion funding invariant")
    if pledge.amount.minor_units > occasion.budget.minor_units - occasion.total_pledged.minor_units:
        return PledgeRejected(reason="exceeds-budget")

    total_pledged = occasion.total_pledged.minor_units + pledge.amount.minor_units
    if abs(total_pledged) > MAX_SAFE_INTEGER:
        raise ValueError("Money addition overflowed")

    return PledgeAccepted(
        occasion=replace(occasion, total_pledged=create_money(total_pledged, pledge.amount.currency)),
    )
```
