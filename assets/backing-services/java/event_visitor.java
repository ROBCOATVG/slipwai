package com.example.deliverystarter.application.ports.events;

/** What {@link EventStore#readAll} calls for each event, in global-position order. */
@FunctionalInterface
public interface EventVisitor {

    /**
     * Handle one event.
     *
     * @return false to stop the replay, true to continue
     */
    boolean visit(CommittedEvent event);
}
