```python
def test_processes_payment_and_returns_transaction_id():
    payment = get_mock_payment()
    result = handle_payment(payment)
    assert result.success is True
    assert isinstance(result.transaction_id, str)
```
