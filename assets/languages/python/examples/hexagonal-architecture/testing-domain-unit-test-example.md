```python
def test_rejects_contribution_exceeding_available_balance() -> None:
    occasion = make_occasion()
    poor_contributor = make_contributor(available_balance=make_money(500, "GBP"))
    large_pledge = make_pledge(amount=make_money(5_000, "GBP"))

    result = pledge_contribution(occasion, poor_contributor, large_pledge)

    assert result.success is False
```
