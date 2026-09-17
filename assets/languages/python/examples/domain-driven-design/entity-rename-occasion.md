```python
from dataclasses import dataclass, replace
from typing import Literal, NewType, Sequence

OccasionId = NewType("OccasionId", str)
GiftIdeaId = NewType("GiftIdeaId", str)
Currency = Literal["GBP", "USD", "EUR"]


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: Currency


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


# Immutable update -- returns new valid state
def rename_occasion(occasion: Occasion, new_name: str) -> Occasion:
    return replace(occasion, name=new_name)
```
