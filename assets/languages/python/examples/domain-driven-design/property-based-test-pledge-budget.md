```python
from hypothesis import given
from hypothesis import strategies as st


@given(
    already_pledged=st.integers(min_value=0, max_value=10_000),
    pledge=st.integers(min_value=1, max_value=10_000),
)
def test_a_successful_pledge_never_exceeds_the_occasion_budget(
    already_pledged: int, pledge: int
) -> None:
    occasion = get_test_occasion(
        budget=create_money(10_000, "GBP"),
        total_pledged=create_money(already_pledged, "GBP"),
    )
    eligibility = get_test_contributor_eligibility(may_pledge=True)

    result = pledge_contribution(
        occasion,
        eligibility,
        PledgeRequest(id=create_pledge_id("pledge-1"), amount=create_money(pledge, "GBP")),
    )

    if isinstance(result, PledgeAccepted):
        assert result.occasion.total_pledged.minor_units <= result.occasion.budget.minor_units
    # rejected pledges are always valid — nothing further to assert
```
