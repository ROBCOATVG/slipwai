```python
from dataclasses import replace


def make_item(**overrides) -> Item:
    defaults = Item(id="item-1", name="Test Item", weight_grams=100)
    return replace(defaults, **overrides)


def make_order(**overrides) -> Order:
    defaults = Order(
        id="order-1",
        items=[make_item()],  # ✅ Compose factories
        customer=make_customer(),  # ✅ Compose factories
        payment=make_payment(),  # ✅ Compose factories
    )
    return replace(defaults, **overrides)


# Usage - override nested objects
def test_calculates_total_with_multiple_items():
    order = make_order(items=[make_item(weight_grams=100), make_item(weight_grams=200)])
    assert calculate_total_weight_grams(order) == 300
```
