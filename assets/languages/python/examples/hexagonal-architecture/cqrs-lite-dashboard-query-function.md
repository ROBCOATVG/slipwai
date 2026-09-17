```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardRow:
    """Flat, read-optimized shape for the dashboard view."""

    event_title: str
    occasion_emoji: str
    event_date: "date"
    saved_amount: int | None
    target_amount: int
    recipient_name: str


async def get_dashboard_cards(db: "Connection", user_id: str) -> list[DashboardRow]:
    """Driven adapter query (not a repository) — joins across several
    aggregates for a read-only dashboard view.

    Deliberately bypasses the aggregate-per-repository pattern because this
    is a display read, not a write.
    """
    rows = await db.fetch(
        """
        SELECT
            events.title                 AS event_title,
            occasions.emoji              AS occasion_emoji,
            events.event_date            AS event_date,
            savings_goals.saved_amount   AS saved_amount,
            savings_goals.target_amount  AS target_amount,
            recipients.name              AS recipient_name
        FROM events
        INNER JOIN occasions    ON occasions.id = events.occasion_id
        LEFT JOIN savings_goals ON savings_goals.event_id = events.id
        INNER JOIN recipients   ON recipients.id = events.recipient_id
        WHERE events.user_id = $1
        """,
        user_id,
    )
    return [DashboardRow(**row) for row in rows]
```
