```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: str


@dataclass(frozen=True)
class OrderId:
    value: str


@dataclass(frozen=True)
class NewOrder:
    order_id: OrderId
    total: Money


@dataclass(frozen=True)
class Order:
    id: OrderId
    total: Money


@dataclass(frozen=True)
class PlaceOrderResult:
    success: bool
    reason: str | None = None


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    reason: str | None = None


class OrderRepository(Protocol):
    async def find_by_id(self, order_id: OrderId) -> Order | None: ...
    async def save(self, order: Order) -> None: ...


class PaymentGateway(Protocol):
    async def charge(self, amount: Money, order_id: OrderId) -> PaymentResult: ...


@dataclass(frozen=True)
class Occasion:
    total_pledged: Money
    budget: Money


@dataclass(frozen=True)
class ContributorEligibility:
    may_pledge: bool


@dataclass(frozen=True)
class Pledge:
    amount: Money


@dataclass(frozen=True)
class PledgeDecision:
    success: bool
    reason: str | None = None


# Use case — takes application-owned collaboration contracts (ports) as parameters
async def place_order(
    repo: OrderRepository,
    gateway: PaymentGateway,
    order: NewOrder,
) -> PlaceOrderResult: ...


# Domain service — takes only domain values
def pledge_contribution(
    occasion: Occasion,
    eligibility: ContributorEligibility,
    pledge: Pledge,
) -> PledgeDecision: ...
```
