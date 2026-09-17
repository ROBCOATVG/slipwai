```java
/**
 * No events needed here: the caller wants the new state, not a record of what happened. Returning the
 * updated aggregate is the simplest thing that works, and events can be added later without changing the
 * rules — only the return type.
 */
public static PledgeDecision pledgeContribution(
        Occasion occasion, ContributorEligibility eligibility, Money amount) {
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
    // The updated aggregate, and no event list.
    return new PledgeDecision.Recorded(
            occasion.withTotalPledged(occasion.totalPledged().plus(amount)), List.of());
}
```
