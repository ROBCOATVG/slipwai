```python
from typing import Protocol
from dataclasses import dataclass


# Driving port — exposed by the application, called by driving adapters
class ForPlacingOrders(Protocol):
    async def place_order(self, command: "PlaceOrderCommand") -> "PlaceOrderResult": ...


# Driven port — application-owned because the use case consumes it
class UserRepository(Protocol):
    async def find_by_id(self, user_id: "UserId") -> "User | None": ...
    async def save(self, user: "User") -> None: ...


@dataclass(frozen=True)
class PaymentPrepared:
    payment_id: "PaymentId"


@dataclass(frozen=True)
class PaymentPrepareFailed:
    reason: "PaymentFailure"


PreparePaymentResult = PaymentPrepared | PaymentPrepareFailed


@dataclass(frozen=True)
class PaymentPaid:
    charge_id: "ChargeId"


@dataclass(frozen=True)
class PaymentDeclined:
    reason: "PaymentFailure"


@dataclass(frozen=True)
class PaymentPending:
    pass


PaymentOutcome = PaymentPaid | PaymentDeclined | PaymentPending


# Driven port — application-owned because the use case consumes it
class PaymentGateway(Protocol):
    async def prepare_payment(
        self,
        *,
        amount: "Money",
        reference: "OrderId",
        idempotency_key: "OrderId",
    ) -> PreparePaymentResult: ...

    async def complete_payment(
        self,
        *,
        payment_id: "PaymentId",
        payment_info: "PaymentInfo",
    ) -> PaymentOutcome: ...


# Driven port — event publishing (outbound to message brokers)
class OrderEventPublisher(Protocol):
    async def publish(self, event: "OrderEvent") -> None: ...
```
