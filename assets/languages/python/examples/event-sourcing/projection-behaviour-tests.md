```python
from __future__ import annotations

from functools import reduce

import pytest


def account_envelope(
    data: AccountEvent, global_position: int, stream_id: StreamId = account_id
) -> AccountProjectionEnvelope:
    return AccountProjectionEnvelope(stream_id, global_position, data)


def test_should_reflect_net_balance_from_a_sequence_of_account_events() -> None:
    view = reduce(
        apply_to_balance_view,
        [
            account_envelope(opened(), 1),
            account_envelope(deposited(10_000), 2),
            account_envelope(withdrawn(3_000), 3),
        ],
        empty_balance_view,
    )

    assert view == BalanceViewOpen(
        account_id=account_id,
        balance_minor_units=7_000,
        currency="GBP",
    )


def test_should_surface_a_duplicate_account_opening_as_corrupt_projection_history() -> None:
    history = [
        account_envelope(opened("GBP"), 1),
        account_envelope(opened("EUR"), 2),
    ]

    with pytest.raises(CorruptProjectionError, match="Corrupt balance projection"):
        reduce(apply_to_balance_view, history, empty_balance_view)
```
