package com.example.deliverystarter.projections;

import com.example.deliverystarter.application.ports.events.CommittedEvent;
import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.readmodels.CheckpointStore;
import com.example.deliverystarter.application.ports.readmodels.Projection;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Supplier;

/**
 * The catch-up runner: how an async read model is maintained, and how it is rebuilt.
 *
 * <p>Two verbs over the two ports, and no I/O of its own — which is why it is here beside the application
 * rather than under {@code adapters}, and why its tests need no database.
 *
 * <pre>{@code
 * Projections.Advance advance = Projections.catchUp(store, checkpoints, view,
 *         new Projections.Runner("worker-1", Instant::now));
 * }</pre>
 *
 * <p>{@code catchUp} is one pass: it reads the log from the projection's checkpoint, applies it in batches,
 * and advances the checkpoint <strong>inside the same transaction as the rows it derived</strong>.
 * {@code catchUpEach} is that pass over every projection at once, and what loops over <em>it</em> is the
 * framework: {@code ScheduledProjections} is a {@code @Scheduled} bean that
 * picks up every {@code Projection} bean there is. A project with only live and inline read models
 * declares none, and nothing runs here.
 *
 * <p>{@code rebuild} is the same pass from zero, with the view emptied first. It is what makes a read model
 * disposable: a projection with a bug is fixed by changing the fold and running this, not by patching rows.
 * It holds the lease across the empty <em>and</em> the re-fold, so a worker cannot catch up into a
 * half-empty view.
 *
 * <h2>Why exactly-once needs nothing else here</h2>
 *
 * <p>The checkpoint moves in the view's own transaction, so the pair is atomic: a crash before the commit
 * leaves both untouched, and the next pass reads the same batch again. Nothing is applied twice and nothing
 * is skipped, and there is no idempotency key to get wrong.
 *
 * <p>That guarantee is the transaction's, not this class's, and it is worth knowing exactly where it stops.
 * A projection whose rows are <strong>not</strong> in the same database as the checkpoint — an HTTP search
 * index, a cache, a file — cannot join that transaction, and for those the fold has to be idempotent on
 * {@code globalPosition} instead: record the position with the row and ignore an event at or below what the
 * row already holds. The lease reduces how often that matters; it never removes the need.
 *
 * <h2>Why a lease and not a lock</h2>
 *
 * <p>Exactly one worker should advance a projection, and a lease with an expiry is how that survives the
 * worker dying. What it is <em>not</em> is the thing that makes the work happen once — the transaction
 * above is. A projection is a fold and folds are cheap; the lease is there to stop every replica burning
 * the same log, not to hold the system together.
 */
public final class Projections {

    /**
     * How long a claim is good for. Long enough that a slow batch does not lose it, short enough that a
     * dead worker's projection resumes within a stand-up rather than a support call.
     */
    public static final Duration DEFAULT_LEASE = Duration.ofSeconds(30);

    /**
     * How many events one transaction applies. A batch is one transaction, so this trades how much work a
     * crash repeats against how long a single transaction holds its locks.
     */
    public static final int DEFAULT_BATCH_SIZE = 500;

    private Projections() {
    }

    /**
     * What one pass needs to know beyond the ports themselves.
     *
     * <p>The clock is a supplier, because a pass long enough to need its lease renewed needs the time
     * <em>again</em> — which an instant passed in cannot give it. Everywhere else in this project an
     * instant is a typed input; here the input is the clock itself, and a test hands over a fixed one.
     */
    public record Runner(String owner, Supplier<Instant> clock, Duration ttl, int batchSize) {

        public Runner(String owner, Supplier<Instant> clock) {
            this(owner, clock, DEFAULT_LEASE, DEFAULT_BATCH_SIZE);
        }
    }

    /**
     * What one pass did.
     *
     * <p>{@code leased} is separate from {@code applied} on purpose: "nothing to apply" and "somebody else
     * is already applying it" are both a quiet zero, and a caller that cannot tell them apart will read the
     * first as an empty log and the second as a finished rebuild.
     */
    public record Advance(int applied, boolean leased) {
    }

    /**
     * Apply everything the log has that this projection has not, once.
     *
     * <p>Returns without doing anything if another worker holds the lease — that is the ordinary case for
     * every replica but one, and not a failure.
     */
    public static Advance catchUp(
            EventStore store, CheckpointStore checkpoints, Projection projection, Runner runner) {
        Optional<CheckpointStore.Lease> claimed =
                checkpoints.claim(projection.name(), runner.owner(), runner.clock().get(), runner.ttl());
        if (claimed.isEmpty()) {
            return new Advance(0, false);
        }
        CheckpointStore.Lease lease = claimed.get();
        try {
            return new Advance(applyFromTheCheckpoint(store, checkpoints, projection, lease, runner), true);
        } finally {
            checkpoints.release(lease);
        }
    }

