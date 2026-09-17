```java
/**
 * An application-owned port where one semantic operation must save both or neither. The port says
 * "together"; how that is achieved is the adapter's problem.
 */
public interface PledgePersistence {

    Optional<StoredOccasion> findOccasionById(OccasionId id);

    Saved saveWithOutbox(Occasion occasion, List<PledgeRecorded> events, int expectedVersion);

    record StoredOccasion(Occasion value, int version) { }

    enum Saved { SAVED, CONFLICT }
}

/**
 * The adapter owns the transaction. `@Transactional` is the framework's — transaction demarcation is
 * infrastructure, and putting it on a use case would drag a framework annotation into the application
 * layer to describe something the application cannot see.
 */
@ApplicationScoped
final class JdbcPledgePersistence implements PledgePersistence {

    @Override
    @Transactional
    public Saved saveWithOutbox(Occasion occasion, List<PledgeRecorded> events, int expectedVersion) {
        if (updateOccasion(occasion, expectedVersion) != 1) {
            return Saved.CONFLICT;   // the version moved; nothing written, nothing to undo
        }
        insertOutbox(events);        // same transaction, so the row and the event commit together
        return Saved.SAVED;
    }
}
```
