package com.example.deliverystarter.application.ports.events;

import java.util.UUID;

/**
 * The message that directly caused an event.
 *
 * <p>A <strong>UUID</strong>, for the same reasons as {@link CorrelationId}, and a different type from it so
 * that passing one where the other belongs does not compile.
 *
 * <p>The rule, from Greg Young: responding to a message, you copy its correlation id as your own and take
 * its id as your causation id. The first event of a business transaction has no cause to point at, which is
 * why {@link DomainEvent} holds this as an {@code Optional} rather than inventing one.
 *
 * @param value the id itself
 */
public record CausationId(UUID value) {

    public CausationId {
        if (value == null) {
            throw new IllegalArgumentException("a causation id cannot be null");
        }
    }

    /**
     * Parse one that arrived as text — from a header, a queue message, or a stored row.
     *
     * @param raw the id in text form
     * @return the parsed id
     * @throws IllegalArgumentException when raw is not a UUID
     */
    public static CausationId of(String raw) {
        if (raw == null) {
            throw new IllegalArgumentException("a causation id must be a UUID, and null is not");
        }
        try {
            return new CausationId(UUID.fromString(raw));
        } catch (IllegalArgumentException cause) {
            throw new IllegalArgumentException(
                    "a causation id must be a UUID, and '" + raw + "' is not", cause);
        }
    }

    @Override
    public String toString() {
        return value.toString();
    }
}
