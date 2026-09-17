```python
from unittest.mock import patch


# ❌ Testing HOW (implementation detail)
def test_calls_validate_amount():
    with patch.object(validator, "validate_amount") as mock_validate_amount:
        process_payment(payment)
        mock_validate_amount.assert_called()  # Tests HOW, not WHAT


# ❌ Testing private methods
def test_validates_cvv_format():
    result = validator._validate_cvv("123")  # Private method!
    assert result is True


# ❌ Testing internal state
def test_sets_validated_flag():
    process_payment(payment)
    assert processor._is_validated is True  # Internal state
```
