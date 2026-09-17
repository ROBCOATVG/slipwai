package com.example.deliverystarter.application.ports.readmodels;

import com.example.deliverystarter.application.ports.events.CommittedEvent;
import java.util.List;

/**
 * A read model that is maintained rather than folded per query — inline or async.
 *
 * <p>Three requirements, and the third is the one usually missed:
 *
 * <ul>
 *   <li>{@code name} identifies its checkpoint. Stable for the life of the projection: renaming it
 *       silently starts a second projection at position zero.
 *   <li>{@code apply} folds a batch into whatever the view is kept in. Under async it is called inside
 *       {@code EventStore.inUnitOfWork}, so it must write through the same connection and must not commit;
 *       under inline the append's transaction is the one it joins.
 *   <li>{@code reset} empties the view. Without it the projection is not disposable, and a projection that
 *       cannot be rebuilt is a second source of truth — which is the whole thing an event log exists to
 *       avoid.
 * </ul>
 *
 * <p>Every row a projection writes is <strong>derived</strong>: it comes from the events, and nothing else.
 * A column the projection alone knows — a {@code doneAt} the worker stamps when it processes the row —
 * cannot survive {@code reset}, and finding that out during an incident is how a rebuild becomes data loss.
 * Where a value like that is needed, it belongs in an event.
 */
public interface Projection {

    String name();

    void apply(List<CommittedEvent> batch);

    void reset();
}
