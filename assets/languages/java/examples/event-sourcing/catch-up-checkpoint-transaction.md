```java
/**
 * One event, applied and checkpointed in a single transaction.
 *
 * <p>If the checkpoint moved in a second transaction, a crash between the two would replay the event and
 * double-count it — which is exactly what "at least once" delivery guarantees will eventually happen.
 * {@code @Transactional} is the framework's, and that is the right place for it: transaction demarcation
 * is infrastructure, and the fold it wraps is pure.
 */
@Transactional
public void apply(EventEnvelope<AccountEvent> envelope) {
    checkpoints.lockExclusively(PROJECTION_NAME);

    long appliedThrough = checkpoints.load(PROJECTION_NAME);
    if (envelope.globalPosition() <= appliedThrough) {
        return;   // an exact redelivery, so there is nothing to do
    }
    if (envelope.globalPosition() != appliedThrough + 1) {
        // A gap means an earlier event is still in flight. Failing here leaves the checkpoint where it
        // was, so the retry arrives in order rather than skipping what was missed.
        throw new IllegalStateException("Projection gap at position " + envelope.globalPosition()
                + ": retry after the missing position");
    }

    BalanceView current = views.load(envelope.streamId()).orElse(EMPTY);
    views.save(envelope.streamId(), applyToBalanceView(current, envelope));
    checkpoints.save(PROJECTION_NAME, envelope.globalPosition());   // the same transaction
}
```
