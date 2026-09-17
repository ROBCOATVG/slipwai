package com.example.deliverystarter.application.ports.events;

import java.util.List;

/**
 * What a decision was made from, and the position it was made at.
 *
 * <p>{@code head} is the store's last global position at the moment of the read — zero for an empty log. It
 * is not a nicety: it is the anchor a {@link Condition} is built from, so "these are the facts I decided
 * on" and "nothing else has happened since" are one round trip rather than two that can disagree.
 *
 * <p>It is also read-your-writes made concrete. A caller that appends and then needs a
 * subscription-maintained view to have caught up can wait for a <em>specific</em> position instead of
 * polling blindly.
 */
public record TaggedRead(List<CommittedEvent> events, long head) {
}
