```python
from dataclasses import dataclass, replace
from typing import Literal


@dataclass(frozen=True)
class Occasion:
    id: "OccasionId"
    name: str
    budget: "Money"
    gift_ideas: tuple["GiftIdea", ...]


def create_occasion(*, id: "OccasionId", name: str, budget: "Money") -> Occasion:
    """Factory enforces invariants on creation (the always-valid principle)."""
    if not name.strip():
        raise ValueError("Occasion name is required")
    if budget.minor_units < 0:
        raise ValueError("Budget minor units must be a non-negative integer")
    return Occasion(id=id, name=name.strip(), budget=budget, gift_ideas=())


# The application/driving edge creates the ID and passes the typed value in.
# Domain creation validates business invariants without a UUID dependency.


@dataclass(frozen=True)
class GiftIdeaAdded:
    occasion: Occasion


@dataclass(frozen=True)
class GiftIdeaRejected:
    reason: Literal["currency-mismatch", "exceeds-budget"]


AddGiftIdeaResult = GiftIdeaAdded | GiftIdeaRejected


def add_gift_idea(occasion: Occasion, idea: "NewGiftIdea") -> AddGiftIdeaResult:
    """State transition enforces invariants; returns a result for business
    outcomes and raises only if the aggregate's own Money invariant has
    already been corrupted (a bug, not a business rule). Unlike the
    JavaScript original, Python's ints have arbitrary precision, so there is
    no equivalent of Number.isSafeInteger overflow checking to replicate.
    """
    if idea.estimated_cost.currency != occasion.budget.currency or any(
        item.estimated_cost.currency != occasion.budget.currency
        for item in occasion.gift_ideas
    ):
        return GiftIdeaRejected(reason="currency-mismatch")

    total_cost = 0
    for item in occasion.gift_ideas:
        if item.estimated_cost.minor_units < 0:
            raise ValueError("Invalid Money invariant")
        total_cost += item.estimated_cost.minor_units

    if idea.estimated_cost.minor_units < 0:
        raise ValueError("Invalid Money invariant")
    if total_cost > occasion.budget.minor_units:
        raise ValueError("Invalid Occasion budget invariant")
    if idea.estimated_cost.minor_units > occasion.budget.minor_units - total_cost:
        return GiftIdeaRejected(reason="exceeds-budget")

    return GiftIdeaAdded(
        occasion=replace(occasion, gift_ideas=occasion.gift_ideas + (idea,))
    )
```
