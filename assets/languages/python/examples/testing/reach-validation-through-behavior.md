```python
import pytest


# Tests covering validation WITHOUT testing the validator directly
@pytest.mark.parametrize(
    "overrides",
    [
        {"amount_minor_units": -100, "currency": "GBP"},
        {"amount_minor_units": 1_500_000, "currency": "GBP"},
        {"cvv": "12"},
    ],
)
def test_process_payment_rejects_invalid_input(overrides):
    payment = get_mock_payment(**overrides)
    result = process_payment(payment)
    assert result.success is False


def test_process_payment_accepts_valid_input():
    payment = get_mock_payment(amount_minor_units=10_000, currency="GBP", cvv="123")
    result = process_payment(payment)
    assert result.success is True


# ✅ Result: validation branches are exercised through the public behavior
```
