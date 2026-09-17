```python
from __future__ import annotations

from functools import reduce

# Event/money factories — complete, valid data with overrides (testing skill's factory pattern)


def opened(currency: Currency = "GBP") -> AccountEvent:
    return AccountOpened(currency)


def money(minor_units: int, currency: Currency = "GBP") -> Money:
    return Money(minor_units, currency)


def deposited(minor_units: int) -> AccountEvent:
    return MoneyDeposited(money(minor_units))


def withdrawn(minor_units: int) -> AccountEvent:
    return MoneyWithdrawn(money(minor_units))


def test_should_record_a_deposit_as_money_deposited_on_an_open_account() -> None:
    state = reduce(evolve, [opened()], initial_state)

    decision = decide(Deposit(money(5_000)), state)

    assert decision == Accepted((MoneyDeposited(money(5_000)),))


def test_should_reject_a_withdrawal_that_exceeds_the_balance() -> None:
    state = reduce(evolve, [opened(), deposited(5_000)], initial_state)

    decision = decide(Withdraw(money(10_000)), state)

    assert decision == Rejected("insufficient-funds")


def test_should_reject_any_operation_on_an_account_that_was_never_opened() -> None:
    decision = decide(Deposit(money(5_000)), initial_state)

    assert decision == Rejected("not-open")
```
