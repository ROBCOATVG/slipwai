```python
from dataclasses import dataclass, replace
from typing import Literal, NewType, Sequence

Currency = Literal["GBP", "USD", "EUR"]
OccasionId = NewType("OccasionId", str)
GiftIdeaId = NewType("GiftIdeaId", str)


def create_occasion_id(raw: str) -> OccasionId:
    if not raw.strip():
        raise ValueError("OccasionId cannot be empty")
    return OccasionId(raw)


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: Currency


def create_money(minor_units: int, currency: Currency) -> Money:
    if minor_units < 0:
        raise ValueError("Money cannot be negative")
    return Money(minor_units=minor_units, currency=currency)


@dataclass(frozen=True)
class GiftIdea:
    id: GiftIdeaId
    description: str


@dataclass(frozen=True)
class Occasion:
    id: OccasionId
    name: str
    gift_ideas: Sequence[GiftIdea]
    budget: Money
    total_pledged: Money
    is_funding_closed: bool


def get_test_occasion(**overrides: object) -> Occasion:
    """Test data factory building a default, valid Occasion. Pass keyword
    overrides for any field, e.g. get_test_occasion(is_funding_closed=True).
    """
    default = Occasion(
        id=create_occasion_id("occasion-1"),
        name="Mum's Birthday",
        gift_ideas=(),
        budget=create_money(10_000, "GBP"),
        total_pledged=create_money(0, "GBP"),
        is_funding_closed=False,
    )
    return replace(default, **overrides)


def test_get_test_occasion_returns_sane_defaults() -> None:
    occasion = get_test_occasion()
    assert occasion.name == "Mum's Birthday"
    assert occasion.budget == Money(minor_units=10_000, currency="GBP")
    assert occasion.is_funding_closed is False


def test_get_test_occasion_applies_overrides() -> None:
    occasion = get_test_occasion(is_funding_closed=True, name="Dad's Retirement")
    assert occasion.is_funding_closed is True
    assert occasion.name == "Dad's Retirement"
```
