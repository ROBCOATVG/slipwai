```typescript
// `materialisation: inline` — the view is written in the same transaction as the append, so it never lags
// the write and read-your-writes costs nothing on this slice. Two things to know before choosing it.
//
// The seam this needs is `EventStore.inUnitOfWork`, which the store you were given already has: a callback
// inside which `append` does not commit, so a view write beside it commits with the events it derives from,
// or neither happens. Any adapter built from the same store's session is inside that transaction too —
// which is why the view's own store below is constructed from it rather than from a pool of its own.
//
// The view must be scoped to the stream being appended. A view folding several streams cannot be kept
// atomic with one append: the row it writes is contended by every other stream's appends, which is a hot
// row and a cross-stream transaction wearing a projection's clothes. That view is `async`.

/**
 * This project's own view table, on the event store's session.
 *
 * Built from the store — `createBalanceViewStore(store)` — for the same reason the checkpoint store is: a
 * write on a second connection is a second transaction, and then "inline" is a word rather than a
 * guarantee.
 */
export interface BalanceViewStore {
  load(accountId: StreamId): Promise<BalanceView | undefined>;
  upsert(view: BalanceView): Promise<void>;
}

export async function depositMoney(
  store: EventStore,
  views: BalanceViewStore,
  command: DepositMoney,
): Promise<DepositOutcome> {
  return store.inUnitOfWork(async () => {
    const history = await store.read(command.accountId);
    const decision = accountDecider.decide(command, rehydrate(accountDecider, history));
    if (decision.outcome === 'rejected') return decision; // nothing appended, nothing projected

    const result = await store.append(command.accountId, currentVersion(history), decision.events);
    // Contention, not failure: the caller re-reads and re-decides. Nothing is half-written, which is the
    // one thing inline gives you for free.
    if (result.outcome === 'version-conflict') return result;

    // The same `applyToBalanceView` the `live` and `async` versions use — the lifecycle decides what
    // maintains the view, never how it is computed. Only the new events are applied: refolding the stream
    // here would put the whole history on the write path, which is the cost inline exists to avoid.
    let view = (await views.load(command.accountId)) ?? emptyBalanceView;
    for (const committed of (await store.read(command.accountId)).slice(history.length)) {
      view = applyToBalanceView(view, {
        streamId: committed.streamId,
        globalPosition: committed.globalPosition,
        data: toDomainEvent(committed),
      });
    }
    await views.upsert(view);
    return result;
  });
}
```

An inline view is still a derivation, so it still needs the rebuild path: when the fold changes or turns out
to be wrong, the fix is to reset the view and replay `readAll(0)` through the same `apply`. Inline removes
the checkpoint and the subscription, not the obligation to be rebuildable.
