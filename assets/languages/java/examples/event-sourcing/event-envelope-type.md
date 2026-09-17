```java
/**
 * The envelope: the domain fact, plus everything about it the domain did not decide.
 *
 * @param id unique event id — the idempotency key, and what a later event's causationId points at
 * @param type the event's name as text, so a reader tolerates a type it does not know
 * @param streamId which aggregate instance
 * @param version position within that stream, and the optimistic-concurrency token
 * @param globalPosition position across every stream, which is what subscriptions and projections order by
 * @param recordedAt ISO-8601, assigned by the store
 * @param data the domain payload
 * @param metadata correlation and causation
 */
public record EventEnvelope<T>(
        UUID id,
        String type,
        String streamId,
        int version,
        long globalPosition,
        String recordedAt,
        T data,
        Metadata metadata) {

    /**
     * Both are UUIDs, and wrapped in a type of their own rather than left as bare UUIDs: they sit side by
     * side here and are the same shape underneath, so swapping them is invisible at runtime — and it
     * destroys the one thing they exist for. As distinct types, the swap does not compile.
     *
     * @param correlationId ties one whole business transaction together
     * @param causationId the message that directly caused this event, empty when nothing did
     */
    public record Metadata(CorrelationId correlationId, Optional<CausationId> causationId) { }

    /** @param value the id itself, parsed with UUID.fromString at whatever edge it arrived through */
    public record CorrelationId(UUID value) { }

    /** @param value the id itself */
    public record CausationId(UUID value) { }
}
```
