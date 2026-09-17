```java
/** One transaction saves one aggregate and its outbox event. Nothing else changes in the same breath. */
PledgeResult handlePledge(PledgeCommand command) {
    Optional<StoredOccasion> stored = persistence.findOccasionById(command.occasionId());
    if (stored.isEmpty()) {
        return new PledgeResult.NotFound();
    }

    PledgeDecision decision = recordPledge(stored.get().value(), command);
    if (!(decision instanceof PledgeDecision.Recorded recorded)) {
        return new PledgeResult.Decided(decision);
    }

    return persistence.saveWithOutbox(
                    recorded.occasion(), recorded.events(), stored.get().version()) == Saved.SAVED
            ? new PledgeResult.Decided(recorded)
            : new PledgeResult.ConcurrentChange();
}

/**
 * The other aggregate converges separately, driven by the event, and idempotently.
 *
 * <p>That is the trade being made: the two are consistent eventually rather than immediately, and in
 * exchange neither write can block or fail because of the other. `applyPledgeOnce` takes the event id so a
 * redelivery — which will happen — costs nothing.
 */
void handlePledgeRecorded(PledgeRecorded event) {
    contributors.applyPledgeOnce(event.id(), event.contributorId(), event.amount());
}
```
