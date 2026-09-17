```python
from dataclasses import dataclass
from datetime import datetime

URGENT_WITHIN_DAYS = 30


@dataclass(frozen=True)
class DashboardCard:
    """Display-ready DTO for the dashboard view."""

    title: str
    emoji: str
    days_away: int
    savings: "SavingsDisplay"
    is_urgent: bool


def to_dashboard_card(row: "DashboardRow", now: datetime) -> DashboardCard:
    """Pure, provider-free policy: no ports, no I/O.

    ``is_urgent`` is a genuine business rule — a threshold on days until the
    event — so it belongs in the hexagon. Cosmetic formatting is out of
    scope here; that is left to the driving/UI edge.
    """
    days_away = (row.event_date - now.date()).days
    return DashboardCard(
        title=row.event_title,
        emoji=row.occasion_emoji,
        days_away=days_away,
        savings=build_savings_display(row.saved_amount, row.target_amount, now),
        is_urgent=days_away < URGENT_WITHIN_DAYS,
    )
```
