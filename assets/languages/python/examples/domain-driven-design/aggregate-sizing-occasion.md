```python
from dataclasses import dataclass


# WRONG — too large: User doesn't need to be in the Occasion aggregate.
@dataclass(frozen=True)
class Occasion:
    organizer: "User"                  # Embedded user — wrong!
    contributors: tuple["User", ...]   # Embedded users — wrong!
    gift_ideas: tuple["GiftIdea", ...]


# RIGHT — only what's needed for consistency.
@dataclass(frozen=True)
class Occasion:
    organizer_id: "UserId"              # Reference by ID
    gift_ideas: tuple["GiftIdea", ...]  # Owned — needed for the budget invariant
    budget: "Money"                     # Owned — needed for the budget invariant
```
