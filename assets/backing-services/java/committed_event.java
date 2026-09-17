package com.example.deliverystarter.application.ports.events;

import java.util.Map;
import java.util.Optional;

/**
 * What the store gives back: the event, plus the facts only the store knows.
 *
 * <p>Composition rather than inheritance — a record cannot extend one — with the envelope's own fields
 * delegated so a caller reads {@code event.type()} rather than {@code event.event().type()}.
 *
 * @param event the fact as the domain decided it
 * @param version this event's position within its own stream, counting from zero
 * @param globalPosition its position across every stream, which is the order a rebuild replays in
 * @param recordedAt storage time, as an ISO-8601 instant. When the store saw it, not when it happened.
 */
public record CommittedEvent(DomainEvent event, int version, long globalPosition, String recordedAt) {

    public String type() {
        return event.type();
    }

    public int schemaVersion() {
        return event.schemaVersion();
    }

    public String streamId() {
        return event.streamId();
    }

    public Map<String, Object> payload() {
        return event.payload();
    }

    public String occurredAt() {
        return event.occurredAt();
    }

    public Actor actor() {
        return event.actor();
    }

    public CorrelationId correlationId() {
        return event.correlationId();
    }

    public Optional<CausationId> causationId() {
        return event.causationId();
    }
}
