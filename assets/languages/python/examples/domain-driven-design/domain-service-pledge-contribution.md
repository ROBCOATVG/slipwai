```python
from dataclasses import dataclass, replace
from typing import Literal, NewType, Sequence, Union

Currency = Literal["GBP", "USD", "EUR"]
OccasionId = NewType("OccasionId", str)
PledgeId = NewType("PledgeId", str)
ContributorId = NewType("ContributorId", str)

_MAX_SAFE_INTEGER = 2**53 - 1


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: Currency


def create_money(minor_units: int, currency: Currency) -> Money:
    if minor_units < 0:
        raise ValueError("Money cannot be negative")
    return Money(minor_units=minor_units, currency=currency)


@dataclass(frozen=True)
class Occasion:
    id: OccasionId
    budget: Money
    total_pledged: Money
    is_funding_closed: bool


@dataclass(frozen=True)
class ContributorEligibility:
    contributor_id: ContributorId
    may_pledge: bool


@dataclass(frozen=True)
class Pledge:
    id: PledgeId
    amount: Money


@dataclass(frozen=True)
class PledgeRecorded:
    id: PledgeId
    occasion_id: OccasionId
    contributor_id: ContributorId
    amount: Money
    type: Literal["PledgeRecorded"] = "PledgeRecorded"


@dataclass(frozen=True)
class PledgeAccepted:
    occasion: Occasion
    events: Sequence[PledgeRecorded]
    success: Literal[True] = True


PledgeRejectionReason = Literal[
    "contributor-ineligible",
    "non-positive-amount",
    "currency-mismatch",
    "exceeds-budget",
    "funding-closed",
]


@dataclass(frozen=True)
class PledgeRejected:
    reason: PledgeRejectionReason
    success: Literal[False] = False


PledgeDecision = Union[PledgeAccepted, PledgeRejected]


# ---------------------------------------------------------------------------
# WRONG -- cramming an external eligibility policy into one entity
# ---------------------------------------------------------------------------
def add_contribution_wrong(occasion: Occasion, pledge: Pledge) -> Occasion:
    """This cannot know whether the contributor is currently eligible."""
    raise NotImplementedError("an entity method has no access to eligibility")


# ---------------------------------------------------------------------------
# CORRECT -- pure domain service consumes a read-only policy fact
# ---------------------------------------------------------------------------
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
    if not all(abs(v) <= _MAX_SAFE_INTEGER for v in values):
        raise ValueError("Invalid Money invariant")

    if pledge.amount.minor_units <= 0:
        return PledgeRejected(reason="non-positive-amount")
    if occasion.total_pledged.minor_units > occasion.budget.minor_units:
        raise ValueError("Invalid Occasion funding invariant")
    if pledge.amount.minor_units > occasion.budget.minor_units - occasion.total_pledged.minor_units:
        return PledgeRejected(reason="exceeds-budget")

    total_pledged = occasion.total_pledged.minor_units + pledge.amount.minor_units
    if abs(total_pledged) > _MAX_SAFE_INTEGER:
        raise ValueError("Money addition overflowed")

    updated_occasion = replace(
        occasion,
        total_pledged=create_money(total_pledged, pledge.amount.currency),
    )
    return PledgeAccepted(
        occasion=updated_occasion,
        events=[
            PledgeRecorded(
                id=pledge.id,
                occasion_id=occasion.id,
                contributor_id=eligibility.contributor_id,
                amount=pledge.amount,
            )
        ],
    )
```
