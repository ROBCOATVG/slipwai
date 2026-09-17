```python
from typing import NewType

OccasionId = NewType("OccasionId", str)
GiftIdeaId = NewType("GiftIdeaId", str)


def create_occasion_id(raw: str) -> OccasionId:
    if not raw.strip():
        raise ValueError("OccasionId cannot be empty")
    return OccasionId(raw)


def create_gift_idea_id(raw: str) -> GiftIdeaId:
    if not raw.strip():
        raise ValueError("GiftIdeaId cannot be empty")
    return GiftIdeaId(raw)


# NewType erases to `str` at runtime, exactly like the branded type it
# replaces -- the distinction only exists for the type checker. A
# GiftIdeaId can never be passed where an OccasionId is expected without
# mypy flagging it, even though both are plain strings underneath.
```
