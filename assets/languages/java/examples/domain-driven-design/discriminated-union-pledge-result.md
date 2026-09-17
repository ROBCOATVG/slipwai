```java
/** What the domain can decide. Every refusal is a named case rather than a string. */
public sealed interface PledgeDecision {
    record Recorded(Occasion occasion, List<PledgeRecorded> events) implements PledgeDecision { }

    record Refused(PledgeRefusal reason) implements PledgeDecision { }
}

public enum PledgeRefusal {
    CONTRIBUTOR_INELIGIBLE, NON_POSITIVE_AMOUNT, CURRENCY_MISMATCH, EXCEEDS_BUDGET, FUNDING_CLOSED
}

/**
 * What the application can return: everything the domain decided, plus the two outcomes only the
 * application can discover. Kept as separate types on purpose — "not found" is not a business rule, and
 * folding it into PledgeRefusal would put it in front of the domain's exhaustive switches.
 */
public sealed interface PledgeResult {
    record Decided(PledgeDecision decision) implements PledgeResult { }

    record NotFound() implements PledgeResult { }

    record ConcurrentChange() implements PledgeResult { }
}
```
