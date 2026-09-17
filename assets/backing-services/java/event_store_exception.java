package com.example.deliverystarter.application.ports.events;

/**
 * A genuine store failure: a lost connection, an unreadable row, a schema version nothing can read.
 *
 * <p>Deliberately NOT what a version conflict comes back as. Contention is expected under load rather than
 * exceptional — the caller re-reads and re-decides — so it is an {@link AppendResult} value. Put it on the
 * error path and the next reader cannot tell ordinary concurrency from a broken database.
 */
public class EventStoreException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public EventStoreException(String message) {
        super(message);
    }

    public EventStoreException(String message, Throwable cause) {
        super(message, cause);
    }
}
