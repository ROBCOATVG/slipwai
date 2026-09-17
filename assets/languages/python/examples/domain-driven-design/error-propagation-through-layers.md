```python
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PledgeAccepted:
    occasion: "Occasion"
    events: tuple["PledgeRecorded", ...]


@dataclass(frozen=True)
class PledgeRejected:
    reason: Literal["funding-closed"]


PledgeDecision = PledgeAccepted | PledgeRejected


# Domain: returns a result with the business reason.
def pledge_contribution(
    occasion: "Occasion", eligibility: "Eligibility", pledge: "NewPledge"
) -> PledgeDecision:
    if occasion.is_funding_closed:
        return PledgeRejected(reason="funding-closed")
    ...


@dataclass(frozen=True)
class PledgeNotFound:
    reason: Literal["not-found"] = "not-found"


@dataclass(frozen=True)
class PledgeConcurrentChange:
    reason: Literal["concurrent-change"] = "concurrent-change"


PledgeResult = PledgeDecision | PledgeNotFound | PledgeConcurrentChange


# Use case: propagates the domain result, controls the save.
async def handle_pledge(repos: "Repos", dto: "PledgeDto") -> PledgeResult:
    stored = await repos.occasion.find_by_id(dto.occasion_id)
    eligibility = await repos.eligibility.find_for(dto.contributor_id)
    if stored is None or eligibility is None:
        return PledgeNotFound()

    result = pledge_contribution(
        stored.value, eligibility, NewPledge(id=dto.pledge_id, amount=dto.amount)
    )
    if isinstance(result, PledgeAccepted):
        saved = await repos.occasion.save_with_outbox(
            result.occasion, result.events, stored.version
        )
        if saved == "conflict":
            return PledgeConcurrentChange()
    return result


# Delivery layer: translates the result to an HTTP-style status code.
def to_http_response(result: PledgeResult) -> tuple[int, dict]:
    if isinstance(result, PledgeAccepted):
        return 200, {"pledged": result.occasion.total_pledged}
    if isinstance(result, PledgeNotFound):
        return 404, {"error": result.reason}
    if isinstance(result, PledgeConcurrentChange):
        return 409, {"error": result.reason}
    return 422, {"error": result.reason}
```
