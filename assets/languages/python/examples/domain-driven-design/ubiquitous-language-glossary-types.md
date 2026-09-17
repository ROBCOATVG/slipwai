```python
from dataclasses import dataclass
from typing import Literal, NewType

GiftIdeaId = NewType("GiftIdeaId", str)
OccasionId = NewType("OccasionId", str)
Currency = Literal["GBP", "USD", "EUR"]


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: Currency


GiftIdeaStatus = Literal["proposed", "selected", "purchased"]


# Uses domain language
@dataclass(frozen=True)
class GiftIdea:
    id: GiftIdeaId
    description: str
    occasion: OccasionId
    estimated_cost: Money
    status: GiftIdeaStatus


# Technical jargon -- avoid this shape. "Item"/"text"/"parent_id" say
# nothing about the domain, unlike GiftIdea's fields above.
@dataclass(frozen=True)
class Item:
    id: str
    text: str
    parent_id: str
```
