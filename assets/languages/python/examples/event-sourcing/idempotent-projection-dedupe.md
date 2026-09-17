```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BalanceRow:
    """Per-account (single-stream) read-model row — version is unique within it."""

    balance_minor_units: int
    applied_through: int


class _HasAmount(Protocol):
    amount: Money


# idempotent apply: ignore any event at or below the version already applied
def project(row: BalanceRow, event: _HasAmount, version: int) -> BalanceRow:
    if version <= row.applied_through:
        return row
    if not isinstance(row.balance_minor_units, int) or not isinstance(event.amount.minor_units, int):
        raise ValueError("Invalid projection money")
    return BalanceRow(row.balance_minor_units + event.amount.minor_units, version)


def test_should_not_double_count_a_redelivered_event() -> None:
    event = MoneyDeposited(money(10_000))

    once = project(BalanceRow(0, 0), event, 1)
    twice = project(once, event, 1)  # the same event, redelivered at the same version

    assert once.balance_minor_units == 10_000
    assert twice.balance_minor_units == 10_000  # not 20_000
```
