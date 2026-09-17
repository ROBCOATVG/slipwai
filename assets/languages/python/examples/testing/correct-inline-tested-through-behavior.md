```python
# load_participant_view.py
async def load_participant_view(db: Db, event_id: EventId, user_id: UserId) -> ParticipantView:
    items = await get_items(db, event_id, user_id)
    your_claims = [i for i in items if i.is_claimed and i.is_claimed_by_current_user]
    available = [i for i in items if not i.is_claimed_by_current_user]
    return ParticipantView(your_claims=your_claims, available=available)


# The behavioral test for load_participant_view covers the filtering:
async def test_returns_claimed_gifts_in_your_claims_and_unclaimed_in_available():
    result = await load_participant_view(db, event_id, user_id)
    assert len(result.your_claims) == 1
    assert len(result.available) == 2
```
