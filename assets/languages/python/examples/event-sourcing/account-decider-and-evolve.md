```python
# domain/account/account.py — pure, no infrastructure imports
from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn, Union

Currency = str  # ISO 4217 currency code, e.g. "GBP"

_MAX_SAFE_MINOR_UNITS = 2**53 - 1  # cross-service JSON/number interop bound


@dataclass(frozen=True, slots=True)
class Money:
    minor_units: int
    currency: Currency


def is_positive_money(money: Money) -> bool:
    return isinstance(money.minor_units, int) and money.minor_units > 0


# --- state: a closed set of variants, never one dataclass with optional fields ---

@dataclass(frozen=True, slots=True)
class Unopened:
    pass


@dataclass(frozen=True, slots=True)
class Open:
    balance: Money


AccountState = Union[Unopened, Open]

initial_state: AccountState = Unopened()


# --- commands ---

@dataclass(frozen=True, slots=True)
class OpenAccount:
    currency: Currency


@dataclass(frozen=True, slots=True)
class Deposit:
    amount: Money


@dataclass(frozen=True, slots=True)
class Withdraw:
    amount: Money


AccountCommand = Union[OpenAccount, Deposit, Withdraw]


# --- events ---

@dataclass(frozen=True, slots=True)
class AccountOpened:
    currency: Currency


@dataclass(frozen=True, slots=True)
class MoneyDeposited:
    amount: Money


@dataclass(frozen=True, slots=True)
class MoneyWithdrawn:
    amount: Money


AccountEvent = Union[AccountOpened, MoneyDeposited, MoneyWithdrawn]


# --- decision result: accept/reject, never an exception for an expected business outcome ---

@dataclass(frozen=True, slots=True)
class Accepted:
    events: tuple[AccountEvent, ...]


@dataclass(frozen=True, slots=True)
class Rejected:
    reason: str


Decision = Union[Accepted, Rejected]


def accept(events: tuple[AccountEvent, ...]) -> Accepted:
    return Accepted(events)


def reject(reason: str) -> Rejected:
    return Rejected(reason)


def _assert_never(value: NoReturn) -> NoReturn:
    raise AssertionError(f"Unhandled variant: {value!r}")


# decide: what SHOULD happen? Returns events (or a rejection). Enforces invariants.
def decide(command: AccountCommand, state: AccountState) -> Decision:
    match command:
        case OpenAccount(currency):
            if isinstance(state, Open):
                return reject("already-open")
            return accept((AccountOpened(currency),))

        case Deposit(amount):
            if not isinstance(state, Open):
                return reject("not-open")
            if not is_positive_money(amount):
                return reject("invalid-amount")
            if amount.currency != state.balance.currency:
                return reject("currency-mismatch")
            if state.balance.minor_units + amount.minor_units > _MAX_SAFE_MINOR_UNITS:
                return reject("balance-overflow")
            return accept((MoneyDeposited(amount),))

        case Withdraw(amount):
            if not isinstance(state, Open):
                return reject("not-open")
            if not is_positive_money(amount):
                return reject("invalid-amount")
            if amount.currency != state.balance.currency:
                return reject("currency-mismatch")
            if amount.minor_units > state.balance.minor_units:
                return reject("insufficient-funds")
            return accept((MoneyWithdrawn(amount),))

        case _:
            _assert_never(command)


class CorruptEventStreamError(RuntimeError):
    """A known event cannot follow the current state — corrupt history, not a no-op."""


def _corrupt_history(state: AccountState, event: AccountEvent) -> CorruptEventStreamError:
    return CorruptEventStreamError(
        f"Corrupt account stream: {type(event).__name__} cannot follow {type(state).__name__}"
    )


def _add_minor_units(left: int, right: int) -> int:
    if not isinstance(left, int) or not isinstance(right, int):
        raise CorruptEventStreamError("Corrupt account stream: unsafe minor-unit operand")
    result = left + right
    if not (0 <= result <= _MAX_SAFE_MINOR_UNITS):
        raise CorruptEventStreamError("Corrupt account stream: invalid resulting balance")
    return result


def _apply_delta(balance: Money, delta_minor_units: int) -> Money:
    return Money(_add_minor_units(balance.minor_units, delta_minor_units), balance.currency)


# evolve applies facts; an impossible known transition is corrupt history, not a no-op.
def evolve(state: AccountState, event: AccountEvent) -> AccountState:
    match event:
        case AccountOpened(currency):
            if not isinstance(state, Unopened):
                raise _corrupt_history(state, event)
            return Open(Money(0, currency))

        case MoneyDeposited(amount):
            if (
                not isinstance(state, Open)
                or not is_positive_money(amount)
                or amount.currency != state.balance.currency
            ):
                raise _corrupt_history(state, event)
            return Open(_apply_delta(state.balance, amount.minor_units))

        case MoneyWithdrawn(amount):
            if (
                not isinstance(state, Open)
                or not is_positive_money(amount)
                or amount.currency != state.balance.currency
                or amount.minor_units > state.balance.minor_units
            ):
                raise _corrupt_history(state, event)
            return Open(_apply_delta(state.balance, -amount.minor_units))

        case _:
            _assert_never(event)
```
