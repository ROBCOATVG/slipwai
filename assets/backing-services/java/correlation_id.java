package com.example.deliverystarter.application.ports.events;

import java.util.UUID;

/**
 * The whole business transaction an event belongs to.
 *
 * <p>A <strong>UUID</strong>, and typed as one rather than left as a String. It is written by one service
 * and read by another, often years later by a tool nobody has written yet, so the one thing it must be is
 * unambiguous: a UUID is unique without a registry, parses the same everywhere, and cannot quietly become a
 * request path, a customer reference, or an empty string that nothing rejects.
 *
 * <p>A record wrapper rather than a bare {@link UUID}, and a separate type from {@link CausationId}, because
 * the two sit side by side in {@link DomainEvent} and are the same shape underneath. Swapping them is
 * invisible at runtime and destroys the one thing they exist for — a causal tree in which everything appears
 * to have caused itself. As a distinct type, the swap does not compile.
 *
 * @param value the id itself
 */
public record CorrelationId(UUID value) {

    public CorrelationId {
        if (value == null) {
            throw new IllegalArgumentException("a correlation id cannot be null");
        }
    }

    /**
     * Parse one that arrived as text — from a header, a queue message, or a stored row.
     *
     * <p>Parsing at the edge is what keeps the type honest: text is checked once, here, rather than trusted
     * everywhere. {@link UUID#fromString} is the check, and it normalises case, so one id has one spelling
     * whichever service wrote it.
     *
     * @param raw the id in text form
     * @return the parsed id
     * @throws IllegalArgumentException when raw is not a UUID
     */
    public static CorrelationId of(String raw) {
        if (raw == null) {
            throw new IllegalArgumentException("a correlation id must be a UUID, and null is not");
        }
        try {
            return new CorrelationId(UUID.fromString(raw));
        } catch (IllegalArgumentException cause) {
            throw new IllegalArgumentException(
                    "a correlation id must be a UUID, and '" + raw + "' is not", cause);
        }
    }

    @Override
    public String toString() {
        return value.toString();
    }
}
