```python
from __future__ import annotations

from typing import Literal

WithdrawRejection = Literal["not-open", "insufficient-funds", "invalid-amount", "currency-mismatch"]


def decide_withdraw(command: Withdraw, state: AccountState) -> Decision[AccountEvent, WithdrawRejection]:
    if not isinstance(state, Open):
        return reject("not-open")
    if not isinstance(command.amount.minor_units, int) or command.amount.minor_units <= 0:
        return reject("invalid-amount")
    if command.amount.currency != state.balance.currency:
        return reject("currency-mismatch")
    if command.amount.minor_units > state.balance.minor_units:
        return reject("insufficient-funds")
    return accept((MoneyWithdrawn(command.amount),))
```
