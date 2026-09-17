```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DepositMoney:
    amount: Money
    at: datetime  # decide stays a pure function of its arguments — never reads the clock internally
```
