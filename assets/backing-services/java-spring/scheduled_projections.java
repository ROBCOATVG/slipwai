package com.example.deliverystarter.projections;

import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.readmodels.CheckpointStore;
import com.example.deliverystarter.application.ports.readmodels.Projection;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

/**
 * What runs an {@code async} read model: the framework's scheduler, ticking a catch-up pass.
 *
 * <p>{@code @Scheduled} is Spring's own, so there is no worker loop, no thread to start, no shutdown hook
 * to remember and nothing to keep alive in a container that already knows how. {@code fixedDelay} rather
 * than {@code fixedRate} is the one option that matters: the delay is measured from the end of the last
 * pass, so a pass slower than the interval cannot have a second pass pile up behind it — and that costs
 * nothing, because the checkpoint means the next pass resumes exactly where this one stopped.
 *
 * <p>{@code @EnableScheduling} lives here rather than on the application class so that the scheduler is
 * turned on by the file that needs it, and the file that needs it is the one you would delete.
 *
 * <p>Inert until the application has the three beans a pass needs, which in a freshly generated project it
 * does not: an {@link EventStore}, a {@link CheckpointStore}, and at least one {@link Projection}. That is
 * not an oversight — which store this application uses is a composition decision, and a project whose read
 * models are all {@code live} or {@code inline} has nothing to run here. Turning it on is two {@code @Bean}
 * methods and a projection:
 *
 * <pre>{@code
 * @Bean
 * EventStore eventStore(Transactions transactions) {
 *     return new PostgresEventStore(transactions);
 * }
 *
 * @Bean
 * CheckpointStore checkpoints(Transactions transactions) {
 *     return new PostgresCheckpointStore(transactions);
 * }
 *
 * @Component
 * public class OrdersByCustomer implements Projection { ... }
 * }</pre>
 *
 * <p>Every {@code Projection} bean is picked up, so a slice turns its own view on by existing. Nothing else
 * registers it, and nothing has to be told the list changed.
 *
 * <p>A failed pass is thrown rather than swallowed, and the scheduler logs it — which is why this class
 * needs no logger of its own. {@code Projections.catchUpEach} attempts every projection first, so one
 * broken fold delays nothing but itself.
 */
@Configuration
@EnableScheduling
public class ScheduledProjections {

    /**
     * This process's identity as a lease holder, for as long as it runs.
     *
     * <p>A UUID rather than a hostname: two replicas in one pod, or a hostname reused by the next
     * container, would be one owner as far as the lease is concerned — and the holder of a lease may always
     * renew it, so two workers sharing a name would both think they held it.
     */
    private final String owner = "worker-" + UUID.randomUUID();

    private final ObjectProvider<EventStore> events;
    private final ObjectProvider<CheckpointStore> checkpoints;
    private final ObjectProvider<Projection> projections;

    ScheduledProjections(
            ObjectProvider<EventStore> events,
            ObjectProvider<CheckpointStore> checkpoints,
            ObjectProvider<Projection> projections) {
        this.events = events;
        this.checkpoints = checkpoints;
        this.projections = projections;
    }

    /**
     * One pass, every {@code projections.every-ms} — a property, so an operator can slow it down without a
     * rebuild, and the value is the lag this project accepts on its async views.
     */
    @Scheduled(fixedDelayString = "${projections.every-ms}")
    void catchUp() {
        EventStore store = events.getIfAvailable();
        CheckpointStore positions = checkpoints.getIfAvailable();
        List<Projection> all = projections.stream().toList();
        if (store == null || positions == null || all.isEmpty()) {
            return;
        }
        Projections.catchUpEach(store, positions, all, new Projections.Runner(owner, Instant::now));
    }
}
