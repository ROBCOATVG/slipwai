```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

# --- minimal supporting domain types (the Decider itself lives elsewhere in the skill) ---


@dataclass(frozen=True)
class OrderId:
    value: str


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int


@dataclass(frozen=True)
class OrderState:
    status: Literal["draft", "placed", "shipped"]
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


# --- the pattern this file actually illustrates ---


@dataclass(frozen=True)
class StoredOrder:
    state: OrderState
    version: int


class OrderRepository(Protocol):
    async def find_by_id(self, order_id: OrderId) -> StoredOrder | None: ...

    async def save(self, state: OrderState, expected_version: int) -> Literal["saved", "conflict"]: ...


class OrderNotifier(Protocol):
    async def notify(self, event: OrderEvent) -> None: ...


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
    order_repo: OrderRepository,
    notifier: OrderNotifier,
    command: PlaceOrderCommand,
    now: datetime,
) -> PlaceOrderResult:
    stored = await order_repo.find_by_id(command.order_id)
    if stored is None:
        return PlaceOrderRejected(reason="not-found")

    decision = decide(command, stored.state, now)
    if not decision.accepted:
        return PlaceOrderRejected(reason=decision.reason)

    events = decision.events
    new_state = stored.state
    for event in events:
        new_state = evolve(new_state, event)

    saved = await order_repo.save(new_state, stored.version)
    if saved == "conflict":
        return PlaceOrderRejected(reason="concurrent-change")

    # Dispatch in-process — simple but non-durable.
    for event in events:
        await notifier.notify(event)

    return PlaceOrderAccepted(order=new_state)
```
