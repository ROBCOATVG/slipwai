```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ParticipantEventView:
    event_id: str
    event_name: str
    occasion_name: str
    claimed_by: str | None


async def get_participant_event_view(
    session: "AsyncSession", event_id: str
) -> ParticipantEventView | None:
    """Query function — JOINs across aggregates for a read-only display view.

    Lives at reporting/adapters/driven/queries/, outside the hexagon;
    returns a DTO, not a domain aggregate.
    """
    row = (
        await session.execute(
            select(
                events.c.id,
                events.c.name,
                occasions.c.name.label("occasion_name"),
                gift_claims.c.claimed_by,
            )
            .select_from(events)
            .join(occasions, occasions.c.id == events.c.occasion_id)
            .outerjoin(gift_claims, gift_claims.c.event_id == events.c.id)
            .where(events.c.id == event_id)
        )
    ).first()
    return ParticipantEventView(*row) if row is not None else None
```
