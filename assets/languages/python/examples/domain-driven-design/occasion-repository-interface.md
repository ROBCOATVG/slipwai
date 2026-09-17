```python
from dataclasses import dataclass
from typing import NewType, Protocol

OccasionId = NewType("OccasionId", str)


@dataclass(frozen=True)
class Occasion:
    id: OccasionId
    name: str


# Application-owned repository contract -- an inside-owned port when
# hexagonal architecture is used. Protocol gives structural typing: any
# object with matching methods satisfies this without inheriting from it.
class OccasionRepository(Protocol):
    async def find_by_id(self, occasion_id: OccasionId) -> Occasion | None: ...

    async def save(self, occasion: Occasion) -> None: ...


# Concrete implementations belong with infrastructure/integration; in
# hexagonal architecture they are driven adapters.
```
