package com.example.deliverystarter.application.ports.events;

/**
 * The outcome of an append: appended, or refused because the stream had moved.
 *
 * <p>A sealed interface rather than a status field, so the two cases carry different data and a caller that
 * forgets one does not compile. {@code Appended} knows the new head version; {@code VersionConflict} knows
 * where the stream really was, which is what the caller needs in order to re-read and re-decide.
 *
 * <p>A version conflict is a <strong>value, not an exception</strong>. See {@link EventStoreException} for
 * why that distinction is load-bearing rather than stylistic.
 */
public sealed interface AppendResult {

    /** The append succeeded, ending at {@code version}. */
    record Appended(int version) implements AppendResult {
    }

    /** The append was refused: the stream was at {@code actualVersion}, not where the caller thought. */
    record VersionConflict(int actualVersion) implements AppendResult {
    }

    static AppendResult appended(int version) {
        return new Appended(version);
    }

    static AppendResult versionConflict(int actualVersion) {
        return new VersionConflict(actualVersion);
    }
}
