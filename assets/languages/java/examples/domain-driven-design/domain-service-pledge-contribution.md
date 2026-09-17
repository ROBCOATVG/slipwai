```java
// WRONG — the entity is asked to enforce a rule about something outside itself. An Occasion cannot know
// whether a contributor is currently eligible, and giving it a way to find out would put a gateway call
// inside an aggregate.
public Occasion addContribution(Contribution contribution) { }

// CORRECT — a pure domain service, taking the eligibility as a read-only fact somebody else established.
// A domain service is where a rule lives when it spans more than one aggregate and belongs to neither.
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
```
