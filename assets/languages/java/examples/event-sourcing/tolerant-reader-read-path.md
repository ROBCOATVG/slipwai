```java
/**
 * On read: stored JSON, then the version it was written in, then the current shape.
 *
 * <p>Tolerant on purpose. `FAIL_ON_UNKNOWN_PROPERTIES` is off, so a field added by a newer deploy does not
 * break an older reader — that is what makes a rolling deploy possible at all. What is NOT tolerated is a
 * missing required field: only a field that was optional, or one with a proven context-invariant default,
 * may be absent. Anything else is corrupt data, which is a bug rather than a business case, so it throws.
 */
private static final ObjectMapper JSON = JsonMapper.builder()
        .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
        .build();

AccountEvent toDomainEvent(String type, int schemaVersion, String payload) {
    StoredAccountEvent stored = readStored(type, schemaVersion, payload);
    return upcast(stored);   // see the upcaster example for the version dispatch
}

private static StoredAccountEvent readStored(String type, int schemaVersion, String payload) {
    Class<? extends StoredAccountEvent> shape = SHAPES.get(new StoredShape(type, schemaVersion));
    if (shape == null) {
        // An unknown (type, version) pair cannot be guessed at. Naming both is what makes the fix
        // obvious: either add the upcaster, or find out who is writing it.
        throw new IllegalStateException(
                "no reader for %s at schema version %d".formatted(type, schemaVersion));
    }
    try {
        return JSON.readValue(payload, shape);
    } catch (JsonProcessingException failure) {
        throw new IllegalStateException("corrupt %s payload".formatted(type), failure);
    }
}
```
