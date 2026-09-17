```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int


@dataclass(frozen=True)
class DraftOrder:
    items: tuple[OrderItem, ...]
    status: Literal["draft"] = "draft"


@dataclass(frozen=True)
class PlacedOrder:
    items: tuple[OrderItem, ...]
    placed_at: datetime
    status: Literal["placed"] = "placed"


OrderState = DraftOrder | PlacedOrder


@dataclass(frozen=True)
class PlaceCommand:
    type: Literal["place"] = "place"


@dataclass(frozen=True)
class OrderPlaced:
    items: tuple[OrderItem, ...]
    placed_at: datetime
    type: Literal["OrderPlaced"] = "OrderPlaced"


@dataclass(frozen=True)
class OrderAccepted:
    events: tuple[OrderPlaced, ...]
    accepted: Literal[True] = True


@dataclass(frozen=True)
class OrderRejected:
    reason: Literal["order-not-draft"]
    accepted: Literal[False] = False


OrderDecision = OrderAccepted | OrderRejected


def decide(command: PlaceCommand, state: OrderState, now: datetime) -> OrderDecision:
    if state.status != "draft":
        return OrderRejected(reason="order-not-draft")
    return OrderAccepted(events=(OrderPlaced(items=state.items, placed_at=now),))


test_item = OrderItem(sku="mug-01", quantity=2)


def test_decide_produces_order_placed_event_for_a_draft_order() -> None:
    now = datetime(2026, 3, 20)
    state = DraftOrder(items=(test_item,))

    decision = decide(PlaceCommand(), state, now)

    assert decision == OrderAccepted(events=(OrderPlaced(items=(test_item,), placed_at=now),))


def test_decide_rejects_placing_an_already_placed_order() -> None:
    now = datetime(2026, 3, 20)
    some_date = datetime(2026, 3, 18)
    state = PlacedOrder(items=(test_item,), placed_at=some_date)

    decision = decide(PlaceCommand(), state, now)

    assert decision == OrderRejected(reason="order-not-draft")
```
