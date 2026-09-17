package com.example.deliverystarter.eventstorecontract;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.deliverystarter.application.ports.events.Actor;
import com.example.deliverystarter.application.ports.events.AppendResult;
import com.example.deliverystarter.application.ports.events.CausationId;
import com.example.deliverystarter.application.ports.events.CommittedEvent;
import com.example.deliverystarter.application.ports.events.CorrelationId;
import com.example.deliverystarter.application.ports.events.DomainEvent;
import com.example.deliverystarter.application.ports.events.Condition;
import com.example.deliverystarter.application.ports.events.ConditionalAppendResult;
import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.events.TagQuery;
import com.example.deliverystarter.application.ports.events.TaggedRead;
import com.example.deliverystarter.application.ports.events.TagsOf;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * One contract, run against every event-store adapter.
 *
 * <p>The infrastructure-free adapters run it in {@code make test}; Postgres runs it in
 * {@code make test-integration}. Two adapters that pass different tests are two different ports wearing one
 * name, and the day they diverge is the day a slice that worked on the fake stops working in production.
 *
 * <p>An abstract base class rather than a parameterised test, so each adapter's own test class names the
 * adapter it is holding to the contract and can add whatever only that adapter can prove.
 *
 * <p>Nothing here truncates or deletes: the log is append-only, and a real store enforces that with a
 * trigger, so a shared table cannot be cleaned between tests. Every test therefore works in freshly named
 * streams and asserts only about those. That is not a workaround — it is what testing against a real
 * append-only log actually looks like.
 */
public abstract class EventStoreContract {

    private static final SecureRandom RANDOM = new SecureRandom();

    private final String run = randomId();
    private final CorrelationId correlationId = new CorrelationId(UUID.randomUUID());
    private int counter;

    /**
     * Build the adapter under test, indexing each event by what {@code tagsOf} returns for it. Called once
     * per case, so each starts clean where the adapter can be clean and works in fresh streams where it
     * cannot.
     */
    protected abstract EventStore newStore(TagsOf tagsOf);

    /**
     * The store every case uses unless it wants tags: indexed by stream, which is what the port does when
     * a project has not said otherwise.
     */
    protected final EventStore newStore() {
        return newStore(TagsOf.byStream());
    }

    /**
     * A store whose events are findable by their payload's ids as well as their stream — which is the only
     * reason a Dynamic Consistency Boundary can be drawn at all.
     */
    protected final EventStore newTaggedStore() {
        return newStore(PAYLOAD_TAGS);
    }

    /**
     * A tagging function of the shape a real project writes: the stream, plus the identifying attributes
     * of the payload.
     *
     * <p>Tags are derived from the event and nothing else, which is what makes the index rebuildable — so
     * this function is called on the way in <em>and</em> during a reindex, and the contract below proves
     * the two agree.
     */
    protected static final TagsOf PAYLOAD_TAGS = event -> {
        List<String> tags = new ArrayList<>();
        tags.add(TagsOf.streamTag(event.streamId()));
        if (event.payload().get("courseId") instanceof String courseId) {
            tags.add("course:" + courseId);
        }
        if (event.payload().get("studentId") instanceof String studentId) {
            tags.add("student:" + studentId);
        }
        return tags;
    };

    /**
     * What a project that has not adopted tags has: a log with no index over it. Every event already in a
     * running project's log was written by a store that behaved exactly like this.
     */
    protected static final TagsOf NO_TAGS = event -> List.of();

    @Test
    void readsAnUnknownStreamAsEmptyRatherThanFailing() {
        assertThat(newStore().read(newStream())).isEmpty();
    }

    @Test
    void appendsToAStreamThatDoesNotExistYet() {
        EventStore store = newStore();
        String stream = newStream();

        AppendResult result = store.append(
                stream, EventStore.NO_STREAM, List.of(event(stream, "Started"), event(stream, "Continued")));

        assertThat(result).isEqualTo(AppendResult.appended(1));
    }

