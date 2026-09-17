```python
# gifting/hexagon/domain/pledge_rules_test.py
from __future__ import annotations

from dataclasses import replace

from gifting.hexagon.domain.pledge import PledgeRequest, record_pledge
from gifting.hexagon.domain.types import ContributorId, Money, Occasion, OccasionId, PledgeId


def make_test_occasion(**overrides: object) -> Occasion:
    defaults = Occasion(
        id=OccasionId("occasion-1"),
        name="Alex's birthday",
        budget=Money(minor_units=10_000, currency="GBP"),
        total_pledged=Money(minor_units=0, currency="GBP"),
        is_funding_closed=False,
    )
    return replace(defaults, **overrides)


def test_adds_the_exact_amount_and_records_what_happened():
    occasion = make_test_occasion(total_pledged=Money(minor_units=5_000, currency="GBP"))

    result = record_pledge(
        occasion,
        PledgeRequest(
            id=PledgeId("pledge-1"),
            contributor_id=ContributorId("contributor-1"),
            amount=Money(minor_units=3_000, currency="GBP"),
        ),
    )

    assert result.success
    assert result.occasion.total_pledged == Money(minor_units=8_000, currency="GBP")
    assert len(result.events) == 1
    assert result.events[0].amount == Money(minor_units=3_000, currency="GBP")
```
