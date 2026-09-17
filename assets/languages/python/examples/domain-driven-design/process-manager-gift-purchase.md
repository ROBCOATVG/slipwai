```python
from dataclasses import dataclass, replace
from typing import Literal


@dataclass(frozen=True)
class OccasionId:
    value: str


# --- phases ---


@dataclass(frozen=True)
class AwaitingPayment:
    occasion_id: OccasionId
    step: Literal["awaiting-payment"] = "awaiting-payment"


@dataclass(frozen=True)
class AwaitingShipment:
    payment_id: str
    step: Literal["awaiting-shipment"] = "awaiting-shipment"


@dataclass(frozen=True)
class Complete:
    tracking_number: str
    step: Literal["complete"] = "complete"


@dataclass(frozen=True)
class Failed:
    reason: str
    step: Literal["failed"] = "failed"


GiftPurchasePhase = AwaitingPayment | AwaitingShipment | Complete | Failed


@dataclass(frozen=True)
class GiftPurchaseProcess:
    phase: GiftPurchasePhase
    processed_event_ids: tuple[str, ...]


# --- events (each carries the id needed for idempotency) ---


@dataclass(frozen=True)
class PaymentSucceeded:
    id: str
    payment_id: str
    type: Literal["PaymentSucceeded"] = "PaymentSucceeded"


@dataclass(frozen=True)
class PaymentFailed:
    id: str
    type: Literal["PaymentFailed"] = "PaymentFailed"


@dataclass(frozen=True)
class GiftShipped:
    id: str
    tracking_number: str
    type: Literal["GiftShipped"] = "GiftShipped"


GiftPurchaseEvent = PaymentSucceeded | PaymentFailed | GiftShipped


# --- commands the process manager emits ---


@dataclass(frozen=True)
class ShipGift:
    payment_id: str
    idempotency_key: str
    type: Literal["ShipGift"] = "ShipGift"


@dataclass(frozen=True)
class ReleaseBudgetHold:
    occasion_id: OccasionId
    idempotency_key: str
    type: Literal["ReleaseBudgetHold"] = "ReleaseBudgetHold"


GiftPurchaseCommand = ShipGift | ReleaseBudgetHold


@dataclass(frozen=True)
class Applied:
    new_state: GiftPurchaseProcess
    commands: tuple[GiftPurchaseCommand, ...]
    outcome: Literal["applied"] = "applied"


@dataclass(frozen=True)
class Ignored:
    new_state: GiftPurchaseProcess
    outcome: Literal["duplicate", "out-of-order"]
    commands: tuple[()] = ()


ProcessReaction = Applied | Ignored


# Apply each event once, and only in the phase that can consume it.
def advance_gift_purchase(state: GiftPurchaseProcess, event: GiftPurchaseEvent) -> ProcessReaction:
    if event.id in state.processed_event_ids:
        return Ignored(new_state=state, outcome="duplicate")

    processed_event_ids = (*state.processed_event_ids, event.id)

    match event:
        case PaymentSucceeded(payment_id=payment_id):
            if state.phase.step != "awaiting-payment":
                return Ignored(new_state=state, outcome="out-of-order")
            return Applied(
                new_state=replace(
                    state,
                    phase=AwaitingShipment(payment_id=payment_id),
                    processed_event_ids=processed_event_ids,
                ),
                commands=(ShipGift(payment_id=payment_id, idempotency_key=event.id),),
            )
        case PaymentFailed():
            if state.phase.step != "awaiting-payment":
                return Ignored(new_state=state, outcome="out-of-order")
            occasion_id = state.phase.occasion_id
            return Applied(
                new_state=replace(
                    state,
                    phase=Failed(reason="payment-declined"),
                    processed_event_ids=processed_event_ids,
                ),
                commands=(ReleaseBudgetHold(occasion_id=occasion_id, idempotency_key=event.id),),
            )
        case GiftShipped(tracking_number=tracking_number):
            if state.phase.step != "awaiting-shipment":
                return Ignored(new_state=state, outcome="out-of-order")
            return Applied(
                new_state=replace(
                    state,
                    phase=Complete(tracking_number=tracking_number),
                    processed_event_ids=processed_event_ids,
                ),
                commands=(),
            )
        case _:
            raise AssertionError(f"Unhandled event: {event!r}")
```
