```java
// application/Pledging.java — the driving port and the result the application returns.
public sealed interface PledgeResult {
    record Recorded(Occasion occasion, List<PledgeRecorded> events) implements PledgeResult { }

    /** The domain's refusals, plus the two only the application can discover. */
    record Refused(String reason) implements PledgeResult { }
}

/**
 * A principal only the authentication adapter can construct. The private constructor is the whole
 * mechanism: no use case, test helper or request body can conjure one, so "authenticated" means it.
 */
public final class AuthenticatedPledger {

    private final ContributorId contributorId;

    private AuthenticatedPledger(ContributorId contributorId) {
        this.contributorId = contributorId;
    }

    /** Called by the authentication adapter, and by a test fixture in the same package. */
    static AuthenticatedPledger of(ContributorId contributorId) {
        return new AuthenticatedPledger(contributorId);
    }

    public ContributorId contributorId() {
        return contributorId;
    }
}

public interface ForPledgingToOccasions {
    PledgeResult pledgeToOccasion(PledgeCommand command);
}

public record PledgeCommand(
        PledgeId pledgeId, OccasionId occasionId, AuthenticatedPledger pledger, Money amount) { }

// application/PledgePersistence.java — the driven port.
public interface PledgePersistence {

    Optional<StoredOccasion> findOccasionById(OccasionId id);

    Saved saveWithOutbox(Occasion occasion, List<PledgeRecorded> events, int expectedVersion);

    record StoredOccasion(Occasion value, int version) { }

    enum Saved { SAVED, CONFLICT }
}

// application/PledgeProjection.java — the driven port for the read side.
public interface PledgeProjection {
    /** The input is an immutable log record: one id permanently names one payload. */
    void recordFrom(PledgeRecorded event);
}
```
