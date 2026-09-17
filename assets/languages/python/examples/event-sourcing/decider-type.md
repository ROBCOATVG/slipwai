```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

State = TypeVar("State")
Command = TypeVar("Command")
Event = TypeVar("Event")


@dataclass(frozen=True, slots=True)
class Decider(Generic[State, Command, Event]):
    initial_state: State
    decide: Callable[[Command, State], Decision[Event]]
    evolve: Callable[[State, Event], State]
    is_terminal: Optional[Callable[[State], bool]] = None
```
