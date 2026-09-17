package com.example.deliverystarter.checkpointstorecontract;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.deliverystarter.application.ports.events.Actor;
import com.example.deliverystarter.application.ports.events.CorrelationId;
import com.example.deliverystarter.application.ports.events.DomainEvent;
import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.readmodels.CheckpointStore;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * One contract, run against every checkpoint adapter.
 *
 * <p>The infrastructure-free adapters run it in {@code make test}; Postgres runs it in
 * {@code make test-integration}. Two adapters that pass different tests are two different ports wearing one
 * name, and with a checkpoint the day they diverge is the day a projection silently applies an event twice.
 *
 * <p>A subclass supplies the <em>pair</em>, not the checkpoint store alone: every adapter is built from the
 * event store it follows, because {@code record} has to land in the same transaction as the view write it
 * accounts for. A contract that let an adapter be constructed on its own would be a contract that permitted
 * the one mistake this port exists to prevent.
 *
 * <p>Every case works in a freshly named projection, because the table is shared with everything else in
 * the database and a {@code DELETE} between cases would only prove that deletes work.
 */
public abstract class CheckpointStoreContract {

    /** A fixed instant, so expiry is tested by choosing the time rather than by sleeping through it. */
    public static final Instant NOW = Instant.parse("2026-09-10T12:00:00Z");

    private static final Duration A_WHILE = Duration.ofSeconds(30);

    private static final SecureRandom RANDOM = new SecureRandom();

    private final CorrelationId correlationId = new CorrelationId(UUID.randomUUID());

    /**
     * The pair under test: the event store, and the checkpoint store built <em>from it</em>.
     *
     * <p>One method returning both rather than two returning each, deliberately. Two methods can be
     * implemented so that the checkpoint store is built from a different instance of the event store — a
     * different transaction, in other words — and then every case here passes except the one that matters.
     * That is not hypothetical: this contract caught exactly that in its own Postgres subclass.
     */
    protected abstract Stores stores();

    /** An event store and the checkpoint store that shares its transaction. */
    public record Stores(EventStore events, CheckpointStore checkpoints) {
    }

    private CheckpointStore checkpoints() {
        return stores().checkpoints();
    }

    /**
     * An unknown projection has consumed nothing, which is not an error — a rebuild has to be expressible
     * without a special case.
     */
    @Test
    void startsAProjectionNothingHasRecordedAtTheBeginning() {
        assertThat(checkpoints().positionOf(newProjection()))
                .isEqualTo(CheckpointStore.FROM_THE_BEGINNING);
    }

    @Test
    void recordsAPositionAndReadsItBack() {
        CheckpointStore checkpoints = checkpoints();
        String projection = newProjection();

        checkpoints.record(projection, 42);

        assertThat(checkpoints.positionOf(projection)).isEqualTo(42);
    }

    @Test
    void recordsTheSameProjectionTwiceWithoutASecondRow() {
        CheckpointStore checkpoints = checkpoints();
        String projection = newProjection();

        checkpoints.record(projection, 7);
        checkpoints.record(projection, 9);

        assertThat(checkpoints.positionOf(projection)).isEqualTo(9);
    }

    @Test
    void putsAPositionBackToTheBeginningForARebuild() {
        CheckpointStore checkpoints = checkpoints();
        String projection = newProjection();
        checkpoints.record(projection, 99);

        checkpoints.record(projection, CheckpointStore.FROM_THE_BEGINNING);

        assertThat(checkpoints.positionOf(projection)).isEqualTo(CheckpointStore.FROM_THE_BEGINNING);
    }

    /**
     * The whole reason this port exists, and the reason an adapter is built from the same thing the event
     * store's transactions come from: the
     * checkpoint moves in the same transaction as the rows it accounts for, so a crash before the commit
     * leaves both untouched and the next pass reads the same batch again. That is exactly-once, and there is
     * no idempotency key in it.
     */
    @Test
    void doesNotRecordAPositionWrittenInAUnitOfWorkThatFails() {
        Stores stores = stores();
        EventStore store = stores.events();
        CheckpointStore checkpoints = stores.checkpoints();
        String projection = newProjection();
        String stream = "checkpoint-" + randomId();

        assertThatThrownBy(() -> store.inUnitOfWork(() -> {
                    store.append(stream, EventStore.NO_STREAM, List.of(event(stream)));
                    checkpoints.record(projection, 5);
                    throw new IllegalStateException("the view write failed");
                }))
                .hasMessage("the view write failed");

        assertThat(checkpoints.positionOf(projection))
                .isEqualTo(CheckpointStore.FROM_THE_BEGINNING);
        assertThat(store.read(stream)).isEmpty();
    }

