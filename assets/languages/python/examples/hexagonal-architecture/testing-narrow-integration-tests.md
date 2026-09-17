```python
# Real database — fresh db per test, no shared state
def test_repository_round_trips_an_order_through_persistence(test_db: sqlite3.Connection) -> None:
    repo = SqlOrderRepository(test_db)
    order = make_order()

    repo.save(order)

    assert repo.find_by_id(order.id) == order


# Real HTTP via a mocked transport
@responses.activate
def test_payment_gateway_returns_success_on_valid_charge() -> None:
    responses.add(
        responses.POST,
        "https://api.stripe.com/v1/charges",
        json={"id": "ch_123", "status": "succeeded"},
        status=200,
    )
    gateway = StripePaymentGateway(api_key="sk_test")

    result = gateway.charge(make_money(1_000, "GBP"), make_payment_info())

    assert result.success is True
```
