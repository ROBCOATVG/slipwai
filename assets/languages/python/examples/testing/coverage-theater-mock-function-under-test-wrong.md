```python
from unittest.mock import patch


def test_calls_validator():
    with patch.object(validator, "validate") as mock_validate:
        validator.validate(payment)
        mock_validate.assert_called()  # Meaningless assertion
```
