```python
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ChargeId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("ChargeId must not be empty")


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: str


def create_charge_id(raw: str) -> ChargeId:
    return ChargeId(raw)


def create_money(minor_units: int, currency: str) -> Money:
    return Money(minor_units, currency)


def parse_currency(raw: str) -> str:
    return raw.upper()


@dataclass(frozen=True)
class StripeCharge:
    """The external system's model, exactly as Stripe hands it to us."""

    id: str
    amount: int  # integer minor units, per Stripe's contract
    currency: str  # lowercase ISO code
    status: str


@dataclass(frozen=True)
class PaymentAccepted:
    charge_id: ChargeId
    amount: Money
    success: Literal[True] = True


@dataclass(frozen=True)
class PaymentRejected:
    reason: str
    success: Literal[False] = False


PaymentResult = PaymentAccepted | PaymentRejected


def to_payment_result(charge: StripeCharge) -> PaymentResult:
    """Anti-Corruption Layer: translate Stripe's model into ours at the boundary."""
    if charge.status == "succeeded":
        return PaymentAccepted(
            charge_id=create_charge_id(charge.id),
            amount=create_money(charge.amount, parse_currency(charge.currency)),
        )
    return PaymentRejected(reason=f"Payment failed: {charge.status}")
```
