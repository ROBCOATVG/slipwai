```python
def test_rejects_negative_amounts():
    payment = get_mock_payment(amount_minor_units=-100, currency="GBP")
    result = process_payment(payment)
    assert result.success is False
    assert "Amount must be positive" in result.error


def test_rejects_invalid_cvv():
    payment = get_mock_payment(cvv="12")  # Only 2 digits
    result = process_payment(payment)
    assert result.success is False
    assert "Invalid CVV" in result.error


def test_processes_valid_payments():
    payment = get_mock_payment(amount_minor_units=10_000, currency="GBP", cvv="123")
    result = process_payment(payment)
    assert result.success is True
    assert isinstance(result.transaction_id, str)
```