    @Test
    void returnsTheStreamInVersionOrderWithWhatOnlyTheStoreKnows() {
        EventStore store = newStore();
        String stream = newStream();
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started", Map.of("step", 1)));
        mustAppend(store, stream, 0, event(stream, "Continued", Map.of("step", 2)));

        List<CommittedEvent> recorded = store.read(stream);

        assertThat(recorded).hasSize(2);
        assertThat(recorded.get(0).type()).isEqualTo("Started");
        assertThat(recorded.get(0).version()).isZero();
        assertThat(recorded.get(1).type()).isEqualTo("Continued");
        assertThat(recorded.get(1).version()).isEqualTo(1);
        assertThat(recorded.get(1).globalPosition()).isGreaterThan(recorded.get(0).globalPosition());
        // The value survives the round trip. Compared as text rather than cast to a number, because a
        // JSON round trip may legitimately widen an int to a long and the contract is about the value
        // arriving, not about which numeric box it arrives in.
        assertThat(String.valueOf(recorded.get(0).payload().get("step"))).isEqualTo("1");
        assertThat(recorded.get(0).actor()).isEqualTo(new Actor("test", run));
        assertThat(recorded.get(0).recordedAt()).isNotBlank();
    }

    /**
     * Every adapter stores these ids the way its database can and hands back the same UUIDs. Postgres has a
     * {@code uuid} column, SQLite has text, the in-memory store has neither. The difference stops at the
     * adapter, and it is provable here rather than by reading three implementations.
     */
    @Test
    void roundTripsTheCorrelationAndCausationIdsAsUuids() {
        EventStore store = newStore();
        String stream = newStream();
        CausationId cause = new CausationId(UUID.randomUUID());
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started"), event(stream, "Caused", cause));

        List<CommittedEvent> recorded = store.read(stream);

        assertThat(recorded.get(0).correlationId()).isEqualTo(correlationId);
        // The first event of a transaction has no cause, and the store does not invent one.
        assertThat(recorded.get(0).causationId()).isEmpty();
        assertThat(recorded.get(1).causationId()).contains(cause);
    }

    @Test
    void reportsAStaleExpectedVersionAsAValueNotAnException() {
        EventStore store = newStore();
        String stream = newStream();
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started"));

        // No assertThatThrownBy anywhere in this test, on purpose: the whole point of the contract is that
        // contention comes back as a value the caller can act on.
        AppendResult result =
                store.append(stream, EventStore.NO_STREAM, List.of(event(stream, "Raced")));

        assertThat(result).isEqualTo(AppendResult.versionConflict(0));
    }

    @Test
    void writesNothingWhenTheExpectedVersionIsStale() {
        EventStore store = newStore();
        String stream = newStream();
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started"));

        store.append(
                stream,
                EventStore.NO_STREAM,
                List.of(event(stream, "Rejected"), event(stream, "AlsoRejected")));

        assertThat(typesOf(store.read(stream))).containsExactly("Started");
    }

    @Test
    void continuesAStreamFromTheVersionItReports() {
        EventStore store = newStore();
        String stream = newStream();
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started"));
        List<CommittedEvent> history = store.read(stream);

        assertThat(EventStore.currentVersion(history)).isZero();
        assertThat(store.append(
                        stream, EventStore.currentVersion(history), List.of(event(stream, "Continued"))))
                .isEqualTo(AppendResult.appended(1));
    }

    @Test
    void treatsAnEmptyAppendAsANoOpAtTheExpectedVersion() {
        EventStore store = newStore();
        String stream = newStream();
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started"));

        assertThat(store.append(stream, 0, List.of())).isEqualTo(AppendResult.appended(0));
        assertThat(store.read(stream)).hasSize(1);
    }

