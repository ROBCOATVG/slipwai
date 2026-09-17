```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PledgeRecorded:
    occasion: "Occasion"
    events: tuple["PledgeRecordedEvent", ...]


@dataclass(frozen=True)
class PledgeRejected:
    reason: str


@dataclass(frozen=True)
class PledgeNotFound:
    reason: str = "not-found"


@dataclass(frozen=True)
class PledgeConflict:
    reason: str = "concurrent-change"


PledgeResult = PledgeRecorded | PledgeRejected | PledgeNotFound | PledgeConflict


class OccasionRepository(Protocol):
    async def find_by_id(self, occasion_id: "OccasionId") -> "StoredOccasion | None": ...
    async def save_with_outbox(
        self,
        occasion: "Occasion",
        events: tuple["PledgeRecordedEvent", ...],
        expected_version: int,
    ) -> "SaveOutcome": ...


class ContributorRepository(Protocol):
    async def apply_pledge_once(
        self, pledge_id: "PledgeId", contributor_id: "ContributorId", amount: "Money"
    ) -> None: ...


# One transaction saves one aggregate and its outbox event.
async def handle_pledge(occasion_repo: OccasionRepository, dto: "PledgeDto") -> PledgeResult:
    stored = await occasion_repo.find_by_id(dto.occasion_id)
    if stored is None:
        return PledgeNotFound()

    result = record_pledge(stored.value, dto)
    if not isinstance(result, PledgeRecorded):
        return result

    saved = await occasion_repo.save_with_outbox(result.occasion, result.events, stored.version)
    if saved == "conflict":
        return PledgeConflict()

    return result


# A separate, idempotent handler converges the other aggregate.
async def handle_pledge_recorded(
    contributor_repo: ContributorRepository, event: "PledgeRecordedEvent"
) -> None:
    await contributor_repo.apply_pledge_once(event.id, event.contributor_id, event.amount)
```
