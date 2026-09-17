```python
class RecordingPledgeInstrumentation:
    """Recording fake for the PledgeInstrumentation port — appends an
    observation per call so use-case tests can assert on them like any
    other behavior."""

    def __init__(self) -> None:
        self.observed: list[dict[str, object]] = []

    def pledge_rejected(self, reason: PledgeRejectionReason, occasion_id: OccasionId) -> None:
        self.observed.append({"kind": "pledge-rejected", "reason": reason, "occasion_id": occasion_id})

    def pledge_accepted(self, amount: Money, occasion_id: OccasionId) -> None:
        self.observed.append({"kind": "pledge-accepted", "amount": amount, "occasion_id": occasion_id})


@pytest.fixture
def closed_occasion() -> Occasion:
    return make_occasion(is_funding_closed=True)


def test_announces_the_rejection_when_funding_is_closed(closed_occasion: Occasion) -> None:
    instrumentation = RecordingPledgeInstrumentation()
    pledging = PledgingToOccasions(
        FakeOccasionRepository(occasions=[closed_occasion]),
        FakeContributorRepository(),
        instrumentation,
    )

    pledging.pledge_to_occasion(make_pledge(occasion_id=closed_occasion.id))

    assert {
        "kind": "pledge-rejected",
        "reason": "funding-closed",
        "occasion_id": closed_occasion.id,
    } in instrumentation.observed
```
