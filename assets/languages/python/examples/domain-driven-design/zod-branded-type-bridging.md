```python
from dataclasses import dataclass
from typing import Any, Literal, NewType, Sequence

OccasionId = NewType("OccasionId", str)
ContributorId = NewType("ContributorId", str)
Currency = Literal["GBP", "USD", "EUR"]


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: Currency


def create_occasion_id(raw: str) -> OccasionId:
    if not raw.strip():
        raise ValueError("OccasionId cannot be empty")
    return OccasionId(raw)


def create_contributor_id(raw: str) -> ContributorId:
    if not raw.strip():
        raise ValueError("ContributorId cannot be empty")
    return ContributorId(raw)


def create_money(minor_units: int, currency: Currency) -> Money:
    if minor_units < 0:
        raise ValueError("Money cannot be negative")
    return Money(minor_units=minor_units, currency=currency)


def parse_currency(raw: str) -> Currency:
    if raw not in ("GBP", "USD", "EUR"):
        raise ValueError(f"Unsupported currency: {raw}")
    return raw  # type: ignore[return-value]


@dataclass(frozen=True)
class PledgeInput:
    occasion_id: OccasionId
    contributor_id: ContributorId
    amount: Money


# Parsing at the trust boundary -- raw, untrusted input becomes validated
# domain types. Raises ValueError (via the factories above) on bad input;
# the caller at the boundary (e.g. an HTTP handler) turns that into a 4xx.
def parse_pledge_input(raw: dict[str, Any]) -> PledgeInput:
    amount = raw["amount"]
    minor_units = int(amount["minorUnits"])
    if minor_units <= 0:
        raise ValueError("amount.minorUnits must be a positive integer")
    return PledgeInput(
        occasion_id=create_occasion_id(str(raw["occasionId"])),
        contributor_id=create_contributor_id(str(raw["contributorId"])),
        amount=create_money(minor_units, parse_currency(amount["currency"])),
    )


@dataclass(frozen=True)
class GiftIdea:
    id: str
    description: str


@dataclass(frozen=True)
class OccasionRow:
    id: str
    name: str
    budget_minor_units: int
    budget_currency: str
    pledged_minor_units: int
    is_funding_closed: bool


@dataclass(frozen=True)
class Occasion:
    id: OccasionId
    name: str
    gift_ideas: Sequence[GiftIdea]
    budget: Money
    total_pledged: Money
    is_funding_closed: bool


# Reconstitution from persistence -- same pattern, used at the integration
# boundary (a driven adapter in hexagonal architecture loads the gift ideas
# alongside the row).
def to_occasion(row: OccasionRow, gift_ideas: Sequence[GiftIdea]) -> Occasion:
    currency = parse_currency(row.budget_currency)
    return Occasion(
        id=create_occasion_id(row.id),
        name=row.name,
        gift_ideas=gift_ideas,
        budget=create_money(row.budget_minor_units, currency),
        total_pledged=create_money(row.pledged_minor_units, currency),
        is_funding_closed=row.is_funding_closed,
    )
```
