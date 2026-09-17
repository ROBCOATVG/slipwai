package com.example.deliverystarter.adapters.driven.eventstorememory;

import com.example.deliverystarter.application.ports.events.CommittedEvent;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Supplier;

/**
 * What a connection is, when there is no database.
 *
 * <p>It exists so the in-memory adapters can do the one thing the real ones do that matters most to the
 * read side: put an append, a view write and a checkpoint in <strong>one transaction</strong>. Build the
 * event store and the checkpoint store from the same instance — which is what
 * {@code new InMemoryCheckpointStore(store)} does — and {@code inUnitOfWork} covers all of it.
 *
 * <p>Rollback is a restore from a shallow copy taken on entry. That is honest for what this is for: it
 * proves the <em>semantics</em> a test needs (a failed batch changes nothing) without pretending to be a
 * transaction manager. Events are immutable records, so copying the lists is enough.
 *
 * <p>Its state is package-visible rather than private, because the store beside it is the other half of one
 * connection's worth of behaviour. Its <em>lock</em> is private, and {@link #atomically} is how anything
 * outside takes it: a lock object reachable from elsewhere is a lock somebody else can hold for their own
 * reasons, which is a deadlock nobody can find. Java monitors are re-entrant, so nesting these is free.
 */
public final class InMemoryDatabase {

    /**
     * One row of the leases this database holds — the storage shape of a projection's lease, without the
     * policy that decides whether it may be taken. That policy is the checkpoint adapter's.
     */
    public record LeaseRow(String owner, Instant expiresAt) {
    }

    private final Object lock = new Object();
    List<CommittedEvent> log = new ArrayList<>();
    /**
     * Global position to the tags it was indexed by — the derived index, kept beside the log rather than
     * on the event, exactly as the SQL adapters keep it in a table of its own.
     */
    Map<Long, List<String>> tags = new LinkedHashMap<>();
    Map<String, Long> checkpoints = new HashMap<>();
    Map<String, LeaseRow> leases = new HashMap<>();
    long nextGlobalPosition = 1;

    /**
     * Run {@code work}, undoing everything it changed if it throws.
     *
     * <p>The lock is deliberately not held across {@code work}: it is not re-entrant here in any useful
     * sense, and {@code work} calls back into methods that take it. Nesting therefore needs no counter —
     * the mutation happens in place, so a rollback is a restore, and an inner block restoring its own
     * snapshot leaves the outer one's intact.
     */
    /** Run {@code work} holding this database's lock, which nothing outside this class can take. */
    public <T> T atomically(Supplier<T> work) {
        synchronized (lock) {
            return work.get();
        }
    }

    public <T> T inUnitOfWork(Supplier<T> work) {
        List<CommittedEvent> log;
        Map<Long, List<String>> tags;
        Map<String, Long> checkpoints;
        Map<String, LeaseRow> leases;
        long nextGlobalPosition;
        synchronized (lock) {
            log = new ArrayList<>(this.log);
            tags = new LinkedHashMap<>(this.tags);
            checkpoints = new HashMap<>(this.checkpoints);
            leases = new HashMap<>(this.leases);
            nextGlobalPosition = this.nextGlobalPosition;
        }

        // A flag and a finally rather than a catch of everything: what has to happen is "undo unless it
        // succeeded", and that is what this says — without naming an exception type it would only rethrow.
        boolean done = false;
        try {
            T result = work.get();
            done = true;
            return result;
        } finally {
            if (!done) {
                synchronized (lock) {
                    this.log = log;
                    this.tags = tags;
                    this.checkpoints = checkpoints;
                    this.leases = leases;
                    this.nextGlobalPosition = nextGlobalPosition;
                }
            }
        }
    }

    long headLocked() {
        return log.isEmpty() ? 0 : log.get(log.size() - 1).globalPosition();
    }

    // positionOf, recordPosition, lease, setLease and deleteLease are the primitives the checkpoint
    // adapter is built from: storage, under this database's lock, with none of the policy that decides
    // whether a lease may be taken.

    /** A projection's recorded position, and zero for one nothing has recorded. */
    public long positionOf(String projection) {
        synchronized (lock) {
            return checkpoints.getOrDefault(projection, 0L);
        }
    }

    /** Write a projection's position. */
    public void recordPosition(String projection, long position) {
        synchronized (lock) {
            checkpoints.put(projection, position);
        }
    }

    /** The lease row a projection currently has, if any. */
    public Optional<LeaseRow> lease(String projection) {
        synchronized (lock) {
            return Optional.ofNullable(leases.get(projection));
        }
    }

    /** Write a projection's lease row. */
    public void setLease(String projection, LeaseRow row) {
        synchronized (lock) {
            leases.put(projection, row);
        }
    }

    /** Remove a projection's lease row, if {@code owner} still holds it. */
    public void deleteLease(String projection, String owner) {
        synchronized (lock) {
            LeaseRow held = leases.get(projection);
            if (held != null && held.owner().equals(owner)) {
                leases.remove(projection);
            }
        }
    }
}
