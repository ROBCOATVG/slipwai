```python
from functools import reduce
from typing import Iterable

def rehydrate(events: Iterable[AccountEvent]) -> AccountState:
    """Rebuild current state by left-folding `evolve` over past events."""
    return reduce(evolve, events, initial_state)
```
