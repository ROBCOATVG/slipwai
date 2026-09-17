```java
/**
 * The port, in the application layer, owned by its consumer.
 *
 * <p>Typed to one aggregate's event family E. One physical store holds many stream types; the adapter
 * parses stored JSON into E on read, so each typed {@code EventStore<E>} is a view over the streams of
 * that family. Nothing here names SQL, a driver or a framework: that is the whole point of a port, and it
 * is what lets the same contract suite run against a map and against Postgres.
 */
public interface EventStore<E> {

    Stream<E> readStream(String streamId);

    AppendOutcome appendToStream(String streamId, List<E> events, int expectedVersion);

    /** The events, and the version the read saw — which is what the next append asserts against. */
    record Stream<E>(List<E> events, int version) { }

    /**
     * A version conflict is a value, not an exception. Contention is expected under load: the caller
     * re-reads and re-decides. On the error path, the next reader cannot tell it from a dead connection.
     */
    enum AppendOutcome { APPENDED, VERSION_CONFLICT }
}
```
