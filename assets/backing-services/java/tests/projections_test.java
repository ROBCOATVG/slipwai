package com.example.deliverystarter.projections;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.deliverystarter.adapters.driven.checkpointstorememory.InMemoryCheckpointStore;
import com.example.deliverystarter.adapters.driven.eventstorememory.InMemoryEventStore;
import com.example.deliverystarter.application.ports.events.Actor;
import com.example.deliverystarter.application.ports.events.CommittedEvent;
import com.example.deliverystarter.application.ports.events.CorrelationId;
import com.example.deliverystarter.application.ports.events.DomainEvent;
import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.readmodels.CheckpointStore;
import com.example.deliverystarter.application.ports.readmodels.Projection;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Supplier;
import org.junit.jupiter.api.Test;

/**
 * The catch-up runner.
 *
 * <p>Against the in-memory pair, and only that pair, because the runner has no I/O of its own: it is two
 * ports and a loop, and what these cases are about is the loop. That is also why it is here rather than
 * beside an adapter — a project that chose the in-memory store still gets every one of these.
 *
 * <p>The guarantee the runner <em>rests</em> on — that a checkpoint recorded in a failed unit of work does
 * not move — is proved in {@code CheckpointStoreContract}, which runs against every store adapter this
 * project has, where a rollback is the database's own rather than a restored copy. Split that way
 * deliberately: the transaction is the adapters' promise, and the loop is what this file holds to it.
 */
class ProjectionsTest {

    private static final Instant NOW = Instant.parse("2026-09-10T12:00:00Z");

    private final InMemoryEventStore store = new InMemoryEventStore();
    private final CheckpointStore checkpoints = new InMemoryCheckpointStore(store);
    private final Titles view = new Titles("titles");

    /**
     * A read model with somewhere to put the result, which is all a projection is.
     *
     * <p>Its rows are <strong>derived</strong>: every one of them comes from an event, so {@code reset} plus
     * a replay reproduces it exactly. A field this class alone knew — a flag it set when it processed a row
     * — could not survive {@code reset}, and finding that out during an incident is how a rebuild becomes
     * data loss.
     */
    private static class Titles implements Projection {

        private final String projectionName;
        /** Empty rather than null: this project's null analysis refuses a null argument, and is right to. */
        private final Optional<RuntimeException> failure;
        final List<String> rows = new ArrayList<>();
        int batches;

        Titles(String name) {
            this.projectionName = name;
            this.failure = Optional.empty();
        }

        Titles(String name, RuntimeException failure) {
            this.projectionName = name;
            this.failure = Optional.of(failure);
        }

        @Override
        public String name() {
            return projectionName;
        }

        @Override
        public void apply(List<CommittedEvent> batch) {
            batches++;
            batch.forEach(event -> rows.add(event.type()));
            failure.ifPresent(broken -> {
                throw broken;
            });
        }

        @Override
        public void reset() {
            rows.clear();
        }
    }

    private static Supplier<Instant> clockAt(Instant instant) {
        return () -> instant;
    }

    private static Projections.Runner runner(String owner, Instant instant) {
        return new Projections.Runner(owner, clockAt(instant));
    }

    private void givenALogOf(String... types) {
        String stream = "projection-" + UUID.randomUUID();
        CorrelationId correlationId = new CorrelationId(UUID.randomUUID());
        List<DomainEvent> batch = new ArrayList<>();
        for (String type : types) {
            batch.add(new DomainEvent(
                    type,
                    1,
                    stream,
                    java.util.Map.of(),
                    "2024-01-01T00:00:00.000000+00:00",
                    new Actor("test", "projections"),
                    correlationId));
        }
        store.append(stream, EventStore.NO_STREAM, batch);
    }

    @Test
    void appliesTheWholeLogAndLeavesTheCheckpointPastIt() {
        givenALogOf("Placed", "Paid");

        Projections.Advance advance =
                Projections.catchUp(store, checkpoints, view, runner("worker-1", NOW));

        assertThat(advance).isEqualTo(new Projections.Advance(2, true));
        assertThat(view.rows).containsExactly("Placed", "Paid");
        assertThat(checkpoints.positionOf("titles")).isEqualTo(3);
    }

    @Test
    void resumesFromTheCheckpointAndAppliesNothingTwice() {
        givenALogOf("Placed");
        Projections.catchUp(store, checkpoints, view, runner("worker-1", NOW));

        givenALogOf("Paid");
        Projections.Advance again =
                Projections.catchUp(store, checkpoints, view, runner("worker-1", NOW));

        assertThat(again.applied()).isEqualTo(1);
        assertThat(view.rows).containsExactly("Placed", "Paid");
    }

    @Test
    void saysAPassHadNothingToDoWithoutTouchingTheView() {
        Projections.Advance advance =
                Projections.catchUp(store, checkpoints, view, runner("worker-1", NOW));

        assertThat(advance).isEqualTo(new Projections.Advance(0, true));
        assertThat(view.batches).isZero();
    }

    /**
     * Each batch is one transaction, so the size trades how much work a crash repeats against how long one
     * transaction holds its locks. That it batches at all is what keeps a rebuild over a long log from
     * materialising the whole thing.
     */
    @Test
    void appliesALongLogInBatchesOfTheSizeItWasGiven() {
        givenALogOf("One", "Two", "Three", "Four", "Five");

        Projections.Advance advance = Projections.catchUp(store, checkpoints, view,
                new Projections.Runner("worker-1", clockAt(NOW), Projections.DEFAULT_LEASE, 2));

        assertThat(advance.applied()).isEqualTo(5);
        assertThat(view.batches).isEqualTo(3);
    }

