```python
def test_calculates_shipment_weight():
    order = create_order(items=[item1, item2])
    assert order.calculate_weight_grams() == 230
```