    @Test
    void keepsStreamsApart() {
        EventStore store = newStore();
        String one = newStream();
        String other = newStream();
        mustAppend(store, one, EventStore.NO_STREAM, event(one, "Mine"));
        mustAppend(store, other, EventStore.NO_STREAM, event(other, "Theirs"));

        assertThat(typesOf(store.read(one))).containsExactly("Mine");
        assertThat(typesOf(store.read(other))).containsExactly("Theirs");
    }

    @Test
    void replaysAcrossAllStreamsInGlobalPositionOrder() {
        EventStore store = newStore();
        String one = newStream();
        String other = newStream();
        mustAppend(store, one, EventStore.NO_STREAM, event(one, "First"));
        mustAppend(store, other, EventStore.NO_STREAM, event(other, "Second"));
        mustAppend(store, one, 0, event(one, "Third"));

        List<CommittedEvent> replayed = replay(store, 0, one, other);

        assertThat(typesOf(replayed)).containsExactly("First", "Second", "Third");
        for (int index = 1; index < replayed.size(); index++) {
            assertThat(replayed.get(index).globalPosition())
                    .isGreaterThan(replayed.get(index - 1).globalPosition());
        }
    }

    @Test
    void replaysOnlyFromTheRequestedPositionOnward() {
        EventStore store = newStore();
        String stream = newStream();
        mustAppend(
                store,
                stream,
                EventStore.NO_STREAM,
                event(stream, "First"),
                event(stream, "Second"));
        List<CommittedEvent> recorded = store.read(stream);

        List<CommittedEvent> replayed = replay(store, recorded.get(1).globalPosition(), stream);

        assertThat(typesOf(replayed)).containsExactly("Second");
    }

    @Test
    void stopsReplayingWhenTheVisitorSaysSo() {
        EventStore store = newStore();
        String stream = newStream();
        mustAppend(
                store,
                stream,
                EventStore.NO_STREAM,
                event(stream, "First"),
                event(stream, "Second"),
                event(stream, "Third"));

        List<String> seen = new ArrayList<>();
        store.readAll(0, recorded -> {
            if (!recorded.streamId().equals(stream)) {
                return true;
            }
            seen.add(recorded.type());
            return seen.size() < 2;
        });

        assertThat(seen).containsExactly("First", "Second");
    }

    // ── The tag index, and the boundary drawn out of it ─────────────────────────────────────────────
    //
    // Everything below is the Dynamic Consistency Boundary, and it runs against every adapter for the same
    // reason the rest of this file does: a fake that answers a tag query differently from Postgres is a
    // fake that proves nothing about production. The SQL adapters translate TagQuery.Filter.matches into
    // SQL, and these are the cases that hold the translation to the definition.

    @Test
    void indexesEveryEventByItsOwnStreamWithoutBeingAsked() {
        EventStore store = newStore();
        String stream = newStream();
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started"));

        TaggedRead found = store.readTagged(TagQuery.tagged(TagsOf.streamTag(stream)), 0);

        assertThat(typesOf(found.events())).containsExactly("Started");
    }

    @Test
    void reportsTheStoreHeadWithWhatItRead() {
        EventStore store = newTaggedStore();
        String stream = newStream();
        TagQuery query = TagQuery.tagged(TagsOf.streamTag(stream));
        TaggedRead empty = store.readTagged(query, 0);
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started"));

        TaggedRead after = store.readTagged(query, 0);

        assertThat(after.head()).isGreaterThan(empty.head());
        assertThat(after.events().get(after.events().size() - 1).globalPosition())
                .isEqualTo(after.head());
    }

    /**
     * A filter is a conjunction. An "any of these tags" filter would be a much weaker guard than the caller
     * wrote, and the difference is invisible until it lets a write through.
     */
    @Test
    void matchesAnEventOnlyWhenItCarriesEveryTagInAFilter() {
        EventStore store = newTaggedStore();
        String stream = newStream();
        String subject = newSubject();
        mustAppend(store, stream, EventStore.NO_STREAM,
                event(stream, "Subscribed", Map.of("courseId", subject, "studentId", subject)));

        TaggedRead both = store.readTagged(
                TagQuery.tagged("course:" + subject, "student:" + subject), 0);
        TaggedRead oneWrong = store.readTagged(
                TagQuery.tagged("course:" + subject, "student:" + subject + "-nobody"), 0);

        assertThat(typesOf(both.events())).containsExactly("Subscribed");
        assertThat(oneWrong.events()).isEmpty();
    }

