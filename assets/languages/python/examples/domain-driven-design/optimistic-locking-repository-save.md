```python
from typing import Literal, Protocol

SaveOutcome = Literal["saved", "conflict"]


class OccasionRepository(Protocol):
    async def save(self, occasion: "Occasion") -> SaveOutcome: ...


async def save(session: "AsyncSession", occasion: "Occasion") -> SaveOutcome:
    """Compare-and-swap on the version field: the WHERE clause only matches
    the row if nobody else has saved a newer version in the meantime."""
    result = await session.execute(
        update(occasions_table)
        .where(
            occasions_table.c.id == occasion.id,
            occasions_table.c.version == occasion.version,
        )
        .values(**to_row(occasion), version=occasion.version + 1)
    )
    return "saved" if result.rowcount == 1 else "conflict"
```
