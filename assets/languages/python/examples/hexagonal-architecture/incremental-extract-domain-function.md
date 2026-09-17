```python
# billing/hexagon/domain/deduct_balance.py — extracted pure function
from dataclasses import dataclass, replace
from typing import Literal, Union

DeductFailureReason = Literal["non-positive-amount", "currency-mismatch", "insufficient-balance"]


@dataclass(frozen=True)
class DeductSuccess:
    user: "User"


@dataclass(frozen=True)
class DeductFailure:
    reason: DeductFailureReason


DeductResult = Union[DeductSuccess, DeductFailure]


def deduct_balance(user: "User", amount: "Money") -> DeductResult:
    """Pure domain rule — no I/O, no exceptions for expected business outcomes."""
    if amount.minor_units <= 0:
        return DeductFailure(reason="non-positive-amount")
    if amount.currency != user.balance.currency:
        return DeductFailure(reason="currency-mismatch")
    if amount.minor_units > user.balance.minor_units:
        return DeductFailure(reason="insufficient-balance")

    new_balance = Money(
        minor_units=user.balance.minor_units - amount.minor_units,
        currency=user.balance.currency,
    )
    return DeductSuccess(user=replace(user, balance=new_balance))
```
