```python
from dataclasses import dataclass


@dataclass(frozen=True)
class PledgingToOccasions:
    """Application/use case: receives identity and coordinates domain behaviour.

    Application code doesn't check JWT tokens or session cookies. It
    authorizes an already-authenticated, provider-free principal and
    invokes domain rules.
    """

    persistence: "PledgePersistence"

    async def pledge_to_occasion(self, command: "PledgeToOccasionCommand") -> "PledgeResult":
        stored = await self.persistence.find_occasion_by_id(command.occasion_id)
        if stored is None:
            return PledgeNotFoundOrConflict(reason="not-found")
        ...  # delegate to the domain function and save the outcome
```
