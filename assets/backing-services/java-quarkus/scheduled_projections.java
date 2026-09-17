package com.example.deliverystarter.projections;

import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.readmodels.CheckpointStore;
import com.example.deliverystarter.application.ports.readmodels.Projection;
import io.quarkus.scheduler.Scheduled;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Instance;
import jakarta.inject.Inject;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * What runs an {@code async} read model: the framework's scheduler, ticking a catch-up pass.
 *
 * <p>{@code @Scheduled} is Quarkus' own, so there is no worker loop, no thread to start, no shutdown hook
 * to remember and nothing to keep alive in a container that already knows how. {@code ConcurrentExecution
 * .SKIP} is the one option that matters: a pass slower than the interval must not have a second pass pile
 * up behind it, and skipping is free because the checkpoint means the next tick resumes exactly where this
 * one stopped.
 *
 * <p>Inert until the application has the three beans a pass needs, which in a freshly generated project it
 * does not: an {@link EventStore}, a {@link CheckpointStore}, and at least one {@link Projection}. That is
 * not an oversight — which store this application uses is a composition decision, and a project whose read
 * models are all {@code live} or {@code inline} has nothing to run here. Turning it on is three producers
 * and a projection:
 *
 * <pre>{@code
 * @Produces @ApplicationScoped
 * EventStore eventStore(Transactions transactions) {
 *     return new PostgresEventStore(transactions);
 * }
 *
 * @Produces @ApplicationScoped
 * CheckpointStore checkpoints(Transactions transactions) {
 *     return new PostgresCheckpointStore(transactions);
 * }
 *
 * @ApplicationScoped
 * public class OrdersByCustomer implements Projection { ... }
 * }</pre>
 *
 * <p>Every {@code Projection} bean is picked up, so a slice turns its own view on by existing. Nothing
 * else registers it, and nothing has to be told the list changed.
 *
 * <p>A failed pass is thrown rather than swallowed, and the scheduler logs it — which is why this class
 * needs no logger of its own. {@code Projections.catchUpEach} attempts every projection first, so one
 * broken fold delays nothing but itself.
 */
@ApplicationScoped
public class ScheduledProjections {

    /**
     * This process's identity as a lease holder, for as long as it runs.
     *
     * <p>A UUID rather than a hostname: two replicas in one pod, or a hostname reused by the next
     * container, would be one owner as far as the lease is concerned — and the holder of a lease may always
     * renew it, so two workers sharing a name would both think they held it.
     */
    private final String owner = "worker-" + UUID.randomUUID();

    private final Instance<EventStore> events;
    private final Instance<CheckpointStore> checkpoints;
    private final Instance<Projection> projections;

    @Inject
    ScheduledProjections(
            Instance<EventStore> events,
            Instance<CheckpointStore> checkpoints,
            Instance<Projection> projections) {
        this.events = events;
        this.checkpoints = checkpoints;
        this.projections = projections;
    }

    /**
     * One pass, every {@code projections.every} — a property, so an operator can slow it down without a
     * rebuild, and the value is the lag this project accepts on its async views.
     */
    @Scheduled(every = "{projections.every}", concurrentExecution = Scheduled.ConcurrentExecution.SKIP)
    void catchUp() {
        if (!events.isResolvable() || !checkpoints.isResolvable() || projections.isUnsatisfied()) {
            return;
        }
        List<Projection> all = new ArrayList<>();
        projections.forEach(all::add);
        Projections.catchUpEach(
                events.get(),
                checkpoints.get(),
                all,
                new Projections.Runner(owner, Instant::now));
    }
}
