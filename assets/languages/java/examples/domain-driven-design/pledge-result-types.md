```java
public sealed interface PledgeDecision {
    record Recorded(Occasion occasion, List<PledgeRecorded> events) implements PledgeDecision { }

    record Refused(PledgeRefusal reason) implements PledgeDecision { }
}

/** The domain's refusals: each one is a rule somebody can point at in a conversation. */
public enum PledgeRefusal {
    CONTRIBUTOR_INELIGIBLE, NON_POSITIVE_AMOUNT, CURRENCY_MISMATCH, EXCEEDS_BUDGET, FUNDING_CLOSED
}

/** The application's outcomes, which are about coordination rather than about the business. */
public sealed interface PledgeResult {
    record Decided(PledgeDecision decision) implements PledgeResult { }

    record NotFound() implements PledgeResult { }

    record ConcurrentChange() implements PledgeResult { }
}
```
