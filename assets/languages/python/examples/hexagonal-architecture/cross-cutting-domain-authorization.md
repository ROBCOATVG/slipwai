```python
from dataclasses import replace


def close_funding(occasion: "Occasion", requester_id: "ContributorId") -> "CloseResult":
    """Domain: "only the organizer can close funding" is a business rule."""
    if occasion.organizer_id != requester_id:
        return NotOrganizer()
    return FundingClosed(occasion=replace(occasion, is_funding_closed=True))
```
