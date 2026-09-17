```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Occasion:
    id: "OccasionId"
    version: int  # incremented on each save
    name: str
    budget: "Money"
    gift_ideas: tuple["GiftIdea", ...]
```
