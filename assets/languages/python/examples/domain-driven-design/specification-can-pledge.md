```python
from dataclasses import dataclass
from typing import Literal, NewType, Sequence

Currency = Literal["GBP", "USD", "EUR"]
OccasionId = NewType("OccasionId", str)
GiftIdeaId = NewType("GiftIdeaId", str)
ContributorId = NewType("ContributorId", str)

_MAX_SAFE_INTEGER = 2**53 - 1


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: Currency


@dataclass(frozen=True)
class GiftIdea:
    id: GiftIdeaId
    status: Literal["proposed", "selected", "purchased"]


@dataclass(frozen=True)
class Occasion:
    id: OccasionId
    gift_ideas: Sequence[GiftIdea]
    budget: Money
    total_pledged: Money
    is_funding_closed: bool


@dataclass(frozen=True)
class ContributorEligibility:
    contributor_id: ContributorId
    may_pledge: bool


def _is_safe_integer(value: int) -> bool:
    return abs(value) <= _MAX_SAFE_INTEGER


# Specification: "can this eligible contributor pledge to this occasion?"
def can_pledge(occasion: Occasion, eligibility: ContributorEligibility, amount: Money) -> bool:
    values = (amount.minor_units, occasion.total_pledged.minor_units, occasion.budget.minor_units)
    if not all(_is_safe_integer(v) for v in values):
        return False
    if occasion.total_pledged.minor_units > occasion.budget.minor_units:
        return False
    return (
        eligibility.may_pledge
        and not occasion.is_funding_closed
        and amount.minor_units > 0
        and amount.currency == occasion.total_pledged.currency
        and occasion.total_pledged.currency == occasion.budget.currency
        and amount.minor_units <= occasion.budget.minor_units - occasion.total_pledged.minor_units
    )


# Compose specifications for complex eligibility
def is_gift_ready(occasion: Occasion) -> bool:
    return occasion.total_pledged.minor_units >= occasion.budget.minor_units and any(
        idea.status == "selected" for idea in occasion.gift_ideas
    )
```