    /**
     * The query is a disjunction of conjunctions, because the constraint that motivates any of this spans
     * entities: a course's events <em>and</em> a student's events, which is two filters and cannot be one.
     */
    @Test
    void matchesAnyFilterInTheQuery() {
        EventStore store = newTaggedStore();
        String courseStream = newStream();
        String studentStream = newStream();
        String subject = newSubject();
        mustAppend(store, courseStream, EventStore.NO_STREAM,
                event(courseStream, "CourseCapacitySet", Map.of("courseId", subject)));
        mustAppend(store, studentStream, EventStore.NO_STREAM,
                event(studentStream, "StudentSubscribed", Map.of("studentId", subject)));

        TaggedRead found = store.readTagged(new TagQuery(List.of(
                TagQuery.Filter.withTags("course:" + subject),
                TagQuery.Filter.withTags("student:" + subject))), 0);

        assertThat(typesOf(found.events())).containsExactly("CourseCapacitySet", "StudentSubscribed");
    }

    @Test
    void narrowsAFilterByEventType() {
        EventStore store = newTaggedStore();
        String stream = newStream();
        String subject = newSubject();
        mustAppend(store, stream, EventStore.NO_STREAM,
                event(stream, "Subscribed", Map.of("courseId", subject)),
                event(stream, "Unsubscribed", Map.of("courseId", subject)));

        TaggedRead found = store.readTagged(new TagQuery(List.of(
                new TagQuery.Filter(List.of("course:" + subject), List.of("Unsubscribed")))), 0);

        assertThat(typesOf(found.events())).containsExactly("Unsubscribed");
    }

    /**
     * The dangerous default, refused explicitly. A condition that matched everything would refuse every
     * concurrent append in the system, and a read that matched everything would quietly become a full
     * replay.
     */
    @Test
    void matchesNothingForAnEmptyQueryRatherThanEverything() {
        EventStore store = newTaggedStore();
        String stream = newStream();
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started"));

        assertThat(store.readTagged(new TagQuery(List.of()), 0).events()).isEmpty();
        assertThat(store.readTagged(
                        new TagQuery(List.of(new TagQuery.Filter(List.of(), List.of()))), 0)
                .events())
                .isEmpty();
    }

    @Test
    void appendsConditionallyWhenNothingMatchingArrivedSinceTheRead() {
        EventStore store = newTaggedStore();
        String stream = newStream();
        String subject = newSubject();
        TagQuery query = TagQuery.tagged("course:" + subject);
        long decidedAt = store.readTagged(query, 0).head();

        ConditionalAppendResult result = store.appendIf(
                new Condition(query, decidedAt),
                List.of(event(stream, "Subscribed", Map.of("courseId", subject))));

        assertThat(result).isInstanceOf(ConditionalAppendResult.Recorded.class);
        assertThat(typesOf(store.read(stream))).containsExactly("Subscribed");
    }

    /**
     * The guard {@code expectedVersion} cannot express: the constraint spans two entities, and what
     * invalidates the decision is an event in a stream the decision never named.
     */
    @Test
    void refusesAConditionalAppendWhenAMatchingEventArrivedSince() {
        EventStore store = newTaggedStore();
        String stream = newStream();
        String other = newStream();
        String subject = newSubject();
        TagQuery query = TagQuery.tagged("course:" + subject);
        long decidedAt = store.readTagged(query, 0).head();
        mustAppend(store, other, EventStore.NO_STREAM,
                event(other, "Subscribed", Map.of("courseId", subject)));

        ConditionalAppendResult result = store.appendIf(
                new Condition(query, decidedAt),
                List.of(event(stream, "Subscribed", Map.of("courseId", subject))));

        assertThat(result).isInstanceOf(ConditionalAppendResult.ConditionConflict.class);
        assertThat(store.read(stream)).isEmpty();
    }