    /**
     * The ordinary case for every replica but one, and not a failure — which is why {@code leased} is
     * reported separately from {@code applied}.
     */
    @Test
    void doesNothingInASecondWorkerWhileTheFirstHoldsTheLease() {
        givenALogOf("Placed");
        checkpoints.claim("titles", "worker-1", NOW, Duration.ofSeconds(30));

        Projections.Advance blocked = Projections.catchUp(
                store, checkpoints, view, runner("worker-2", NOW.plusSeconds(1)));

        assertThat(blocked).isEqualTo(new Projections.Advance(0, false));
        assertThat(view.rows).isEmpty();
    }

    @Test
    void takesOverInAnotherWorkerOnceTheLeaseHasLapsed() {
        givenALogOf("Placed");
        checkpoints.claim("titles", "worker-1", NOW, Duration.ofSeconds(30));

        Projections.Advance taken = Projections.catchUp(
                store, checkpoints, view, runner("worker-2", NOW.plusSeconds(300)));

        assertThat(taken).isEqualTo(new Projections.Advance(1, true));
    }

    @Test
    void releasesTheLeaseWhenThePassIsDone() {
        givenALogOf("Placed");

        Projections.catchUp(store, checkpoints, view, runner("worker-1", NOW));

        assertThat(checkpoints.claim("titles", "worker-2", NOW, Duration.ofSeconds(30))).isPresent();
    }

    /**
     * Exactly-once, and there is no idempotency key in it: the checkpoint moves in the same transaction as
     * the rows, so a crash before the commit leaves both untouched and the next pass reads the same batch
     * again.
     */
    @Test
    void movesNeitherTheViewNorTheCheckpointWhenABatchFails() {
        givenALogOf("Placed");
        Titles broken = new Titles("broken", new IllegalStateException("the view write failed"));

        assertThatThrownBy(() -> Projections.catchUp(store, checkpoints, broken, runner("worker-1", NOW)))
                .hasMessage("the view write failed");

        assertThat(checkpoints.positionOf("broken")).isEqualTo(CheckpointStore.FROM_THE_BEGINNING);
    }

    /** Otherwise one bad batch costs a whole lease before anything tries again — every time. */
    @Test
    void releasesTheLeaseEvenWhenThePassFails() {
        givenALogOf("Placed");
        Titles broken = new Titles("broken", new IllegalStateException("the view write failed"));

        assertThatThrownBy(() -> Projections.catchUp(store, checkpoints, broken, runner("worker-1", NOW)))
                .isInstanceOf(IllegalStateException.class);

        assertThat(checkpoints.claim("broken", "worker-2", NOW, Duration.ofSeconds(30))).isPresent();
    }

    /**
     * What a scheduled pass does: every projection, each under its own checkpoint and its own lease.
     */
    @Test
    void catchesUpEveryProjectionInOnePass() {
        givenALogOf("Placed", "Paid");
        Titles other = new Titles("also-titles");

        var advances = Projections.catchUpEach(
                store, checkpoints, List.of(view, other), runner("worker-1", NOW));

        assertThat(advances)
                .containsEntry("titles", new Projections.Advance(2, true))
                .containsEntry("also-titles", new Projections.Advance(2, true));
        assertThat(view.rows).containsExactly("Placed", "Paid");
        assertThat(other.rows).containsExactly("Placed", "Paid");
    }

    /**
     * One broken fold must not starve the projections after it in the list.
     *
     * <p>The scheduler runs this on a timer, so a projection that throws every pass would otherwise stop
     * every projection registered after it — permanently, and with nothing in the log to say which one was
     * at fault. Every projection is attempted, and the pass then fails loudly with all of it.
     */
    @Test
    void appliesTheOtherProjectionsWhenOneOfThemFails() {
        givenALogOf("Placed");
        Titles broken = new Titles("broken", new IllegalStateException("the view write failed"));

        assertThatThrownBy(() ->
                        Projections.catchUpEach(
                                store, checkpoints, List.of(broken, view), runner("worker-1", NOW)))
                .isInstanceOf(Projections.PassFailed.class)
                .hasMessageContaining("1 projection(s)")
                .hasRootCauseMessage("the view write failed");

        assertThat(view.rows).containsExactly("Placed");
    }

    /**
     * What makes a read model disposable, and therefore what makes a projection bug fixable by changing the
     * fold rather than by patching rows.
     */
    @Test
    void aRebuildEmptiesTheViewAndFoldsTheWholeLogIntoItAgain() {
        givenALogOf("Placed", "Paid");
        Projections.catchUp(store, checkpoints, view, runner("worker-1", NOW));
        view.rows.add("something nothing derived");

        Projections.Advance rebuilt =
                Projections.rebuild(store, checkpoints, view, runner("worker-1", NOW));

        assertThat(rebuilt).isEqualTo(new Projections.Advance(2, true));
        assertThat(view.rows).containsExactly("Placed", "Paid");
    }

    /**
     * A rebuild is destructive, so "somebody else is advancing this" has to be distinguishable from "there
     * was nothing to apply". {@code leased} is that distinction.
     */
    @Test
    void aRebuildThatCannotTakeTheLeaseLeavesTheViewAlone() {
        givenALogOf("Placed");
        Projections.catchUp(store, checkpoints, view, runner("worker-1", NOW));
        checkpoints.claim("titles", "worker-1", NOW, Duration.ofSeconds(30));

        Projections.Advance refused = Projections.rebuild(
                store, checkpoints, view, runner("worker-2", NOW.plusSeconds(1)));

        assertThat(refused).isEqualTo(new Projections.Advance(0, false));
        assertThat(view.rows).hasSize(1);
    }
}
