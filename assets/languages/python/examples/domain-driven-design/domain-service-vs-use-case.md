```python
from dataclasses import dataclass, replace
from typing import Literal, Protocol

MAX_SAFE_INTEGER = 2**53 - 1


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
    type: Literal["PledgeRecorded"] = "PledgeRecorded"


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
PledgeResult = PledgeDecision  # the use case surfaces the same shape, plus its own reasons


@dataclass(frozen=True)
class Pledge:
    id: PledgeId
    amount: Money


# DOMAIN SERVICE — contains business logic, operates on domain types.
# Colocate with the domain concepts it serves under the chosen physical structure.
def pledge_contribution(
    occasion: Occasion,
    eligibility: ContributorEligibility,
    pledge: Pledge,
) -> PledgeDecision:
    if not eligibility.may_pledge:
        return PledgeRejected(reason="contributor-ineligible")
    if occasion.is_funding_closed:
        return PledgeRejected(reason="funding-closed")
    if (
        pledge.amount.currency != occasion.total_pledged.currency
        or occasion.total_pledged.currency != occasion.budget.currency
    ):
        return PledgeRejected(reason="currency-mismatch")

    values = (
        occasion.total_pledged.minor_units,
        occasion.budget.minor_units,
        pledge.amount.minor_units,
    )
    if any(abs(value) > MAX_SAFE_INTEGER for value in values):
        raise ValueError("Invalid Money invariant")
    if pledge.amount.minor_units <= 0:
        return PledgeRejected(reason="non-positive-amount")
    if occasion.total_pledged.minor_units > occasion.budget.minor_units:
        raise ValueError("Invalid Occasion funding invariant")
    if pledge.amount.minor_units > occasion.budget.minor_units - occasion.total_pledged.minor_units:
        return PledgeRejected(reason="exceeds-budget")

    total_pledged = occasion.total_pledged.minor_units + pledge.amount.minor_units
    if abs(total_pledged) > MAX_SAFE_INTEGER:
        raise ValueError("Money addition overflowed")

    return PledgeAccepted(
        occasion=replace(
            occasion,
            total_pledged=create_money(total_pledged, pledge.amount.currency),
        ),
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


# USE CASE — application orchestration only, no business rules.
# Place as application policy; never assume it belongs in a domain/ package.
async def handle_pledge(
    persistence: PledgePersistence,
    eligibility_gateway: ContributorEligibilityGateway,
    dto: PledgeDto,
) -> PledgeResult:
    stored = await persistence.find_occasion_by_id(dto.occasion_id)
    eligibility = await eligibility_gateway.find_for(dto.contributor_id)
    if stored is None or eligibility is None:
        return PledgeRejected(reason="not-found")

    result = pledge_contribution(
        stored.value,
        eligibility,
        Pledge(id=dto.pledge_id, amount=dto.amount),
    )
    if isinstance(result, PledgeAccepted):
        saved = await persistence.save_with_outbox(result.occasion, result.events, stored.version)
        if saved == "conflict":
            return PledgeRejected(reason="concurrent-change")
    return result
```
