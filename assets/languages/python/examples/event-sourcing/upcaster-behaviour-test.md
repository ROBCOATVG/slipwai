```python
from __future__ import annotations


def test_should_upcast_a_v1_order_placed_into_the_current_shape_the_domain_can_fold() -> None:
    v1 = OrderPlacedV1(order_id="o-1", total_minor_units=4_000, currency="EUR")

    current = upcast_order_placed(v1)

    assert current == OrderPlacedV2(
        order_id="o-1",
        total_amount=TotalAmount(minor_units=4_000, currency="EUR"),
    )
```
