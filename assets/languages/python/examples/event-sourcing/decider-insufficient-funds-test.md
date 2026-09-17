```python
from __future__ import annotations

from functools import reduce

# Ordinary behaviour-driven tests through the public decider API.
# The returned events/rejection are the observable behaviour of `decide`.


def open_account(currency: Currency = "GBP") -> AccountEvent:
    return AccountOpened(currency)


def money(minor_units: int, currency: Currency = "GBP") -> Money:
    return Money(minor_units, currency)


def deposited(minor_units: int) -> AccountEvent:
    return MoneyDeposited(money(minor_units))


def test_should_reject_a_withdrawal_that_exceeds_the_balance() -> None:
    state = reduce(evolve, [open_account(), deposited(5_000)], initial_state)

    decision = decide(Withdraw(money(10_000)), state)

    assert decision == Rejected("insufficient-funds")


def test_should_record_a_deposit_as_a_money_deposited_event_on_an_open_account() -> None:
    state = reduce(evolve, [open_account()], initial_state)

    decision = decide(Deposit(money(5_000)), state)

    assert decision == Accepted((MoneyDeposited(money(5_000)),))
```
