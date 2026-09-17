```python
import pytest


@pytest.mark.parametrize(
    "overrides, want_success",
    [
        ({"amount_minor_units": -100, "currency": "GBP"}, False),
        ({"amount_minor_units": 1_500_000, "currency": "GBP"}, False),
        ({"cvv": "12"}, False),
        ({}, True),
    ],
)
def test_validate_payment(overrides, want_success):
    payment = get_mock_payment(**overrides)
    assert validate(payment).success is want_success
```
