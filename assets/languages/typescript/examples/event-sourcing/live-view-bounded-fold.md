```typescript
// `materialisation: live` — the view is folded per query and nothing is stored. No table, no checkpoint,
// no subscription, no rebuild path, and strongly consistent by construction: it reads the log the command
// just wrote. That is why it is the answer taken by default, and why the slice has to declare the ceiling
// it holds inside. Here the ceiling is asserted rather than assumed.

/**
 * `liveBudget.events` for this view, and the argument for it belongs beside the number: one account
 * stream, which ends at closure, so the ceiling is the busiest account's lifetime and not a guess about
 * traffic. Raise it deliberately, or materialise the view — do not raise it because a test went red.
 */
const MAX_EVENTS_FOLDED = 40;

export class ViewOutgrewItsBudget extends Error {}

export async function readBalanceView(events: EventStore, accountId: StreamId): Promise<BalanceView> {
  const history = await events.read(accountId);
  if (history.length > MAX_EVENTS_FOLDED) {
    // Failing is the point. A per-query fold does not degrade visibly — it gets slower by a millisecond a
    // week until a page times out, and by then the fix is a table, a checkpoint, a backfill and every
    // caller. This turns that into one red test on the day the model changed.
    throw new ViewOutgrewItsBudget(
      `balance view folded ${String(history.length)} events for ${accountId}, over its budget of ` +
        `${String(MAX_EVENTS_FOLDED)}: close the stream at a business boundary, or materialise the view`,
    );
  }
  return history.reduce<BalanceView>(
    (view, committed) =>
      applyToBalanceView(view, {
        streamId: committed.streamId,
        globalPosition: committed.globalPosition,
        data: toDomainEvent(committed),
      }),
    emptyBalanceView,
  );
}
```

```typescript
// tests/projection/balance-view-budget.test.ts — the test that makes the ceiling a fact
it('fails on a stream past the budget rather than getting slower', async () => {
  const account = await openAccountWithDeposits(events, MAX_EVENTS_FOLDED);

  await deposit(events, account, 1);

  await expect(readBalanceView(events, account)).rejects.toThrow(ViewOutgrewItsBudget);
});
```
