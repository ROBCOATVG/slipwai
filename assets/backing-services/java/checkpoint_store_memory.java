package com.example.deliverystarter.adapters.driven.checkpointstorememory;

import com.example.deliverystarter.adapters.driven.eventstorememory.InMemoryDatabase;
import com.example.deliverystarter.adapters.driven.eventstorememory.InMemoryEventStore;
import com.example.deliverystarter.application.ports.readmodels.CheckpointStore;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;

/**
 * The in-memory checkpoint store, on the same "connection" as the in-memory event store.
 *
 * <p>Built from the store rather than standing alone, which is the rule every checkpoint adapter here
 * follows: {@code record} has to land in the same transaction as the view write it accounts for, and an
 * adapter that does not share the store's unit of work cannot do that however carefully it is called.
 *
 * <p>What it can prove: that a projection resumes from where it stopped, that one worker at a time advances
 * it, that a lease expires, and that a batch which fails leaves both the view and the checkpoint where they
 * were. What it cannot prove is a genuine race between two workers, because this one serialises them —
 * {@code make test-integration} is where two connections contend for one lease.
 */
public final class InMemoryCheckpointStore implements CheckpointStore {

    private final InMemoryDatabase database;

    /** Take the store's own database, so both adapters are inside one unit of work. */
    public InMemoryCheckpointStore(InMemoryEventStore store) {
        this.database = store.sharedDatabase();
    }

    @Override
    public long positionOf(String projection) {
        return database.positionOf(projection);
    }

    @Override
    public void record(String projection, long position) {
        database.recordPosition(projection, position);
    }

    @Override
    public Optional<Lease> claim(String projection, String owner, Instant now, Duration ttl) {
        Optional<InMemoryDatabase.LeaseRow> held = database.lease(projection);
        if (held.isPresent() && !held.get().owner().equals(owner) && held.get().expiresAt().isAfter(now)) {
            return Optional.empty();
        }
        Instant expiresAt = now.plus(ttl);
        database.setLease(projection, new InMemoryDatabase.LeaseRow(owner, expiresAt));
        return Optional.of(new Lease(projection, owner, expiresAt));
    }

    @Override
    public void release(Lease lease) {
        database.deleteLease(lease.projection(), lease.owner());
    }
}
