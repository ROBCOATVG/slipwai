```java
// Domain: returns a reason in the business's vocabulary.
public static PledgeDecision pledgeContribution(
        Occasion occasion, ContributorEligibility eligibility, PledgeId id, Money amount) {
    if (occasion.fundingClosed()) {
        return new PledgeDecision.Refused(PledgeRefusal.FUNDING_CLOSED);
    }
    return recordPledge(occasion, id, eligibility.contributorId(), amount);
}

// Application: propagates the decision, and adds only what it alone can discover.
PledgeResult handlePledge(PledgeCommand command) {
    Optional<StoredOccasion> stored = persistence.findOccasionById(command.occasionId());
    Optional<ContributorEligibility> eligibility = eligibilities.findFor(command.contributorId());
    if (stored.isEmpty() || eligibility.isEmpty()) {
        return new PledgeResult.NotFound();
    }

    PledgeDecision decision = pledgeContribution(
            stored.get().value(), eligibility.get(), command.pledgeId(), command.amount());
    if (!(decision instanceof PledgeDecision.Recorded recorded)) {
        return new PledgeResult.Decided(decision);
    }
    return persistence.saveWithOutbox(recorded.occasion(), recorded.events(), stored.get().version())
                    == Saved.SAVED
            ? new PledgeResult.Decided(recorded)
            : new PledgeResult.ConcurrentChange();
}

// Driving adapter: the only place a reason becomes a status code.
private static Response toResponse(PledgeResult result) {
    return switch (result) {
        case PledgeResult.NotFound notFound -> Response.status(404).build();
        case PledgeResult.ConcurrentChange conflict -> Response.status(409).build();
        case PledgeResult.Decided decided -> switch (decided.decision()) {
            case PledgeDecision.Recorded recorded ->
                    Response.ok(Map.of("pledged", recorded.occasion().totalPledged())).build();
            case PledgeDecision.Refused refused ->
                    Response.status(422).entity(Map.of("error", refused.reason())).build();
        };
    };
}
```
