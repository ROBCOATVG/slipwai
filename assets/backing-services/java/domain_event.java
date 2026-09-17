package com.example.deliverystarter.application.ports.events;

import java.util.Map;
import java.util.Optional;

/**
 * A fact the domain decided on, before any store has seen it.
 *
 * <p>The payload is copied on construction, so an event cannot be edited through the map the caller still
 * holds. An event is a fact: the whole model depends on it being unchangeable once decided.
 *
 * @param type the event's name, in the domain's own vocabulary
 * @param schemaVersion which version of this event's shape the payload is written in
 * @param streamId the stream this event belongs to, which is the concurrency boundary
 * @param payload the event's own data
 * @param occurredAt domain time, as an ISO-8601 instant. Taken from a clock at the edge and passed in as a
 *     typed input — the domain never reads the clock, which is what makes a decision function testable
 *     without freezing global time. Distinct from {@link CommittedEvent#recordedAt()}, and conflating the
 *     two is how clock problems become unreconcilable.
 * @param actor who caused it
 * @param correlationId what wider piece of work this belongs to
 * @param causationId the event that caused this one, and empty when nothing did — the first event of a
 *     business transaction has no cause to point at, and inventing one would be a lie about the shape of
 *     the tree
 */
public record DomainEvent(
        String type,
        int schemaVersion,
        String streamId,
        Map<String, Object> payload,
        String occurredAt,
        Actor actor,
        CorrelationId correlationId,
        Optional<CausationId> causationId) {

    public DomainEvent {
        payload = EventStore.copyPayload(payload);
        if (causationId == null) {
            throw new IllegalArgumentException(
                    "causationId is Optional.empty() when nothing caused this event, never null");
        }
    }

    /** An event nothing caused, which is where a business transaction starts. */
    public DomainEvent(
            String type,
            int schemaVersion,
            String streamId,
            Map<String, Object> payload,
            String occurredAt,
            Actor actor,
            CorrelationId correlationId) {
        this(type, schemaVersion, streamId, payload, occurredAt, actor, correlationId, Optional.empty());
    }

    /** The same event, bound to a stream — what an adapter does before writing a batch. */
    public DomainEvent inStream(String stream) {
        return new DomainEvent(
                type, schemaVersion, stream, payload, occurredAt, actor, correlationId, causationId);
    }
}
