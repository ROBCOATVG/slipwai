```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol


@dataclass(frozen=True)
class OrderId:
    value: str


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int


@dataclass(frozen=True)
class OrderState:
    status: Literal["draft", "placed"]
    items: tuple[OrderItem, ...]


@dataclass(frozen=True)
class PlaceOrderCommand:
    order_id: OrderId
    type: Literal["place"] = "place"


@dataclass(frozen=True)
class OrderPlaced:
    items: tuple[OrderItem, ...]
    placed_at: datetime
    type: Literal["OrderPlaced"] = "OrderPlaced"


OrderEvent = OrderPlaced  # other event variants live alongside this one


@dataclass(frozen=True)
class OrderAccepted:
    events: tuple[OrderEvent, ...]
    accepted: Literal[True] = True


@dataclass(frozen=True)
class OrderRejected:
    reason: str
    accepted: Literal[False] = False


OrderDecision = OrderAccepted | OrderRejected


def decide(command: PlaceOrderCommand, state: OrderState, now: datetime) -> OrderDecision:
    if state.status != "draft":
        return OrderRejected(reason="order-not-draft")
    return OrderAccepted(events=(OrderPlaced(items=state.items, placed_at=now),))


def evolve(state: OrderState, event: OrderEvent) -> OrderState:
    return OrderState(status="placed", items=event.items)


@dataclass(frozen=True)
class StoredOrder:
    state: OrderState
    version: int


# Application-owned persistence contract — a driven port when hexagonal architecture is used.
# The contract requires one atomic aggregate + outbox operation.
class PlaceOrderPersistence(Protocol):
    async def find_order_by_id(self, order_id: OrderId) -> StoredOrder | None: ...

    async def save_with_outbox(
        self,
        state: OrderState,
        events: tuple[OrderEvent, ...],
        expected_version: int,
    ) -> Literal["saved", "conflict"]: ...


@dataclass(frozen=True)
class PlaceOrderAccepted:
    order: OrderState
    success: Literal[True] = True


@dataclass(frozen=True)
class PlaceOrderRejected:
    reason: str
    success: Literal[False] = False


PlaceOrderResult = PlaceOrderAccepted | PlaceOrderRejected


async def handle_place_order(
    persistence: PlaceOrderPersistence,
    command: PlaceOrderCommand,
    now: datetime,
) -> PlaceOrderResult:
    stored = await persistence.find_order_by_id(command.order_id)
    if stored is None:
        return PlaceOrderRejected(reason="not-found")

    decision = decide(command, stored.state, now)
    if not decision.accepted:
        return PlaceOrderRejected(reason=decision.reason)

    events = decision.events
    new_state = stored.state
    for event in events:
        new_state = evolve(new_state, event)

    # One compare-and-save operation persists aggregate + outbox, or neither.
    saved = await persistence.save_with_outbox(new_state, events, stored.version)
    if saved == "conflict":
        return PlaceOrderRejected(reason="concurrent-change")

    return PlaceOrderAccepted(order=new_state)
```
