```python
from dataclasses import dataclass
from typing import Protocol


# WRONG — constructs its own dependencies internally (untestable, tightly coupled)
async def create_order_wrong(order: "NewOrder") -> None:
    repo = SqlAlchemyOrderRepository(get_session())              # hardcoded
    gateway = StripePaymentGateway(os.environ["STRIPE_KEY"])     # hardcoded
    ...


# RIGHT — dependencies injected as constructor parameters


@dataclass(frozen=True)
class Recorded:
    order: "Order"


@dataclass(frozen=True)
class Conflict:
    pass


RecordPaymentResult = Recorded | Conflict
RecordChargeResult = Recorded | Conflict


@dataclass(frozen=True)
class OrderPlaced:
    order: "Order"


@dataclass(frozen=True)
class OrderPlacementFailed:
    reason: str


OrderResult = OrderPlaced | OrderPlacementFailed


class OrderRepository(Protocol):
    async def find_by_id(self, order_id: str) -> "Order | None": ...

    async def find_or_create_pending(self, order: "NewOrder") -> "Order": ...

    async def record_payment(
        self, order_id: str, payment_id: str, *, expected_version: int
    ) -> RecordPaymentResult: ...

    async def record_charge(
        self, order_id: str, charge_id: str, *, expected_version: int
    ) -> RecordChargeResult: ...


class ForPlacingOrders(Protocol):
    async def place_order(self, order: "NewOrder") -> OrderResult: ...


class OrderPlacement:
    """Use case — dependencies arrive as constructor parameters, never built inline."""

    def __init__(self, repo: OrderRepository, gateway: "PaymentGateway") -> None:
        self._repo = repo
        self._gateway = gateway

    async def place_order(self, order: "NewOrder") -> OrderResult:
        payable = await self._repo.find_or_create_pending(order)
        if payable.status == "paid":
            return OrderPlaced(order=payable)

        if payable.payment_id is None:
            prepared = await self._gateway.prepare_payment(
                amount=payable.total,
                reference=payable.id,
                idempotency_key=payable.id,
            )
            if isinstance(prepared, PaymentPrepareFailed):
                return OrderPlacementFailed(reason=prepared.reason)

            payment_recorded = await self._repo.record_payment(
                payable.id, prepared.payment_id, expected_version=payable.version
            )
            if isinstance(payment_recorded, Recorded):
                payable = payment_recorded.order
            else:
                current = await self._repo.find_by_id(payable.id)
                if current is not None and current.status == "paid":
                    return OrderPlaced(order=current)
                if current is None or current.status != "pending" or current.payment_id is None:
                    return OrderPlacementFailed(reason="concurrent-change")
                payable = current

        if payable.payment_id is None:
            return OrderPlacementFailed(reason="concurrent-change")

        payment = await self._gateway.complete_payment(
            payment_id=payable.payment_id, payment_info=payable.payment
        )
        if isinstance(payment, PaymentPending):
            return OrderPlacementFailed(reason="payment-pending")
        if isinstance(payment, PaymentDeclined):
            return OrderPlacementFailed(reason=payment.reason)

        recorded = await self._repo.record_charge(
            payable.id, payment.charge_id, expected_version=payable.version
        )
        if isinstance(recorded, Recorded):
            return OrderPlaced(order=recorded.order)

        current = await self._repo.find_by_id(payable.id)
        if (
            current is not None
            and current.status == "paid"
            and current.charge_id == payment.charge_id
        ):
            return OrderPlaced(order=current)
        return OrderPlacementFailed(reason="concurrent-change")
```
