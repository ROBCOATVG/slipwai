package com.example.deliverystarter.application.ports.events;

/**
 * The outcome of a conditional append: recorded, or refused because the condition no longer holds.
 *
 * <p>A sealed interface for the same reason {@link AppendResult} is one, and a conflict is a
 * <strong>value</strong> for the same reason a version conflict is: contention is ordinary, and a caller
 * re-reads and re-decides. This is where the two boundaries agree.
 *
 * <p>Both cases carry the store head as found, so a caller that retries reads from there.
 */
public sealed interface ConditionalAppendResult {

    /** The condition held, and the events are recorded up to {@code head}. */
    record Recorded(long head) implements ConditionalAppendResult {
    }

    /** Something matching the condition was recorded after the position it was anchored to. */
    record ConditionConflict(long head) implements ConditionalAppendResult {
    }

    static ConditionalAppendResult recorded(long head) {
        return new Recorded(head);
    }

    static ConditionalAppendResult conditionConflict(long head) {
        return new ConditionConflict(head);
    }
}
