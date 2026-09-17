```python
def test_validates_payment():
    result = validate(get_mock_payment())
    assert result.success is True  # Only happy path!


# Missing: negative amounts, invalid CVV, missing fields, etc.
```