    /**
     * The compatibility that makes this additive rather than a fork. A conditional append still lands at
     * the next version of the stream it names, so every slice written against {@code read}, {@code append}
     * and {@code folds} goes on working unchanged.
     */
    @Test
    void leavesAConditionalAppendReadableAsPartOfItsStream() {
        EventStore store = newTaggedStore();
        String stream = newStream();
        String subject = newSubject();
        TagQuery query = TagQuery.tagged("course:" + subject);
        mustAppend(store, stream, EventStore.NO_STREAM,
                event(stream, "Opened", Map.of("courseId", subject)));
        store.appendIf(
                new Condition(query, store.readTagged(query, 0).head()),
                List.of(event(stream, "Subscribed", Map.of("courseId", subject))));

        List<CommittedEvent> stored = store.read(stream);

        assertThat(stored).hasSize(2);
        assertThat(stored.get(0).version()).isZero();
        assertThat(stored.get(1).version()).isEqualTo(1);
        assertThat(store.append(stream, EventStore.currentVersion(stored), List.of()))
                .isEqualTo(AppendResult.appended(1));
    }

    /**
     * What every project generated before tags existed is, and what it stays until it says otherwise: the
     * log, unchanged, with an index over nothing.
     */
    @Test
    void behavesExactlyAsItDidBeforeWhenItIndexesNothing() {
        EventStore store = newStore(NO_TAGS);
        String stream = newStream();

        AppendResult result = store.append(
                stream, EventStore.NO_STREAM, List.of(event(stream, "Started")));

        assertThat(result).isEqualTo(AppendResult.appended(0));
        assertThat(typesOf(store.read(stream))).containsExactly("Started");
        assertThat(store.readTagged(TagQuery.tagged(TagsOf.streamTag(stream)), 0).events()).isEmpty();
    }

    /**
     * The adoption path, as a test rather than as a paragraph.
     *
     * <p>A project already in production applies the migration, which creates an empty index, and runs
     * this. Nothing about the log changes — which is the only reason it is possible at all, since the log
     * refuses to be rewritten.
     *
     * <p>{@code retag} rebuilds the whole index rather than one stream's share of it. Against a shared
     * database that is safe here because every tagging function in this suite returns the stream tag plus
     * more, so a rebuild under one of them satisfies every other case's assumptions as well.
     */
    @Test
    void indexesALogItDidNotIndexWhenTheEventsWereWritten() {
        EventStore store = newStore(NO_TAGS);
        String stream = newStream();
        String subject = newSubject();
        mustAppend(store, stream, EventStore.NO_STREAM,
                event(stream, "Enrolled", Map.of("courseId", subject)),
                event(stream, "Graduated", Map.of("courseId", subject)));
        TagQuery query = TagQuery.tagged("course:" + subject);
        assertThat(store.readTagged(query, 0).events()).isEmpty();

        int indexed = store.retag(PAYLOAD_TAGS);

        assertThat(indexed).isGreaterThanOrEqualTo(2);
        assertThat(typesOf(store.readTagged(query, 0).events()))
                .containsExactly("Enrolled", "Graduated");
        // Idempotent: a second run indexes nothing, so a reindex that died halfway is finished by running
        // it again rather than started over.
        assertThat(store.reindexTags(0)).isZero();
    }

