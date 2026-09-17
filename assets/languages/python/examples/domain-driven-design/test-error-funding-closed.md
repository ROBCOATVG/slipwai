```python
import pytest


@pytest.mark.asyncio
async def test_rejects_pledge_when_funding_is_closed():
    closed_occasion = get_test_occasion(is_funding_closed=True)
    occasion_repo = create_fake_occasion_repository([closed_occasion])
    contributor_repo = create_fake_contributor_repository([test_contributor])

    result = await handle_pledge(
        occasion_repo,
        contributor_repo,
        PledgeDto(
            occasion_id=closed_occasion.id,
            contributor_id=test_contributor.id,
            amount=create_money(2_500, "GBP"),
        ),
    )

    assert result == PledgeRejected(reason="funding-closed")
    assert occasion_repo.saved_entities == []
```
