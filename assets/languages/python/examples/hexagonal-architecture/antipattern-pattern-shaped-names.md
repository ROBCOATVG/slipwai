```python
from typing import Protocol


# ❌ Names the pattern or type mechanism
class IPaymentPort(Protocol):
    async def charge(self, amount: "Money", payment_info: "PaymentInfo") -> "ChargeResult": ...


class PaymentGatewayImpl:
    async def charge(self, amount: "Money", payment_info: "PaymentInfo") -> "ChargeResult": ...


async def place_order_use_case(order: "NewOrder") -> "OrderResult": ...


# ✅ Names the role and the concrete adapter
class PaymentGateway(Protocol):
    async def charge(self, amount: "Money", payment_info: "PaymentInfo") -> "ChargeResult": ...


class StripePaymentGateway:
    async def charge(self, amount: "Money", payment_info: "PaymentInfo") -> "ChargeResult": ...


async def place_order(order: "NewOrder") -> "OrderResult": ...
```