    /**
     * What "indexed" means, which the adapters have to agree on or the number an adoption run reports is a
     * different number in every store.
     *
     * <p>An event this project's tagging function returns nothing for is never findable by tag, so a
     * reindex that counted it would report work it did not do and would never settle at zero. Both halves
     * matter: the in-memory store must not record an empty index entry, which would make the event look
     * indexed to a later run under a real tagging function, and the SQL stores must not count a row they
     * wrote no tags for.
     */
    @Test
    void countsOnlyTheEventsAReindexMadeFindableByTag() {
        EventStore store = newStore(NO_TAGS);
        String stream = newStream();
        String subject = newSubject();
        mustAppend(store, stream, EventStore.NO_STREAM,
                event(stream, "Enrolled", Map.of("courseId", subject)),
                event(stream, "Graduated", Map.of("courseId", subject)));

        assertThat(store.reindexTags(0)).isZero();
    }

    /**
     * The reason {@code head} is a method of its own, and what stops a decision from being made against two
     * different moments.
     *
     * <p>A command that needs two queries — a course's capacity and a student's own subscriptions — reads
     * twice. If each read hands back its own head and the caller guards with the second one, an event
     * matching the <em>first</em> query could have arrived between the two reads, before that head, and the
     * conditional append would never look for it: the guard says "nothing since here" about a position the
     * facts do not cover.
     *
     * <p>Pinning the boundary first and passing it as {@code until} removes the gap. Both reads see the
     * same log, the head handed back is the boundary rather than whatever has happened since, and a
     * {@link Condition} built from it covers exactly the facts it was decided on.
     */
    @Test
    void readsAsOfABoundaryAndNothingAfterIt() {
        EventStore store = newTaggedStore();
        String stream = newStream();
        String subject = newSubject();
        TagQuery query = TagQuery.tagged("course:" + subject);
        mustAppend(store, stream, EventStore.NO_STREAM,
                event(stream, "Enrolled", Map.of("courseId", subject)));

        long boundary = store.head();
        // Somebody else's event, after the boundary this decision was drawn at.
        mustAppend(store, stream, 0, event(stream, "Graduated", Map.of("courseId", subject)));

        TaggedRead asOf = store.readTagged(query, 0, boundary);
        assertThat(typesOf(asOf.events())).containsExactly("Enrolled");
        assertThat(asOf.head()).isEqualTo(boundary);

        // Unbounded, the same query sees both — the ceiling is the caller's decision, not a filter the
        // store applies on its own.
        TaggedRead current = store.readTagged(query, 0);
        assertThat(typesOf(current.events())).containsExactly("Enrolled", "Graduated");
        assertThat(current.head()).isGreaterThanOrEqualTo(boundary);
    }

    /**
     * The one failure that would make the index worse than not having it: an event visible to {@code read}
     * whose tags are not yet visible to {@code readTagged} would let the next conditional append miss the
     * very event that should have refused it.
     */
    @Test
    void makesAnAppendAndItsTagsArriveTogetherOrNotAtAll() {
        EventStore store = newTaggedStore();
        String stream = newStream();
        String subject = newSubject();
        mustAppend(store, stream, EventStore.NO_STREAM,
                event(stream, "Subscribed", Map.of("courseId", subject)));

        assertThat(store.readTagged(TagQuery.tagged("course:" + subject), 0).events())
                .hasSameSizeAs(store.read(stream));
    }

    /**
     * What an inline read model and an async checkpoint are both built on: a write of somebody else's that
     * fails takes the append with it.
     */
    @Test
    void leavesTheLogAsItWasWhenAUnitOfWorkFails() {
        EventStore store = newStore();
        String stream = newStream();

        assertThatThrownBy(() -> store.inUnitOfWork(() -> {
                    store.append(stream, EventStore.NO_STREAM, List.of(event(stream, "Started")));
                    throw new IllegalStateException("the view write failed");
                }))
                .hasMessage("the view write failed");

        assertThat(store.read(stream)).isEmpty();
    }

