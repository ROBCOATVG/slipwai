```java
// domain/Pledges.java — an aggregate operation as a pure function. No clock, no store, no framework.
public static PledgeDecision recordPledge(
        Occasion occasion, PledgeId pledgeId, ContributorId contributor, Money amount) {

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

    // A new Occasion rather than a mutated one: the caller's copy stays exactly as it was, so a refusal
    // further up cannot leave a half-applied change behind.
    Occasion updated = new Occasion(
            occasion.id(),
            occasion.name(),
            occasion.budget(),
            Money.of(occasion.totalPledged().minorUnits() + amount.minorUnits(), amount.currency()),
            occasion.fundingClosed());

    return new PledgeDecision.Recorded(
            updated, List.of(new PledgeRecorded(pledgeId, occasion.id(), contributor, amount)));
}
```
