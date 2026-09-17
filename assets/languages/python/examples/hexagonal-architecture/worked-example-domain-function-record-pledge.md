```python
# gifting/hexagon/domain/pledge.py — aggregate operation, pure function
from __future__ import annotations

from dataclasses import dataclass, replace

from gifting.hexagon.domain.types import (
    ContributorId,
    Money,
    Occasion,
    PledgeAccepted,
    PledgeDecision,
    PledgeId,
    PledgeRecorded,
    PledgeRejected,
    make_money,
)


@dataclass(frozen=True)
class PledgeRequest:
    id: PledgeId
    contributor_id: ContributorId
    amount: Money


def record_pledge(occasion: Occasion, pledge: PledgeRequest) -> PledgeDecision:
    if occasion.is_funding_closed:
        return PledgeRejected(reason="funding-closed")

    if (
        pledge.amount.currency != occasion.total_pledged.currency
        or occasion.total_pledged.currency != occasion.budget.currency
    ):
        return PledgeRejected(reason="currency-mismatch")

    if (
        occasion.total_pledged.minor_units < 0
        or occasion.budget.minor_units < 0
        or pledge.amount.minor_units < 0
    ):
        raise ValueError("invalid Money invariant: minor_units must not be negative")

    if pledge.amount.minor_units <= 0:
        return PledgeRejected(reason="non-positive-amount")

    if occasion.total_pledged.minor_units > occasion.budget.minor_units:
        raise ValueError("invalid Occasion invariant: total pledged exceeds budget")

    remaining = occasion.budget.minor_units - occasion.total_pledged.minor_units
    if pledge.amount.minor_units > remaining:
        return PledgeRejected(reason="exceeds-budget")

    updated_occasion = replace(
        occasion,
        total_pledged=make_money(
            occasion.total_pledged.minor_units + pledge.amount.minor_units,
            occasion.total_pledged.currency,
        ),
    )

    event = PledgeRecorded(
        id=pledge.id,
        occasion_id=occasion.id,
        contributor_id=pledge.contributor_id,
        amount=pledge.amount,
    )

    return PledgeAccepted(occasion=updated_occasion, events=(event,))
```
