package com.example.deliverystarter.application.ports.events;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/**
 * The event-store port and the envelope it carries.
 *
 * <p>Five capabilities, and a store that cannot offer all five must not be adopted:
 *
 * <ol>
 *   <li>append with an expected version (optimistic concurrency, one stream at a time)
 *   <li>ordered reads of a single stream
 *   <li>replay from position zero, across all streams
 *   <li>reads by tag query, which return the store head as well as the events
 *   <li>append conditional on a tag query — the same guarantee as (1) over a boundary that is not one
 *       stream
 * </ol>
 *
 * <p>The last two are the <strong>Dynamic Consistency Boundary</strong>, and they are additive: a stream
 * and its expected version remain the default boundary, and every slice generated so far uses nothing
 * else. See {@link TagsOf} for what a tag is and why it is derived rather than modelled.
 *
 * <p>Nothing here names Postgres, SQL, JDBC, Agroal or Quarkus. That matters more than usual on this
 * backend: the framework owns startup and ships a first-party datasource, a migration integration and a
 * health check, and every one of those lives <em>behind</em> this interface in a driven adapter. The port
 * is what makes that swap invisible to the application — which is why "use the framework's integration"
 * and "keep the hexagon" are the same instruction rather than competing ones.
 *
 * <p>Every adapter under {@code adapters/driven} implements it, and one contract suite runs against all of
 * them.
 */
public interface EventStore {

    /**
     * The expected version for a stream that must not exist yet, which is how first-write races are
     * detected.
     */
    int NO_STREAM = -1;

    /** The stream in version order, or an empty list for a stream that does not exist. */
    List<CommittedEvent> read(String streamId);

    /**
     * Append a batch at an expected version.
     *
     * <p>A version conflict comes back as an {@link AppendResult}, never as a thrown exception. Exceptions
     * are for genuine failures — a lost connection, an unreadable row.
     */
    AppendResult append(String streamId, int expectedVersion, List<DomainEvent> events);

    /**
     * Replay across all streams from a global position, in order, stopping when the visitor says so.
     *
     * <p>This exists so read models can be rebuilt from zero — without it they are not disposable, and a
     * projection bug becomes unfixable. A visitor rather than a returned list, so a rebuild over a long log
     * does not materialise the whole thing in memory.
     */
    void readAll(long fromPosition, EventVisitor visit);

    /**
     * Run {@code work} in one transaction, which an append and somebody else's write share.
     *
     * <p>Inside it, {@code append} and {@code appendIf} do <strong>not</strong> commit: returning commits
     * everything once, and a thrown exception rolls all of it back. Outside it they commit themselves,
     * exactly as they always have, so nothing already written needs to know this exists.
     *
     * <p>Two things need it, and they are the same need. A read model materialised <em>inline</em> is
     * written here, so a query can never see an event whose view row is missing — and a failed view write
     * takes the append down with it. A projection maintained <em>asynchronously</em> records its checkpoint
     * here, in the same transaction as the rows it derived, which is what makes it exactly-once rather than
     * approximately-once. A checkpoint committed separately from the view it describes is not a checkpoint;
     * it is a race with a number in it.
     *
     * <p>Nesting is allowed and re-entrant: the outermost call owns the commit. Any other adapter built
     * from this store is inside it, which is why the read-side adapters are constructed from this one.
     *
     * <p>Two shapes of the same method, because a unit of work that produces a value and one that only
     * writes are both ordinary — and the alternative is a {@code return null} at every call site that has
     * nothing to hand back, which this project's null analysis refuses on sight and is right to.
     */
    <T> T inUnitOfWork(Supplier<T> work);

    /** A unit of work that produces nothing: the writes are the point. */
    default void inUnitOfWork(Runnable work) {
        inUnitOfWork(() -> {
            work.run();
            return Boolean.TRUE;
        });
    }

    /**
     * The last global position in the log, or zero when it is empty.
     *
     * <p>The boundary a decision is made against, taken <strong>once</strong> and then handed to every read
     * that decision needs. A command that reads twice and uses the second read's head has promised
     * something it never checked: an event matching the first query could have arrived between the two
     * reads, before that head, and the conditional append would not look for it. Pin it here, pass it as
     * {@code until}, and that mistake has nowhere to happen:
     *
     * <pre>{@code
     * long boundary = store.head();
     * TaggedRead course = store.readTagged(byCourse, 0, boundary);
     * TaggedRead student = store.readTagged(byStudent, 0, boundary);
     * store.appendIf(new Condition(both, boundary), List.of(event));
     * }</pre>
     */
    long head();

    /**
     * The events matching {@code query} in {@code (after, until]}, and the position they are as of.
     *
     * <p>This is the DCB read: what a decision loads. {@code after} is for resuming a long read, not for
     * the guard. {@code until} is the ceiling — zero for none, which is every position, since the log
     * starts at one — and it is what a decision reading twice pins first, so both reads see the same log.
     * The head handed back is what the facts are as of: {@code until} when it is given, the store's head
     * when it is not, and either way it is what a {@link Condition} is built from.
     */
    TaggedRead readTagged(TagQuery query, long after, long until);

    /** The same read with no ceiling, which is what a decision needing one query asks for. */
    default TaggedRead readTagged(TagQuery query, long after) {
        return readTagged(query, after, 0);
    }

    /**
     * Append only if nothing matching {@code condition.query()} was recorded after
     * {@code condition.after()}.
     *
     * <p>The events still name their streams and still land at gapless per-stream versions — the store
     * assigns each one the next version of the stream it names — so {@code read}, {@code folds} and every
     * slice written against {@code append} keep working unchanged. What differs is only what the write is
     * guarded by.
     */
    ConditionalAppendResult appendIf(Condition condition, List<DomainEvent> events);

    /**
     * Index events this store's tagging function has not indexed yet, and report how many.
     *
     * <p>The verb an already-running project needs: applying the migration creates an empty index, and this
     * is what fills it from the history that is already there. Idempotent, so running it twice indexes
     * nothing the second time and a run that died halfway is resumed by running it again.
     */
    int reindexTags(long fromPosition);

    /**
     * Adopt a new tagging function and rebuild the whole index under it, reporting how many events were
     * indexed.
     *
     * <p>Because the index is derived, what a project tags is a decision it can change — unlike the events
     * themselves. Both halves happen together on purpose: an index rebuilt under one function while appends
     * carry on under another is an index that disagrees with itself.
     */
    int retag(TagsOf tagsOf);

    /** The expected version to pass when appending to a stream just read. */
    static int currentVersion(List<CommittedEvent> stream) {
        return stream.isEmpty() ? NO_STREAM : stream.get(stream.size() - 1).version();
    }

    /** An unmodifiable copy that tolerates null values, which {@code Map.copyOf} does not. */
    static Map<String, Object> copyPayload(Map<String, Object> payload) {
        return Collections.unmodifiableMap(new LinkedHashMap<>(payload));
    }
}
