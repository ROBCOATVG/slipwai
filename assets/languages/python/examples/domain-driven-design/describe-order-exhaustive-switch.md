```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, NoReturn, Sequence


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


Order = DraftOrder | PlacedOrder | ShippedOrder


def _assert_never(value: NoReturn) -> NoReturn:
    raise AssertionError(f"Unhandled order variant: {value!r}")


def describe_order(order: Order) -> str:
    match order:
        case DraftOrder(items=items):
            return f"Draft with {len(items)} items"
        case PlacedOrder(placed_at=placed_at):
            return f"Placed at {placed_at.isoformat()}"
        case ShippedOrder(tracking_number=tracking_number):
            return f"Shipped: {tracking_number}"
        case _:
            # A type checker that understands match exhaustiveness (e.g.
            # pyright) narrows `order` to `Never` here once every variant
            # above is handled; adding a new Order variant without a case
            # here becomes a static type error, not just a runtime one.
            return _assert_never(order)
```