    /**
     * One pass over every projection there is, which is what a scheduled worker calls.
     *
     * <p>No projection's failure hides another's. Each is attempted, the advances are reported by name, and
     * a pass with failures ends by throwing one exception carrying all of them — so the framework's
     * scheduler logs it, the next tick tries again, and a projection whose fold is broken does not quietly
     * starve every projection after it in the list.
     *
     * <p>Order is the iteration order it was given. It does not matter to correctness: each projection has
     * its own checkpoint and its own lease.
     */
    // Catching RuntimeException is exactly what this method is for, which is why the rule against it is
    // lifted here and nowhere else in the project. Nothing is swallowed: every failure leaves in the
    // exception below, and the rule exists to stop a broad catch hiding one — not to make a pass over
    // independent projections stop at the first.
    @SuppressWarnings("PMD.AvoidCatchingGenericException")
    public static Map<String, Advance> catchUpEach(
            EventStore store,
            CheckpointStore checkpoints,
            Iterable<Projection> projections,
            Runner runner) {
        Map<String, Advance> advances = new LinkedHashMap<>();
        List<RuntimeException> failures = new ArrayList<>();
        for (Projection projection : projections) {
            try {
                advances.put(projection.name(), catchUp(store, checkpoints, projection, runner));
            } catch (RuntimeException failure) {
                failures.add(failure);
            }
        }
        if (!failures.isEmpty()) {
            throw new PassFailed(failures);
        }
        return advances;
    }

    /**
     * What a pass throws when one or more projections failed: the first as the cause, the rest suppressed.
     *
     * <p>One exception rather than the first one raw, because "the pass failed, here is everything that
     * went wrong in it" is what somebody reading the log needs — and losing the second failure to the
     * first is how a second bug survives a release.
     */
    public static final class PassFailed extends RuntimeException {

        private static final long serialVersionUID = 1L;

        PassFailed(List<RuntimeException> failures) {
            super(failures.size() + " projection(s) failed to catch up", failures.get(0));
            failures.subList(1, failures.size()).forEach(this::addSuppressed);
        }
    }

    /**
     * Empty the view, put its checkpoint back to zero, and fold the whole log into it again.
     *
     * <p>The reset and the checkpoint go back together, in one transaction, because a view emptied without
     * its checkpoint is a permanently empty view and a checkpoint reset without its view is a doubled one.
     */
    public static Advance rebuild(
            EventStore store, CheckpointStore checkpoints, Projection projection, Runner runner) {
        Optional<CheckpointStore.Lease> claimed =
                checkpoints.claim(projection.name(), runner.owner(), runner.clock().get(), runner.ttl());
        if (claimed.isEmpty()) {
            return new Advance(0, false);
        }
        CheckpointStore.Lease lease = claimed.get();
        try {
            store.inUnitOfWork(() -> {
                projection.reset();
                checkpoints.record(projection.name(), CheckpointStore.FROM_THE_BEGINNING);
            });
            return new Advance(applyFromTheCheckpoint(store, checkpoints, projection, lease, runner), true);
        } finally {
            checkpoints.release(lease);
        }
    }

    /**
     * Batch after batch until the log runs out, holding the lease throughout.
     *
     * <p>The checkpoint is re-read each time round rather than tracked in a local, so a batch that rolled
     * back is read again instead of being skipped by a variable the database never agreed with.
     */
    private static int applyFromTheCheckpoint(
            EventStore store,
            CheckpointStore checkpoints,
            Projection projection,
            CheckpointStore.Lease lease,
            Runner runner) {
        int applied = 0;
        while (true) {
            long position = checkpoints.positionOf(projection.name());
            List<CommittedEvent> batch = take(store, position, runner.batchSize());
            if (batch.isEmpty()) {
                return applied;
            }

            store.inUnitOfWork(() -> {
                projection.apply(batch);
                // The next position, not the last one applied: what positionOf promises is where to
                // resume, and an off-by-one here re-applies one event forever.
                checkpoints.record(projection.name(), batch.get(batch.size() - 1).globalPosition() + 1);
            });
            applied += batch.size();

            if (batch.size() < runner.batchSize()) {
                return applied;
            }
            Optional<CheckpointStore.Lease> renewed = checkpoints.claim(
                    lease.projection(), lease.owner(), runner.clock().get(), runner.ttl());
            if (renewed.isEmpty()) {
                // The lease lapsed mid-pass and somebody else took it: stop where the checkpoint is, which
                // the new owner will read. Losing a lease is not an error — it is a slow pass.
                return applied;
            }
        }
    }

    /** The first {@code count} events of a replay, and no more of the log read than that. */
    private static List<CommittedEvent> take(EventStore store, long fromPosition, int count) {
        List<CommittedEvent> batch = new ArrayList<>(count);
        store.readAll(fromPosition, event -> {
            batch.add(event);
            return batch.size() < count;
        });
        return batch;
    }
}
