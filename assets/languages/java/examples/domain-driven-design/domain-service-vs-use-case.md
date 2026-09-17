```java
// DOMAIN SERVICE — business logic over domain types only. It sits with the concepts it serves.
public static PledgeDecision pledgeContribution(
        Occasion occasion, ContributorEligibility eligibility, PledgeId id, Money amount) {
    if (!eligibility.mayPledge()) {
        return new PledgeDecision.Refused(PledgeRefusal.CONTRIBUTOR_INELIGIBLE);
    }
    if (occasion.fundingClosed()) {
        return new PledgeDecision.Refused(PledgeRefusal.FUNDING_CLOSED);
    }
    if (amount.currency() != occasion.budget().currency()) {
        return new PledgeDecision.Refused(PledgeRefusal.CURRENCY_MISMATCH);
    }
    if (!amount.isPositive()) {
        return new PledgeDecision.Refused(PledgeRefusal.NON_POSITIVE_AMOUNT);
    }
    long remaining = occasion.budget().minorUnits() - occasion.totalPledged().minorUnits();
    if (amount.minorUnits() > remaining) {
        return new PledgeDecision.Refused(PledgeRefusal.EXCEEDS_BUDGET);
    }
    return new PledgeDecision.Recorded(
            occasion.withTotalPledged(occasion.totalPledged().plus(amount)),
            List.of(new PledgeRecorded(id, occasion.id(), eligibility.contributorId(), amount)));
}

// USE CASE — application orchestration and no business rules. Note that every line is either a call
// outward or a translation of one: load, load, decide, save. No rule is decided here.
@ApplicationScoped
final class PledgeHandler {

    private final PledgePersistence persistence;
    private final ContributorEligibilityGateway eligibilities;

    PledgeResult handle(PledgeCommand command) {
        Optional<StoredOccasion> stored = persistence.findOccasionById(command.occasionId());
        Optional<ContributorEligibility> eligibility =
                eligibilities.findFor(command.contributorId());
        if (stored.isEmpty() || eligibility.isEmpty()) {
            return new PledgeResult.NotFound();
        }

        PledgeDecision decision = pledgeContribution(
                stored.get().value(), eligibility.get(), command.pledgeId(), command.amount());
        if (!(decision instanceof PledgeDecision.Recorded recorded)) {
            return new PledgeResult.Decided(decision);
        }
        return persistence.saveWithOutbox(
                        recorded.occasion(), recorded.events(), stored.get().version()) == Saved.SAVED
                ? new PledgeResult.Decided(recorded)
                : new PledgeResult.ConcurrentChange();
    }
}
```
