```python
# prepare_participant_data.py (new module, one caller)
def prepare_participant_data(items: list[Item]) -> ParticipantView:
    return ParticipantView(
        your_claims=[i for i in items if i.is_claimed and i.is_claimed_by_current_user],
        available=[i for i in items if not i.is_claimed_by_current_user],
    )


# test_prepare_participant_data.py (tests the helper directly)
def test_filters_claims(): ...
```
