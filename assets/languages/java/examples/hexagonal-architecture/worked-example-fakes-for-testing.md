```java
// testing/InMemoryPledgePersistence.java
//
// Not final, deliberately: a test that needs to stage a stale read overrides findOccasionById to pin the
// version it reports. That is the one extension point a fake of a versioned port earns.
public class InMemoryPledgePersistence implements PledgePersistence {

    private final Map<OccasionId, StoredOccasion> occasions = new HashMap<>();
    private final List<Occasion> saved = new ArrayList<>();
    private final List<PledgeRecorded> outbox = new ArrayList<>();

    public InMemoryPledgePersistence(Occasion... initial) {
        for (Occasion occasion : initial) {
            occasions.put(occasion.id(), new StoredOccasion(occasion, 0));
        }
    }

    @Override
    public Optional<StoredOccasion> findOccasionById(OccasionId id) {
        return Optional.ofNullable(occasions.get(id));
    }

    /**
     * The version check is the point of this fake. A mock told to return SAVED would never disagree with
     * the use case about concurrency, so the retry path would be tested against nothing.
     */
    @Override
    public Saved saveWithOutbox(Occasion occasion, List<PledgeRecorded> events, int expectedVersion) {
        StoredOccasion current = occasions.get(occasion.id());
        if (current == null || current.version() != expectedVersion) {
            return Saved.CONFLICT;
        }
        occasions.put(occasion.id(), new StoredOccasion(occasion, expectedVersion + 1));
        saved.add(occasion);
        outbox.addAll(events);
        return Saved.SAVED;
    }

    public List<Occasion> saved() {
        return List.copyOf(saved);
    }

    public List<PledgeRecorded> outboxEvents() {
        return List.copyOf(outbox);
    }
}

// testing/InMemoryPledgeProjection.java — idempotent, like the real one.
public final class InMemoryPledgeProjection implements PledgeProjection {

    private final Map<PledgeId, PledgeRecorded> records = new LinkedHashMap<>();

    @Override
    public void recordFrom(PledgeRecorded event) {
        records.putIfAbsent(event.id(), event);
    }

    public List<PledgeRecorded> records() {
        return List.copyOf(records.values());
    }
}
```
