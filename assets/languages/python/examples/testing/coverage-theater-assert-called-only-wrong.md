```python
from unittest.mock import patch


def test_processes_payment():
    with patch.object(processor, "process") as mock_process:
        handle_payment(payment)
        mock_process.assert_called_with(payment)  # So what?
```
