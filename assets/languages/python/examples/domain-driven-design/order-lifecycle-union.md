```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Sequence


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int


@dataclass(frozen=True)
class DraftOrder:
    items: Sequence[OrderItem]
    status: Literal["draft"] = "draft"


@dataclass(frozen=True)
class PlacedOrder:
    items: Sequence[OrderItem]
    placed_at: datetime
    status: Literal["placed"] = "placed"


@dataclass(frozen=True)
class ShippedOrder:
    items: Sequence[OrderItem]
    placed_at: datetime
    shipped_at: datetime
    tracking_number: str
    status: Literal["shipped"] = "shipped"


# Each variant carries only the data valid for that state; status is the
# discriminant that match/case (and static type checkers) narrow on.
Order = DraftOrder | PlacedOrder | ShippedOrder
```
