```python
from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence


# GiftItem is a minimal stand-in for the sibling type used by
# calculate_committed_total below.
@dataclass(frozen=True)
class GiftItem:
    status: str  # "idea" | "selected" | "purchased"
    price_pence: int


# Pure but NOT domain -- formats for human display.
# Belongs in presentation code; a hexagonal app may place it at the driving edge.
def format_event_date(value: date | None) -> str | None:
    return f"{value:%B} {value.day}, {value.year}" if value else None


# Pure AND domain -- business rule that affects behaviour.
# The application supplies "now" as data; domain code does not read a clock.
# Belongs in domain policy for events.
def is_past_event(event_date: datetime | None, now: datetime) -> bool:
    return event_date < now if event_date else False


# Pure AND domain -- business calculation.
# Belongs in domain policy for budgets.
def calculate_committed_total(items: Sequence[GiftItem]) -> int:
    return sum(item.price_pence for item in items if item.status != "idea")
```
