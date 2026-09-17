```java
// domain/Types.java — the vocabulary, with the invariants inside the types rather than beside them.

/** A wrapper type, not a String. An OccasionId cannot be passed where a ContributorId belongs. */
public record OccasionId(String value) {
    public OccasionId {
        if (value.isBlank()) {
            throw new IllegalArgumentException("an occasion id cannot be blank");
        }
    }
}

public record ContributorId(String value) { }

public record PledgeId(String value) { }

public enum Currency { GBP, USD, EUR }

/** Minor units as a long, never a double, and never negative. Validated in the constructor. */
public record Money(long minorUnits, Currency currency) {
    public Money {
        if (minorUnits < 0) {
            throw new IllegalArgumentException("money cannot be negative: " + minorUnits);
        }
    }

    public static Money of(long minorUnits, Currency currency) {
        return new Money(minorUnits, currency);
    }

    public boolean isPositive() {
        return minorUnits > 0;
    }
}

public record Occasion(
        OccasionId id, String name, Money budget, Money totalPledged, boolean fundingClosed) {

    /** An always-valid aggregate: the invariant is checked here, so no code path can construct a bad one. */
    public Occasion {
        if (budget.currency() != totalPledged.currency()) {
            throw new IllegalArgumentException("an occasion's budget and pledges must share a currency");
        }
        if (totalPledged.minorUnits() > budget.minorUnits()) {
            throw new IllegalArgumentException("pledges cannot exceed the budget");
        }
    }
}

public record PledgeRecorded(
        PledgeId id, OccasionId occasionId, ContributorId contributorId, Money amount) { }

public sealed interface PledgeDecision {
    record Recorded(Occasion occasion, List<PledgeRecorded> events) implements PledgeDecision { }

    record Refused(PledgeRefusal reason) implements PledgeDecision { }
}

/** An enum rather than free text, so the HTTP mapping can be exhaustive over it. */
public enum PledgeRefusal {
    NON_POSITIVE_AMOUNT, CURRENCY_MISMATCH, EXCEEDS_BUDGET, FUNDING_CLOSED
}
```
