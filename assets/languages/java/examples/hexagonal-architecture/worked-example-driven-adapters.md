```java
// adapters/driven/JdbcPledgePersistence.java
@ApplicationScoped
final class JdbcPledgePersistence implements PledgePersistence {

    private final DataSource dataSource;

    @Override
    public Optional<StoredOccasion> findOccasionById(OccasionId id) { }

    /**
     * The occasion row and its outbox rows commit together or not at all. That is the entire reason the
     * port exposes one method instead of two: two calls could be interrupted between them, and an event
     * that never got published is indistinguishable from one that never happened.
     */
    @Override
    @Transactional
    public Saved saveWithOutbox(Occasion occasion, List<PledgeRecorded> events, int expectedVersion) {
        if (update(occasion, expectedVersion) != 1) {
            return Saved.CONFLICT;
        }
        insertOutbox(events);
        return Saved.SAVED;
    }
}

// adapters/driven/JdbcPledgeProjection.java
@ApplicationScoped
final class JdbcPledgeProjection implements PledgeProjection {

    /**
     * ON CONFLICT DO NOTHING on the event id, which is what makes redelivery free. A broker promises "at
     * least once", so this method will be called twice with the same event — that is normal operation and
     * not an error to report.
     */
    private static final String INSERT = """
            INSERT INTO pledge_projection (event_id, occasion_id, contributor_id, amount_minor_units)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (event_id) DO NOTHING
            """;

    @Override
    public void recordFrom(PledgeRecorded event) { }
}
```
