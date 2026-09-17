```python
# gifting/hexagon/application/pledge_to_occasion.py — use case
from __future__ import annotations

from dataclasses import dataclass

from gifting.hexagon.application.pledging import (
    PledgeNotFoundOrConflict,
    PledgePersistence,
    PledgeProjection,
    PledgeResult,
    PledgeToOccasionCommand,
)
from gifting.hexagon.domain.pledge import PledgeRequest, record_pledge
from gifting.hexagon.domain.types import PledgeRecorded


@dataclass(frozen=True)
class PledgingToOccasions:
    """Implements ForPledgingToOccasions by wiring PledgePersistence to the
    record_pledge aggregate operation. Structural typing (Protocol) means
    this class satisfies the port without declaring it explicitly."""

    persistence: PledgePersistence

    async def pledge_to_occasion(self, command: PledgeToOccasionCommand) -> PledgeResult:
        stored = await self.persistence.find_occasion_by_id(command.occasion_id)
        if stored is None:
            return PledgeNotFoundOrConflict(reason="not-found")

        decision = record_pledge(
            stored.value,
            PledgeRequest(
                id=command.pledge_id,
                contributor_id=command.principal.contributor_id,
                amount=command.amount,
            ),
        )
        if decision.success:
            outcome = await self.persistence.save_with_outbox(
                decision.occasion, decision.events, stored.version
            )
            if outcome == "conflict":
                return PledgeNotFoundOrConflict(reason="concurrent-change")
        return decision


# gifting/hexagon/application/pledge_recorded_handler.py
async def handle_pledge_recorded(projection: PledgeProjection, event: PledgeRecorded) -> None:
    """Idempotent event handler: the outbox worker retries delivery, so this
    must stay safe even if the same PledgeRecorded event arrives twice."""
    await projection.record_from(event)
```