    @Test
    void commitsEverythingInAUnitOfWorkThatCompletesOnce() {
        EventStore store = newStore();
        String one = newStream();
        String other = newStream();

        // The `Runnable` overload, which is what a unit of work with nothing to hand back is for — and
        // the only case here that exercises it. Writing `return null` instead would be asking the port
        // for something it does not promise: this project's null analysis refuses a null result, and the
        // overload exists so no call site has to write one.
        store.inUnitOfWork(() -> {
            store.append(one, EventStore.NO_STREAM, List.of(event(one, "Mine")));
            store.append(other, EventStore.NO_STREAM, List.of(event(other, "Theirs")));
        });

        assertThat(typesOf(store.read(one))).containsExactly("Mine");
        assertThat(typesOf(store.read(other))).containsExactly("Theirs");
    }

    /**
     * A conflict is a value, so the caller's transaction survives it and goes on to commit what else it was
     * doing. Without a savepoint per nested block, a refused append would either poison the outer
     * transaction or leave its own half-written events inside it.
     */
    @Test
    void writesNothingAndEndsNothingWhenANestedAppendIsRefused() {
        EventStore store = newStore();
        String stream = newStream();
        String other = newStream();
        mustAppend(store, stream, EventStore.NO_STREAM, event(stream, "Started"));

        AppendResult refused = store.inUnitOfWork(() -> {
            AppendResult result = store.append(stream, EventStore.NO_STREAM,
                    List.of(event(stream, "Rejected"), event(stream, "AlsoRejected")));
            store.append(other, EventStore.NO_STREAM, List.of(event(other, "Unaffected")));
            return result;
        });

        assertThat(refused).isEqualTo(AppendResult.versionConflict(0));
        assertThat(typesOf(store.read(stream))).containsExactly("Started");
        assertThat(typesOf(store.read(other))).containsExactly("Unaffected");
    }

    /**
     * The value a case's tags are built from. Unique per case, not per run, because Postgres runs this
     * suite against a database it shares with every other case and every previous run — and a tag is not
     * scoped to a stream, so two cases tagging by the same id would find each other's events.
     */
    protected final String newSubject() {
        counter++;
        return run + "-" + counter;
    }

    /** A fresh stream name per case, so a shared append-only log needs no cleaning between tests. */
    protected final String newStream() {
        counter++;
        return "contract-" + run + "-" + counter;
    }

    /** An event in this run's own vocabulary, with every envelope field populated. */
    protected final DomainEvent event(String streamId, String type) {
        return event(streamId, type, Map.of());
    }

    protected final DomainEvent event(String streamId, String type, Map<String, Object> payload) {
        return new DomainEvent(
                type,
                1,
                streamId,
                payload,
                "2024-01-01T00:00:00.000000+00:00",
                new Actor("test", run),
                correlationId);
    }

    /** The same event, caused by another message — the second half of the correlation/causation pair. */
    protected final DomainEvent event(String streamId, String type, CausationId causationId) {
        return new DomainEvent(
                type,
                1,
                streamId,
                Map.of(),
                "2024-01-01T00:00:00.000000+00:00",
                new Actor("test", run),
                correlationId,
                Optional.of(causationId));
    }

    protected final void mustAppend(
            EventStore store, String streamId, int expectedVersion, DomainEvent... batch) {
        AppendResult result = store.append(streamId, expectedVersion, List.of(batch));
        assertThat(result)
                .as("append to %s at version %d", streamId, expectedVersion)
                .isInstanceOf(AppendResult.Appended.class);
    }

    private List<CommittedEvent> replay(EventStore store, long from, String... streams) {
        List<String> wanted = List.of(streams);
        List<CommittedEvent> replayed = new ArrayList<>();
        store.readAll(from, event -> {
            if (wanted.contains(event.streamId())) {
                replayed.add(event);
            }
            return true;
        });
        return replayed;
    }

    protected static List<String> typesOf(List<CommittedEvent> recorded) {
        return recorded.stream().map(CommittedEvent::type).toList();
    }

    private static String randomId() {
        byte[] buffer = new byte[8];
        RANDOM.nextBytes(buffer);
        return HexFormat.of().formatHex(buffer);
    }
}
