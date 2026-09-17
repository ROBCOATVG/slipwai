```python
@pytest.fixture
def test_order() -> Order:
    return make_order()


def test_saves_order_and_charges_payment_on_success(test_order: Order) -> None:
    order_repo = FakeOrderRepository()
    payment_gateway = FakePaymentGateway(always_succeeds=True)
    order_placement = OrderPlacement(order_repo, payment_gateway)

    result = order_placement.place_order(test_order)

    assert result.success is True
    assert len(order_repo.saved_entities) == 1


def test_does_not_save_order_when_payment_fails(test_order: Order) -> None:
    order_repo = FakeOrderRepository()
    payment_gateway = FakePaymentGateway(always_fails=True)
    order_placement = OrderPlacement(order_repo, payment_gateway)

    result = order_placement.place_order(test_order)

    assert result.success is False
    assert len(order_repo.saved_entities) == 0
```
