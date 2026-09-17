```python
from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn, Union


@dataclass(frozen=True, slots=True)
class BalanceViewUnopened:
    pass


@dataclass(frozen=True, slots=True)
class BalanceViewOpen:
    account_id: StreamId
    balance_minor_units: int
    currency: Currency


BalanceView = Union[BalanceViewUnopened, BalanceViewOpen]

empty_balance_view: BalanceView = BalanceViewUnopened()


@dataclass(frozen=True, slots=True)
class AccountProjectionEnvelope:
    stream_id: StreamId
    global_position: int
    data: AccountEvent


class CorruptProjectionError(RuntimeError):
    """A known event cannot follow the current view — corrupt history, not a no-op."""


def _corrupt_balance_projection(view: BalanceView, event: AccountEvent) -> CorruptProjectionError:
    return CorruptProjectionError(
        f"Corrupt balance projection: {type(event).__name__} cannot follow {type(view).__name__}"
    )


def is_positive_minor_units(minor_units: int) -> bool:
    return isinstance(minor_units, int) and minor_units > 0


def add_minor_units(left: int, right: int) -> int:
    if not isinstance(left, int) or not isinstance(right, int):
        raise CorruptProjectionError("Corrupt account history: unsafe minor-unit operand")
    result = left + right
    if result < 0:
        raise CorruptProjectionError("Corrupt account history: invalid projected balance")
    return result


def _assert_never(value: NoReturn) -> NoReturn:
    raise AssertionError(f"Unhandled variant: {value!r}")


def apply(view: BalanceView, envelope: AccountProjectionEnvelope) -> BalanceView:
    event = envelope.data
    match event:
        case AccountOpened(currency):
            if not isinstance(view, BalanceViewUnopened):
                raise _corrupt_balance_projection(view, event)
            return BalanceViewOpen(envelope.stream_id, 0, currency)

        case MoneyDeposited(amount):
            if (
                not isinstance(view, BalanceViewOpen)
                or view.account_id != envelope.stream_id
                or not is_positive_minor_units(amount.minor_units)
                or amount.currency != view.currency
            ):
                raise _corrupt_balance_projection(view, event)
            return BalanceViewOpen(
                view.account_id,
                add_minor_units(view.balance_minor_units, amount.minor_units),
                view.currency,
            )

        case MoneyWithdrawn(amount):
            if (
                not isinstance(view, BalanceViewOpen)
                or view.account_id != envelope.stream_id
                or not is_positive_minor_units(amount.minor_units)
                or amount.currency != view.currency
                or amount.minor_units > view.balance_minor_units
            ):
                raise _corrupt_balance_projection(view, event)
            return BalanceViewOpen(
                view.account_id,
                add_minor_units(view.balance_minor_units, -amount.minor_units),
                view.currency,
            )

        case _:
            _assert_never(event)
```
