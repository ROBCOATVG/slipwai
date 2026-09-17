```python
from __future__ import annotations

from functools import reduce


def test_should_reflect_deposits_and_withdrawals_in_the_balance_available_to_withdraw() -> None:
    state = reduce(evolve, [opened(), deposited(10_000), withdrawn(3_000)], initial_state)

    # behaviour: GBP 70.00 is available, GBP 70.01 is not
    assert isinstance(decide(Withdraw(money(7_000)), state), Accepted)
    assert isinstance(decide(Withdraw(money(7_001)), state), Rejected)
```
