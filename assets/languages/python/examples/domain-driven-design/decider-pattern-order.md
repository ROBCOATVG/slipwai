```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int


@dataclass(frozen=True)
class PlaceCommand:
    type: Literal["place"] = "place"


@dataclass(frozen=True)
class ShipCommand:
    tracking_number: str
    type: Literal["ship"] = "ship"


OrderCommand = PlaceCommand | ShipCommand


@dataclass(frozen=True)
class OrderPlaced:
    items: tuple[OrderItem, ...]
    placed_at: datetime
    type: Literal["OrderPlaced"] = "OrderPlaced"


@dataclass(frozen=True)
class OrderShipped:
    tracking_number: str
    type: Literal["OrderShipped"] = "OrderShipped"


OrderEvent = OrderPlaced | OrderShipped


@dataclass(frozen=True)
class DraftOrder:
    items: tuple[OrderItem, ...]
    status: Literal["draft"] = "draft"


@dataclass(frozen=True)
class PlacedOrder:
    items: tuple[OrderItem, ...]
    placed_at: datetime
    status: Literal["placed"] = "placed"


@dataclass(frozen=True)
class ShippedOrder:
    items: tuple[OrderItem, ...]
    placed_at: datetime
    tracking_number: str
    status: Literal["shipped"] = "shipped"


OrderState = DraftOrder | PlacedOrder | ShippedOrder


@dataclass(frozen=True)
class OrderAccepted:
    events: tuple[OrderEvent, ...]
    accepted: Literal[True] = True


@dataclass(frozen=True)
class OrderRejected:
    reason: Literal["order-not-draft", "order-not-placed"]
    accepted: Literal[False] = False


OrderDecision = OrderAccepted | OrderRejected


# 1. Decide: command + current state → an explicit acceptance or rejection
def decide(command: OrderCommand, state: OrderState, now: datetime) -> OrderDecision:
    match command:
        case PlaceCommand():
            if state.status != "draft":
                return OrderRejected(reason="order-not-draft")
            return OrderAccepted(events=(OrderPlaced(items=state.items, placed_at=now),))
        case ShipCommand(tracking_number=tracking_number):
            if state.status != "placed":
                return OrderRejected(reason="order-not-placed")
            return OrderAccepted(events=(OrderShipped(tracking_number=tracking_number),))
        case _:
            raise AssertionError(f"Unhandled command: {command!r}")


# 2. Evolve: state + event → new state (pure state transformation).
# OrderState is a discriminated union of lifecycle phases (see "Make Illegal
# States Unrepresentable"), so each case builds the full target variant —
# there is no partial "reuse a draft's shape as a shipped order" shortcut.
def evolve(state: OrderState, event: OrderEvent) -> OrderState:
    match event:
        case OrderPlaced(items=items, placed_at=placed_at):
            if state.status != "draft":
                raise ValueError(f"Corrupt order history: OrderPlaced cannot follow {state.status}")
            return PlacedOrder(items=items, placed_at=placed_at)
        case OrderShipped(tracking_number=tracking_number):
            if state.status != "placed":
                raise ValueError(f"Corrupt order history: OrderShipped cannot follow {state.status}")
            return ShippedOrder(
                items=state.items,
                placed_at=state.placed_at,
                tracking_number=tracking_number,
            )
        case _:
            raise AssertionError(f"Unhandled event: {event!r}")


# 3. Initial state
INITIAL_STATE: OrderState = DraftOrder(items=())
```
