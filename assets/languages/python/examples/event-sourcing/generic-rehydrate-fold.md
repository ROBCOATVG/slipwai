```python
from __future__ import annotations

from functools import reduce
from typing import Iterable, TypeVar

State = TypeVar("State")
Command = TypeVar("Command")
Event = TypeVar("Event")


def rehydrate(decider: Decider[State, Command, Event], events: Iterable[Event]) -> State:
    return reduce(decider.evolve, events, decider.initial_state)
```
