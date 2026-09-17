```python
from __future__ import annotations

# `materialisation: live` — the view is folded per query and nothing is stored. No table, no checkpoint,
# no subscription, no rebuild path, and strongly consistent by construction: it reads the log the command
# just wrote. That is why it is the answer taken by default, and why the slice has to declare the ceiling
# it holds inside. Here the ceiling is asserted rather than assumed.

#: `liveBudget.events` for this view, and the argument for it belongs beside the number: one account
#: stream, which ends at closure, so the ceiling is the busiest account's lifetime and not a guess about
#: traffic. Raise it deliberately, or materialise the view — do not raise it because a test went red.
MAX_EVENTS_FOLDED = 40


class ViewOutgrewItsBudget(RuntimeError):
    """The stream got longer than this view is allowed to fold on every query."""


def read_balance_view(events: EventStore, account_id: StreamId) -> BalanceView:
    history = events.read(account_id)
    if len(history) > MAX_EVENTS_FOLDED:
        # Failing is the point. A per-query fold does not degrade visibly — it gets slower by a
        # millisecond a week until a page times out, and by then the fix is a table, a checkpoint, a
        # backfill and every caller. This turns that into one red test on the day the model changed.
        raise ViewOutgrewItsBudget(
            f"balance view folded {len(history)} events for {account_id}, over its budget of "
            f"{MAX_EVENTS_FOLDED}: close the stream at a business boundary, or materialise the view"
        )
    view = empty_balance_view
    for committed in history:
        view = apply_to_balance_view(
            view,
            AccountProjectionEnvelope(
                stream_id=committed.stream_id,
                global_position=committed.global_position,
                data=to_domain_event(committed),
            ),
        )
    return view
```

```python
# tests/projection/test_balance_view_budget.py — the test that makes the ceiling a fact
def test_a_stream_past_the_budget_fails_rather_than_getting_slower(events: EventStore) -> None:
    account = open_account_with_deposits(events, count=MAX_EVENTS_FOLDED)

    with pytest.raises(ViewOutgrewItsBudget):
        deposit(events, account, times=1)
        read_balance_view(events, account)
```
