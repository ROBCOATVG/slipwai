```java
/** The fold itself: a whole stream of envelopes into one view. */
static BalanceView project(List<EventEnvelope<AccountEvent>> history) {
    BalanceView view = EMPTY;
    for (EventEnvelope<AccountEvent> envelope : history) {
        view = applyToBalanceView(view, envelope);
    }
    return view;
}

// Rebuilding from position zero is the whole reason a projection is disposable: drop the row, replay,
// and the view is whatever the log says it is. A projection that cannot be rebuilt is a second source of
// truth, and a bug in it is unfixable.
static BalanceView rebuild(EventStore<AccountEvent> store, String accountId) {
    List<EventEnvelope<AccountEvent>> history = store.readAllForStream(accountId, 0);
    return project(history);
}
```
