```python
from __future__ import annotations

from typing import Protocol

# `materialisation: inline` — the view is written in the same transaction as the append, so it never lags
# the write and read-your-writes costs nothing on this slice. Two things to know before choosing it.
#
# The seam this needs is `EventStore.unit_of_work()`, which the store you were given already has: a block
# inside which `append` does not commit, so a view write beside it commits with the events it derives from,
# or neither happens. Any adapter built from the same store is inside that transaction too — which is why
# the view's own store below is constructed from it rather than from a connection of its own.
#
# The view must be scoped to the stream being appended. A view folding several streams cannot be kept
# atomic with one append: the row it writes is contended by every other stream's appends, which is a hot
# row and a cross-stream transaction wearing a projection's clothes. That view is `async`.


class BalanceViewStore(Protocol):
    """This project's own view table, on the event store's connection.

    Built from the store — `create_balance_view_store(store)` — for the same reason the checkpoint store
    is: a write on a second connection is a second transaction, and then "inline" is a word rather than a
    guarantee.
    """

    def load(self, account_id: StreamId) -> BalanceView | None: ...
    def upsert(self, view: BalanceView) -> None: ...


def deposit_money(
    store: EventStore,
    views: BalanceViewStore,
    command: DepositMoney,
) -> DepositOutcome:
    with store.unit_of_work():
        history = store.read(command.account_id)
        decision = account_decider.decide(command, rehydrate(account_decider, history))
        if isinstance(decision, Rejected):
            return decision  # nothing appended, nothing projected, the transaction rolls back

        result = store.append(command.account_id, current_version(history), decision.events)
        if isinstance(result, VersionConflict):
            # Contention, not failure: the caller re-reads and re-decides. Nothing is half-written,
            # which is the one thing inline gives you for free.
            return result

        # The same `apply` the `live` and `async` versions use — the lifecycle decides what maintains the
        # view, never how it is computed. Only the new events are applied: refolding the stream here would
        # put the whole history on the write path, which is the cost inline exists to avoid.
        view = views.load(command.account_id) or empty_balance_view
        for committed in store.read(command.account_id)[len(history):]:
            view = apply_to_balance_view(
                view,
                AccountProjectionEnvelope(
                    stream_id=committed.stream_id,
                    global_position=committed.global_position,
                    data=to_domain_event(committed),
                ),
            )
        views.upsert(view)
        return result
```

An inline view is still a derivation, so it still needs the rebuild path: when the fold changes or turns out
to be wrong, the fix is to reset the view and replay `read_all(0)` through the same `apply`. Inline removes
the checkpoint and the subscription, not the obligation to be rebuildable.
