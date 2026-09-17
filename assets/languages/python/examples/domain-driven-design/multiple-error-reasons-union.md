```python
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class OrderCreated:
    order: "Order"


@dataclass(frozen=True)
class OrderRejected:
    reason: Literal[
        "empty-cart",
        "item-out-of-stock",
        "payment-declined",
        "address-invalid",
        "daily-limit-exceeded",
    ]


CreateOrderResult = OrderCreated | OrderRejected
```
