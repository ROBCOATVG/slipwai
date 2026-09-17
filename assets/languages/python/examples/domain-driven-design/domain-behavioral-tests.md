```python
# Behavioral — tests a business rule
def test_event_with_a_past_date_is_considered_past() -> None:
    now = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)
    assert is_past_event(datetime(2026, 3, 19, 12, 0, tzinfo=timezone.utc), now) is True
    assert is_past_event(datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc), now) is False


# Behavioral — tests a business calculation
def test_committed_total_includes_only_non_idea_items() -> None:
    items = [
        get_test_item(status="committed", price_pence=5000),
        get_test_item(status="idea", price_pence=3000),
    ]
    assert calculate_committed_total(items) == 5000
```
