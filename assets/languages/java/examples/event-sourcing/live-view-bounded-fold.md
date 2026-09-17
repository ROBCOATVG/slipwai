```java
// materialisation: live — the view is folded per query and nothing is stored. No table, no checkpoint, no
// subscription, no rebuild path, and strongly consistent by construction: it reads the log the command
// just wrote. That is why it is the answer taken by default, and why the slice has to declare the ceiling
// it holds inside. Here the ceiling is asserted rather than assumed.

public final class BalanceViews {

    /**
     * {@code liveBudget.events} for this view, and the argument for it belongs beside the number: one
     * account stream, which ends at closure, so the ceiling is the busiest account's lifetime and not a
     * guess about traffic. Raise it deliberately, or materialise the view — not because a test went red.
     */
    public static final int MAX_EVENTS_FOLDED = 40;

    public static final class ViewOutgrewItsBudget extends RuntimeException {
        ViewOutgrewItsBudget(String message) {
            super(message);
        }
    }

    public static BalanceView readBalanceView(EventStore events, String accountId) {
        List<CommittedEvent> history = events.read(accountId);
        if (history.size() > MAX_EVENTS_FOLDED) {
            // Failing is the point. A per-query fold does not degrade visibly — it gets slower by a
            // millisecond a week until a request times out, and by then the fix is a table, a checkpoint,
            // a backfill and every caller. This turns that into one red test on the day the model changed.
            throw new ViewOutgrewItsBudget(
                    "balance view folded %d events for %s, over its budget of %d: close the stream at a "
                            .formatted(history.size(), accountId, MAX_EVENTS_FOLDED)
                            + "business boundary, or materialise the view");
        }
        BalanceView view = BalanceView.empty();
        for (CommittedEvent committed : history) {
            view = BalanceView.apply(view, new ProjectionEnvelope(
                    committed.streamId(), committed.globalPosition(), toDomainEvent(committed)));
        }
        return view;
    }
}
```

```java
// BalanceViewBudgetTest.java — the test that makes the ceiling a fact
@Test
void aStreamPastTheBudgetFailsRatherThanGettingSlower() {
    String account = openAccountWithDeposits(events, BalanceViews.MAX_EVENTS_FOLDED);

    deposit(events, account, 1);

    assertThatThrownBy(() -> BalanceViews.readBalanceView(events, account))
            .isInstanceOf(BalanceViews.ViewOutgrewItsBudget.class);
}
```
