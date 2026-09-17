package com.example.deliverystarter.application.ports.events;

import java.util.List;

/**
 * How an adapter learns what to index an event by.
 *
 * <p>A function, so a project's tagging rule is testable without a database — and everything below this
 * line in the port is the <strong>Dynamic Consistency Boundary</strong>, which is additive. A stream and its
 * expected version remain the default boundary, and every slice generated so far uses nothing else. The
 * factory's {@code docs/adr/0001-a-dcb-capable-log.md} records why the log carries both.
 *
 * <p>Tags are <strong>derived, never modelled</strong>: nothing in {@code docs/event-model/model.yaml} names
 * one, because a tag is a technical index over the log and not a fact about the business. A project's own
 * tagging function is where it decides what its events are findable by — usually the identifying attributes
 * of the payload, alongside the stream:
 *
 * <pre>{@code
 * TagsOf tagsOf = event -> {
 *     List<String> tags = new ArrayList<>(List.of(TagsOf.streamTag(event.streamId())));
 *     if (event.payload().get("courseId") instanceof String courseId) {
 *         tags.add("course:" + courseId);
 *     }
 *     return tags;
 * };
 * }</pre>
 *
 * <p>Pass it to the adapter's constructor. Changing it later is safe and cheap — the index is derived, so
 * {@code retag} rebuilds it from the log — which is the whole reason tags live in an index of their own
 * rather than on the event row.
 */
@FunctionalInterface
public interface TagsOf {

    /** What this event is indexed by. */
    List<String> tagsOf(DomainEvent event);

    /**
     * The tag every event carries by default: its own stream, as a tag.
     *
     * <p>A method rather than an inlined string because it is the one place the correspondence between the
     * two boundaries is spelled: a stream id <em>is</em> a tag, so a log that indexes tags indexes the
     * streams it already had, and stream-per-aggregate is the case where every event carries exactly one.
     */
    static String streamTag(String streamId) {
        return "stream:" + streamId;
    }

    /** What an event is indexed by, unless this project says otherwise. */
    static TagsOf byStream() {
        return event -> List.of(streamTag(event.streamId()));
    }
}
