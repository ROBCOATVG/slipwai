```python
from dataclasses import dataclass
from typing import Literal

Currency = Literal["GBP", "USD", "EUR"]

# Mirrors JavaScript's Number.MAX_SAFE_INTEGER so the same class of
# overflow bug is caught explicitly, rather than relying on Python's
# arbitrary-precision ints to silently paper over it.
_MAX_SAFE_INTEGER = 2**53 - 1


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.minor_units, int) or abs(self.minor_units) > _MAX_SAFE_INTEGER:
            raise ValueError("Money minor units must be a safe integer")
        if self.minor_units < 0:
            raise ValueError("Money cannot be negative")


# __post_init__ raising = an invariant violation (a bug in calling code).
# Validation of untrusted input happens at trust boundaries BEFORE a Money
# is ever constructed. If __post_init__ raises, something bypassed that
# boundary check.
```
