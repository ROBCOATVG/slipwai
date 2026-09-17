```python
# ❌ Business rule in the route handler
@app.post("/orders/{order_id}/approve")
async def approve_order(order_id: str) -> JSONResponse:
    order = await order_repo.find_by_id(order_id)
    if order.item_count > 100:
        await require_manager_approval(order)  # business rule!
    ...


# ✅ Business rule in the domain
from dataclasses import dataclass


@dataclass(frozen=True)
class OrderPlaced:
    order: "Order"


@dataclass(frozen=True)
class RequiresApproval:
    pass


PlaceOrderResult = OrderPlaced | RequiresApproval


def place_order(order: "Order") -> PlaceOrderResult:
    if order.item_count > 100:
        return RequiresApproval()
    return OrderPlaced(order=order)
```
