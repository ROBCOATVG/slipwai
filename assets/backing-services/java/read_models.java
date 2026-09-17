package com.example.deliverystarter.application.ports.readmodels;

import java.time.Duration;
import java.time.Instant;
import java.util.Optional;

/**
 * Where each projection has got to, and who is allowed to advance it.
 *
 * <p>The write side of this project arrives finished — a port, its adapters, one contract suite. This is
 * the other half, and it exists because the half that was missing is the half that gets invented badly: a
 * read model folded in the request because that was the only read path already built.
 *
 * <p><strong>A checkpoint is only a checkpoint if it commits with the rows it describes.</strong>
 * Everything here is shaped by that one sentence: {@code record} never commits on its own, and
 * {@code Projections} calls it inside {@code EventStore.inUnitOfWork}, so the position and the view move
 * together or neither moves. Record it separately and you have chosen, without noticing, between losing
 * updates and applying them twice.
 *
 * <p>Every adapter is built from whatever answers "which transaction am I in" for the store it follows:
 * the in-memory one from the store's own database, a file-backed one from its connection, a
 * server-backed one from the framework's {@code Transactions}. Deliberately, and it is the same
 * requirement in every shape:
 * {@code record} has to land in the same transaction as the view write, and two adapters on two
 * connections cannot do that however carefully they are called.
 *
 * <p>{@code docs/event-model/README.md} says which of the three lifecycles — live, inline, async — a
 * slice's read model uses, and {@code make check-model} makes a slice say so before it can be planned.
 * This interface is what async is built from, and {@code inUnitOfWork} is what inline is built from.
 */
public interface CheckpointStore {

    /**
     * Where a projection that has never run starts. The position is the <em>next</em> global position to
     * apply, so zero means "the whole log", and a rebuild is a record of zero followed by a catch-up.
     */
    long FROM_THE_BEGINNING = 0;

    /**
     * The right to advance one projection, held by one worker until it expires.
     *
     * <p>An expiry rather than a lock, because the failure to survive is a worker that dies holding it: a
     * lock nothing releases is a projection that never advances again, and the first anybody hears of it is
     * a stale view. A lease that lapses is a projection that resumes on its own.
     *
     * <p>The lease is an <strong>efficiency measure, not a correctness one</strong>. Two workers holding it
     * at once would each apply events inside a unit of work, and the checkpoint moving in the same
     * transaction is what makes the loser's work a no-op rather than a duplicate. The lease is what stops
     * that being the normal case.
     */
    record Lease(String projection, String owner, Instant expiresAt) {
    }

    /**
     * The next global position this projection has not yet applied.
     *
     * <p>{@link #FROM_THE_BEGINNING} for a projection nothing has recorded — an unknown projection is one
     * that has consumed nothing, not an error, because a rebuild has to be expressible without a special
     * case.
     */
    long positionOf(String projection);

    /**
     * Move the checkpoint. <strong>Does not commit</strong> — the caller's unit of work does.
     *
     * <p>Call it inside the same unit of work as the writes it accounts for, always. It is safe to call
     * outside one, and then it commits on its own, which is exactly the mistake this sentence exists to
     * name.
     */
    void record(String projection, long position);

    /**
     * Take or renew the lease, or empty if somebody else holds an unexpired one.
     *
     * <p>{@code now} is passed in rather than read from a clock, for the reason every instant in this
     * project is: a test that cannot choose the time cannot test expiry without sleeping. The owner already
     * holding the lease always succeeds, which is how a long catch-up renews.
     */
    Optional<Lease> claim(String projection, String owner, Instant now, Duration ttl);

    /**
     * Give the lease up early. A lease held by somebody else is left alone. Releasing is politeness, not
     * correctness: not releasing costs the next worker one {@code ttl}.
     */
    void release(Lease lease);
}
