```java
// application/PledgingToOccasions.java — the use case.
final class PledgingToOccasions implements ForPledgingToOccasions {

    private final PledgePersistence persistence;

    PledgingToOccasions(PledgePersistence persistence) {
        this.persistence = persistence;
    }

    @Override
    public PledgeResult pledgeToOccasion(PledgeCommand command) {
        Optional<PledgePersistence.StoredOccasion> stored =
                persistence.findOccasionById(command.occasionId());
        if (stored.isEmpty()) {
            return new PledgeResult.Refused("not-found");
        }

        // The decision is the domain's. This method's whole job is what surrounds it.
        PledgeDecision decision = recordPledge(
                stored.get().value(), command.pledgeId(), command.pledger().contributorId(),
                command.amount());

        return switch (decision) {
            case PledgeDecision.Refused refused ->
                    new PledgeResult.Refused(refused.reason().name());
            case PledgeDecision.Recorded recorded -> persistence.saveWithOutbox(
                            recorded.occasion(), recorded.events(), stored.get().version())
                    == PledgePersistence.Saved.SAVED
                    ? new PledgeResult.Recorded(recorded.occasion(), recorded.events())
                    : new PledgeResult.Refused("concurrent-change");
        };
    }
}

// application/PledgeRecordedHandler.java — the read side, kept separate on purpose.
@ApplicationScoped
final class PledgeRecordedHandler {

    private final PledgeProjection projection;

    void handle(PledgeRecorded event) {
        projection.recordFrom(event);
    }
}
```
