package com.example.deliverystarter.application.ports.events;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Which events a decision loads, and — as part of a {@link Condition} — which events invalidate it.
 *
 * <p>A disjunction of filters, because the constraint that motivates any of this spans entities: deciding
 * whether a student may subscribe to a course needs the course's events <em>and</em> that student's events,
 * which is two filters and cannot be one. Think of it as the SQL query that fetches exactly the events
 * needed to decide.
 *
 * <p><strong>An empty query matches nothing</strong>, never everything. A condition that matched everything
 * would refuse every concurrent append in the system, and a read that matched everything would quietly
 * become a full replay; both are failures worth being loud about, and neither is what anybody meant to
 * write.
 */
public record TagQuery(List<Filter> filters) {

    /**
     * One conjunction: an event matches when it carries <strong>every</strong> tag named here and, where
     * {@code types} names any, when its type is one of them. A filter naming neither matches nothing.
     */
    public record Filter(List<String> tags, List<String> types) {

        /** A filter on tags alone, which is the common shape. */
        public static Filter withTags(String... tags) {
            return new Filter(List.of(tags), List.of());
        }

        /**
         * Whether one event matches, given the tags it was indexed by.
         *
         * <p>In the port rather than in each adapter because it is the definition, and an adapter that
         * computed it differently in SQL would be a second definition nothing compares. The in-memory
         * adapter uses this directly; the SQL adapters translate it, and the contract suite is what holds
         * the translation to it.
         */
        public boolean matches(CommittedEvent event, List<String> indexed) {
            if (tags.isEmpty() && types.isEmpty()) {
                return false;
            }
            if (!types.isEmpty() && !types.contains(event.type())) {
                return false;
            }
            return indexed.containsAll(tags);
        }
    }

    /** A query of one filter on tags alone, which is the common shape. */
    public static TagQuery tagged(String... tags) {
        return new TagQuery(List.of(Filter.withTags(tags)));
    }

    /** Whether any of this query's filters matches the event. */
    public boolean matches(CommittedEvent event, List<String> indexed) {
        return filters.stream().anyMatch(filter -> filter.matches(event, indexed));
    }

    /** Every tag this query mentions, deduplicated — what an index lookup can narrow on. */
    public Set<String> tags() {
        Set<String> mentioned = new LinkedHashSet<>();
        for (Filter filter : filters) {
            mentioned.addAll(filter.tags());
        }
        return mentioned;
    }
}
