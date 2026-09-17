```python
def test_rejects_invalid_payment():
    payment = get_mock_payment(amount_minor_units=-100, currency="GBP")
    result = validate(payment)
    assert result.success is False
    assert "Amount must be positive" in result.error
```
