```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


# WRONG — {"success": False, "error": str} tells you nothing. Use specific
# reason literals instead, so the type checker can help.
@dataclass(frozen=True)
class Ok(Generic[T]):
    data: T


@dataclass(frozen=True)
class Err:
    error: str  # a bare string — no reason literal, no exhaustiveness check


Result = Ok[T] | Err
```
