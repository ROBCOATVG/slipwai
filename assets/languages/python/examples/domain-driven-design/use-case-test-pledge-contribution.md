```python
from dataclasses import dataclass, replace
from typing import Literal, Protocol

import pytest


@dataclass(frozen=True)
class OccasionId:
    value: str


@dataclass(frozen=True)
class PledgeId:
    value: str


@dataclass(frozen=True)
class ContributorId:
    value: str


@dataclass(frozen=True)
class Money:
    minor_units: int
    currency: str


def create_money(minor_units: int, currency: str) -> Money:
    return Money(minor_units, currency)


def create_pledge_id(value: str) -> PledgeId:
    return PledgeId(value)


@dataclass(frozen=True)
class Occasion:
    id: OccasionId
    is_funding_closed: bool
    total_pledged: Money
    budget: Money


@dataclass(frozen=True)
class ContributorEligibility:
    contributor_id: ContributorId
    may_pledge: bool


@dataclass(frozen=True)
class PledgeRecorded:
    id: PledgeId
    occasion_id: OccasionId
    contributor_id: ContributorId
    amount: Money


@dataclass(frozen=True)
class PledgeAccepted:
    occasion: Occasion
    events: tuple[PledgeRecorded, ...]
    success: Literal[True] = True


@dataclass(frozen=True)
class PledgeRejected:
    reason: str
    success: Literal[False] = False


PledgeDecision = PledgeAccepted | PledgeRejected


@dataclass(frozen=True)
class Pledge:
    id: PledgeId
    amount: Money


def pledge_contribution(
    occasion: Occasion,
    eligibility: ContributorEligibility,
    pledge: Pledge,
) -> PledgeDecision:
    if not eligibility.may_pledge:
        return PledgeRejected(reason="contributor-ineligible")
    if occasion.is_funding_closed:
        return PledgeRejected(reason="funding-closed")
    if pledge.amount.minor_units > occasion.budget.minor_units - occasion.total_pledged.minor_units:
        return PledgeRejected(reason="exceeds-budget")
    total_pledged = occasion.total_pledged.minor_units + pledge.amount.minor_units
    return PledgeAccepted(
        occasion=replace(occasion, total_pledged=create_money(total_pledged, pledge.amount.currency)),
        events=(
            PledgeRecorded(
                id=pledge.id,
                occasion_id=occasion.id,
                contributor_id=eligibility.contributor_id,
                amount=pledge.amount,
            ),
        ),
    )


@dataclass(frozen=True)
class StoredOccasion:
    value: Occasion
    version: int


class PledgePersistence(Protocol):
    async def find_occasion_by_id(self, occasion_id: OccasionId) -> StoredOccasion | None: ...

    async def save_with_outbox(
        self,
        occasion: Occasion,
        events: tuple[PledgeRecorded, ...],
        expected_version: int,
    ) -> Literal["saved", "conflict"]: ...


class ContributorEligibilityGateway(Protocol):
    async def find_for(self, contributor_id: ContributorId) -> ContributorEligibility | None: ...


@dataclass(frozen=True)
class PledgeDto:
    pledge_id: PledgeId
    occasion_id: OccasionId
    contributor_id: ContributorId
    amount: Money


async def handle_pledge(
    persistence: PledgePersistence,
    eligibility_gateway: ContributorEligibilityGateway,
    dto: PledgeDto,
) -> PledgeDecision:
    stored = await persistence.find_occasion_by_id(dto.occasion_id)
    eligibility = await eligibility_gateway.find_for(dto.contributor_id)
    if stored is None or eligibility is None:
        return PledgeRejected(reason="not-found")

    result = pledge_contribution(stored.value, eligibility, Pledge(id=dto.pledge_id, amount=dto.amount))
    if isinstance(result, PledgeAccepted):
        saved = await persistence.save_with_outbox(result.occasion, result.events, stored.version)
        if saved == "conflict":
            return PledgeRejected(reason="concurrent-change")
    return result


# --- in-memory fakes for the use-case test ---


class FakePledgePersistence:
    def __init__(self, occasions: list[Occasion]) -> None:
        self._occasions = {occasion.id: occasion for occasion in occasions}
        self.saved_entities: list[Occasion] = []
        self.outbox_events: list[PledgeRecorded] = []

    async def find_occasion_by_id(self, occasion_id: OccasionId) -> StoredOccasion | None:
        occasion = self._occasions.get(occasion_id)
        return None if occasion is None else StoredOccasion(value=occasion, version=1)

    async def save_with_outbox(
        self,
        occasion: Occasion,
        events: tuple[PledgeRecorded, ...],
        expected_version: int,
    ) -> Literal["saved", "conflict"]:
        self._occasions[occasion.id] = occasion
        self.saved_entities.append(occasion)
        self.outbox_events.extend(events)
        return "saved"


class FakeContributorEligibilityGateway:
    def __init__(self, entries: list[ContributorEligibility]) -> None:
        self._entries = {entry.contributor_id: entry for entry in entries}

    async def find_for(self, contributor_id: ContributorId) -> ContributorEligibility | None:
        return self._entries.get(contributor_id)


test_occasion = Occasion(
    id=OccasionId("occasion-1"),
    is_funding_closed=False,
    total_pledged=create_money(0, "GBP"),
    budget=create_money(50_000, "GBP"),
)
test_contributor = ContributorId("contributor-1")


@pytest.mark.asyncio
async def test_handle_pledge_rejects_a_pledge_from_an_ineligible_contributor() -> None:
    persistence = FakePledgePersistence([test_occasion])
    eligibility_gateway = FakeContributorEligibilityGateway(
        [ContributorEligibility(contributor_id=test_contributor, may_pledge=False)],
    )

    result = await handle_pledge(
        persistence,
        eligibility_gateway,
        PledgeDto(
            pledge_id=create_pledge_id("pledge-1"),
            occasion_id=test_occasion.id,
            contributor_id=test_contributor,
            amount=create_money(5_000, "GBP"),
        ),
    )

    assert result == PledgeRejected(reason="contributor-ineligible")
    assert persistence.saved_entities == []
    assert persistence.outbox_events == []
```
