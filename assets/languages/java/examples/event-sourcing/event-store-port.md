```java
/**
 * The port, owned by the command handler that uses it. Typed to one aggregate's event family, like a
 * repository — one physical store holds many stream types, and the adapter parses stored JSON into E on
 * read, so each typed EventStore<E> is a view over that family's streams.
 */
public interface EventStore<E> {

    /** The stream's events and the version they were read at. */
    Stream<E> readStream(String streamId);

    /** Appends, asserting the stream has not moved. A conflict is a returned value, never an exception. */
    AppendOutcome appendToStream(String streamId, List<E> events, int expectedVersion);

    record Stream<E>(List<E> events, int version) { }

    enum AppendOutcome { APPENDED, VERSION_CONFLICT }
}
```
