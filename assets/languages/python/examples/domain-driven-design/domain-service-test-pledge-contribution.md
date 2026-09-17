```python
from dataclasses import dataclass, replace
from typing import Literal


@dataclass(frozen=True)
class OccasionId:
    value: str


@dataclass(frozen=True)
class PledgeId:
    value: str


@dataclass(frozen=True)
class ContributorId:
    value: str


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: str


def create_money(minor_units: int, currency: str) -> Money:
    return Money(minor_units, currency)


def create_pledge_id(value: str) -> PledgeId:
    return PledgeId(value)


@dataclass(frozen=True)
class Occasion:
    id: OccasionId
    is_funding_closed: bool
    total_pledged: Money
    budget: Money


@dataclass(frozen=True)
class ContributorEligibility:
    contributor_id: ContributorId
    may_pledge: bool


@dataclass(frozen=True)
class PledgeAccepted:
    occasion: Occasion
    success: Literal[True] = True


@dataclass(frozen=True)
class PledgeRejected:
    reason: str
    success: Literal[False] = False


PledgeDecision = PledgeAccepted | PledgeRejected


@dataclass(frozen=True)
class Pledge:
    id: PledgeId
    amount: Money


def pledge_contribution(
    occasion: Occasion,
    eligibility: ContributorEligibility,
    pledge: Pledge,
) -> PledgeDecision:
    if not eligibility.may_pledge:
        return PledgeRejected(reason="contributor-ineligible")
    if occasion.is_funding_closed:
        return PledgeRejected(reason="funding-closed")
    if pledge.amount.minor_units > occasion.budget.minor_units - occasion.total_pledged.minor_units:
        return PledgeRejected(reason="exceeds-budget")
    total_pledged = occasion.total_pledged.minor_units + pledge.amount.minor_units
    return PledgeAccepted(
        occasion=replace(occasion, total_pledged=create_money(total_pledged, pledge.amount.currency)),
    )


def get_test_occasion(**overrides: object) -> Occasion:
    defaults = Occasion(
        id=OccasionId("occasion-1"),
        is_funding_closed=False,
        total_pledged=create_money(0, "GBP"),
        budget=create_money(50_000, "GBP"),
    )
    return replace(defaults, **overrides)


def get_test_contributor_eligibility(**overrides: object) -> ContributorEligibility:
    defaults = ContributorEligibility(contributor_id=ContributorId("contributor-1"), may_pledge=True)
    return replace(defaults, **overrides)


def test_pledge_contribution_rejects_pledge_when_contributor_is_ineligible() -> None:
    occasion = get_test_occasion()
    eligibility = get_test_contributor_eligibility(may_pledge=False)

    result = pledge_contribution(
        occasion,
        eligibility,
        Pledge(id=create_pledge_id("pledge-1"), amount=create_money(5_000, "GBP")),
    )

    assert result.success is False
```
