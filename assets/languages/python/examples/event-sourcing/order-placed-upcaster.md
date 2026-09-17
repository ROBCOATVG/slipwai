```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NoReturn, Union


@dataclass(frozen=True, slots=True)
class OrderPlacedV1:
    order_id: str
    total_minor_units: int
    currency: Currency
    type: Literal["OrderPlaced"] = "OrderPlaced"
    version: Literal[1] = 1


@dataclass(frozen=True, slots=True)
class TotalAmount:
    minor_units: int
    currency: Currency


@dataclass(frozen=True, slots=True)
class OrderPlacedV2:
    order_id: str
    total_amount: TotalAmount  # structural change from V1's flat fields
    type: Literal["OrderPlaced"] = "OrderPlaced"
    version: Literal[2] = 2


OrderPlaced = OrderPlacedV2  # the shape the domain uses today
StoredOrderPlaced = Union[OrderPlacedV1, OrderPlacedV2]


def upcast_order_placed_v1_to_v2(event: OrderPlacedV1) -> OrderPlacedV2:
    return OrderPlacedV2(
        order_id=event.order_id,
        total_amount=TotalAmount(event.total_minor_units, event.currency),
    )


def _assert_never(value: NoReturn) -> NoReturn:
    raise AssertionError(f"Unhandled variant: {value!r}")


# On read: dispatch on the stored version and upcast forward to the current shape.
# A union of versioned dataclasses keeps this exhaustive and cast-free.
def upcast_order_placed(raw: StoredOrderPlaced) -> OrderPlaced:
    match raw:
        case OrderPlacedV1():
            return upcast_order_placed_v1_to_v2(raw)
        case OrderPlacedV2():
            return raw
        case _:
            _assert_never(raw)
```
