```java
// An exception, because an invariant violation is a bug: no caller has a sensible response to "money was
// negative" other than to stop.
public record Money(long minorUnits, Currency currency) {
    public Money {
        if (minorUnits < 0) {
            throw new IllegalArgumentException("money cannot be negative: " + minorUnits);
        }
    }
}

// A result type, because this is an expected business outcome: the caller has something to do about an
// ineligible contributor, and it is not to crash.
public static PledgeDecision pledgeContribution(
        Occasion occasion, ContributorEligibility eligibility, PledgeId id, Money amount) {
    if (!eligibility.mayPledge()) {
        return new PledgeDecision.Refused(PledgeRefusal.CONTRIBUTOR_INELIGIBLE);
    }
    return new PledgeDecision.Recorded(occasion, List.of());
}
```
