```python
# gifting/hexagon/application/pledge_contribution_test.py
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from gifting.hexagon.application.pledge_to_occasion import (
    PledgingToOccasions,
    handle_pledge_recorded,
)
from gifting.hexagon.application.pledging import AuthenticatedPledger, PledgeToOccasionCommand
from gifting.hexagon.domain.types import (
    ContributorId,
    Money,
    Occasion,
    OccasionId,
    PledgeId,
    PledgeRecorded,
)
from gifting.testing.fakes.fake_pledge_persistence import FakePledgePersistence
from gifting.testing.fakes.fake_pledge_projection import FakePledgeProjection


def make_test_occasion(**overrides: object) -> Occasion:
    defaults = Occasion(
        id=OccasionId("occasion-1"),
        name="Alex's birthday",
        budget=Money(minor_units=10_000, currency="GBP"),
        total_pledged=Money(minor_units=0, currency="GBP"),
        is_funding_closed=False,
    )
    return replace(defaults, **overrides)


TEST_PLEDGE_ID = PledgeId("pledge-1")
TEST_CONTRIBUTOR_ID = ContributorId("contributor-1")
TEST_PRINCIPAL = AuthenticatedPledger(contributor_id=TEST_CONTRIBUTOR_ID)


@pytest.mark.asyncio
async def test_updates_one_aggregate_and_records_its_outbox_event():
    occasion = make_test_occasion()
    persistence = FakePledgePersistence([occasion])
    pledging = PledgingToOccasions(persistence=persistence)

    result = await pledging.pledge_to_occasion(
        PledgeToOccasionCommand(
            pledge_id=TEST_PLEDGE_ID,
            occasion_id=occasion.id,
            principal=TEST_PRINCIPAL,
            amount=Money(minor_units=2_500, currency="GBP"),
        )
    )

    assert result.success
    assert result.occasion.total_pledged == Money(minor_units=2_500, currency="GBP")
    assert len(persistence.saved_entities) == 1
    assert persistence.outbox_events == [
        PledgeRecorded(
            id=TEST_PLEDGE_ID,
            occasion_id=occasion.id,
            contributor_id=TEST_CONTRIBUTOR_ID,
            amount=Money(minor_units=2_500, currency="GBP"),
        )
    ]


@pytest.mark.parametrize(
    ("occasion", "amount", "expected_reason"),
    [
        pytest.param(
            make_test_occasion(
                budget=Money(minor_units=10_000, currency="GBP"),
                total_pledged=Money(minor_units=9_000, currency="GBP"),
            ),
            Money(minor_units=2_500, currency="GBP"),
            "exceeds-budget",
            id="exceeds-budget",
        ),
        pytest.param(
            make_test_occasion(),
            Money(minor_units=2_500, currency="USD"),
            "currency-mismatch",
            id="currency-mismatch",
        ),
        pytest.param(
            make_test_occasion(is_funding_closed=True),
            Money(minor_units=2_500, currency="GBP"),
            "funding-closed",
            id="funding-closed",
        ),
    ],
)
@pytest.mark.asyncio
async def test_rejects_an_invalid_pledge(occasion, amount, expected_reason):
    persistence = FakePledgePersistence([occasion])
    pledging = PledgingToOccasions(persistence=persistence)

    result = await pledging.pledge_to_occasion(
        PledgeToOccasionCommand(
            pledge_id=TEST_PLEDGE_ID,
            occasion_id=occasion.id,
            principal=TEST_PRINCIPAL,
            amount=amount,
        )
    )

    assert not result.success
    assert result.reason == expected_reason
    assert persistence.saved_entities == []
    assert persistence.outbox_events == []


@pytest.mark.asyncio
async def test_rejects_one_of_two_concurrent_writes_from_the_same_version():
    occasion = make_test_occasion()
    persistence = FakePledgePersistence([occasion])
    pledging = PledgingToOccasions(persistence=persistence)

    results = await asyncio.gather(
        pledging.pledge_to_occasion(
            PledgeToOccasionCommand(
                pledge_id=PledgeId("pledge-1"),
                occasion_id=occasion.id,
                principal=TEST_PRINCIPAL,
                amount=Money(minor_units=2_500, currency="GBP"),
            )
        ),
        pledging.pledge_to_occasion(
            PledgeToOccasionCommand(
                pledge_id=PledgeId("pledge-2"),
                occasion_id=occasion.id,
                principal=TEST_PRINCIPAL,
                amount=Money(minor_units=3_000, currency="GBP"),
            )
        ),
    )

    successes = [result for result in results if result.success]
    failures = [result for result in results if not result.success]
    assert len(successes) == 1
    assert [failure.reason for failure in failures] == ["concurrent-change"]
    assert len(persistence.saved_entities) == 1
    assert len(persistence.outbox_events) == 1


@pytest.mark.asyncio
async def test_handles_a_redelivered_pledge_recorded_event_once():
    projection = FakePledgeProjection()
    event = PledgeRecorded(
        id=TEST_PLEDGE_ID,
        occasion_id=OccasionId("occasion-1"),
        contributor_id=TEST_CONTRIBUTOR_ID,
        amount=Money(minor_units=2_500, currency="GBP"),
    )

    await handle_pledge_recorded(projection, event)
    await handle_pledge_recorded(projection, event)

    assert projection.records == [event]
```
