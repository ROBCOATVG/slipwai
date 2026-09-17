```python
class FakeOrderRepository:
    """In-memory OrderRepository fake — satisfies the OrderRepository protocol
    structurally so use-case tests never touch a real database."""

    def __init__(self) -> None:
        self._store: dict[OrderId, Order] = {}
        self.saved_entities: list[Order] = []

    def find_by_id(self, order_id: OrderId) -> Order | None:
        return self._store.get(order_id)

    def save(self, order: Order) -> None:
        self._store[order.id] = order
        self.saved_entities.append(order)
```
