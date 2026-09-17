package com.example.deliverystarter.application.ports.events;

/**
 * The guard on a conditional append: {@code query} must have matched nothing after {@code after}.
 *
 * <p>{@code after} is the {@code head} of the {@link TaggedRead} the decision was made from. The pair is the
 * boundary — dynamic because the caller draws it per decision, out of tags, rather than inheriting it from
 * how streams were laid out months earlier.
 */
public record Condition(TagQuery query, long after) {
}
