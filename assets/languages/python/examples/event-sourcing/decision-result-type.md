```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, Union

E = TypeVar("E")
R = TypeVar("R", bound=str)


@dataclass(frozen=True, slots=True)
class Accepted(Generic[E]):
    events: tuple[E, ...]


@dataclass(frozen=True, slots=True)
class Rejected(Generic[R]):
    reason: R


Decision = Union[Accepted[E], Rejected[R]]


def accept(events: tuple[E, ...]) -> Accepted[E]:
    return Accepted(events)


def reject(reason: R) -> Rejected[R]:
    return Rejected(reason)
```