    @Test
    void claimsAProjectionForOneOwner() {
        Optional<CheckpointStore.Lease> lease = checkpoints().claim(newProjection(), "worker-1", NOW, A_WHILE);

        assertThat(lease).isPresent();
        assertThat(lease.get().owner()).isEqualTo("worker-1");
        assertThat(lease.get().expiresAt()).isEqualTo(NOW.plus(A_WHILE));
    }

    @Test
    void refusesAClaimWhileSomebodyElseHoldsAnUnexpiredLease() {
        CheckpointStore checkpoints = checkpoints();
        String projection = newProjection();
        checkpoints.claim(projection, "worker-1", NOW, A_WHILE);

        assertThat(checkpoints.claim(projection, "worker-2", NOW.plusSeconds(1), A_WHILE)).isEmpty();
    }

    /** How a pass long enough to outlive its lease keeps it: the holder always succeeds. */
    @Test
    void letsTheOwnerRenewItsOwnLease() {
        CheckpointStore checkpoints = checkpoints();
        String projection = newProjection();
        checkpoints.claim(projection, "worker-1", NOW, A_WHILE);

        Optional<CheckpointStore.Lease> renewed =
                checkpoints.claim(projection, "worker-1", NOW.plusSeconds(10), A_WHILE);

        assertThat(renewed).isPresent();
        assertThat(renewed.get().expiresAt()).isEqualTo(NOW.plusSeconds(10).plus(A_WHILE));
    }

    /**
     * An expiry rather than a lock, because the failure to survive is a worker that dies holding it. A lock
     * nothing releases is a projection that never advances again, and the first anybody hears of it is a
     * stale view.
     */
    @Test
    void letsAnotherOwnerClaimALapsedLease() {
        CheckpointStore checkpoints = checkpoints();
        String projection = newProjection();
        checkpoints.claim(projection, "worker-1", NOW, A_WHILE);

        Optional<CheckpointStore.Lease> taken =
                checkpoints.claim(projection, "worker-2", NOW.plus(A_WHILE).plusSeconds(1), A_WHILE);

        assertThat(taken).isPresent();
        assertThat(taken.get().owner()).isEqualTo("worker-2");
    }

    @Test
    void makesAReleasedLeaseClaimableAtOnce() {
        CheckpointStore checkpoints = checkpoints();
        String projection = newProjection();
        CheckpointStore.Lease lease =
                checkpoints.claim(projection, "worker-1", NOW, A_WHILE).orElseThrow();

        checkpoints.release(lease);

        assertThat(checkpoints.claim(projection, "worker-2", NOW, A_WHILE)).isPresent();
    }

    @Test
    void doesNothingWhenReleasingALeaseSomebodyElseHolds() {
        CheckpointStore checkpoints = checkpoints();
        String projection = newProjection();
        checkpoints.claim(projection, "worker-1", NOW, A_WHILE);

        checkpoints.release(new CheckpointStore.Lease(projection, "worker-2", NOW));

        assertThat(checkpoints.claim(projection, "worker-3", NOW, A_WHILE)).isEmpty();
    }

    /**
     * The two live in one row, and moving one must not move the other: a claim that reset the position
     * would rebuild a projection every time a worker restarted.
     */
    @Test
    void doesNotDisturbThePositionWhenTheLeaseMoves() {
        CheckpointStore checkpoints = checkpoints();
        String projection = newProjection();
        checkpoints.record(projection, 12);

        checkpoints.release(checkpoints.claim(projection, "worker-1", NOW, A_WHILE).orElseThrow());

        assertThat(checkpoints.positionOf(projection)).isEqualTo(12);
    }

    protected final String newProjection() {
        return "contract-" + randomId();
    }

    private DomainEvent event(String streamId) {
        return new DomainEvent(
                "Started",
                1,
                streamId,
                Map.of(),
                "2024-01-01T00:00:00.000000+00:00",
                new Actor("test", "checkpoints"),
                correlationId);
    }

    private static String randomId() {
        byte[] buffer = new byte[8];
        RANDOM.nextBytes(buffer);
        return HexFormat.of().formatHex(buffer);
    }
}
