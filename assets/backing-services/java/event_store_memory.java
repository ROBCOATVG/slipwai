package com.example.deliverystarter.adapters.driven.eventstorememory;

import com.example.deliverystarter.application.ports.events.AppendResult;
import com.example.deliverystarter.application.ports.events.CommittedEvent;
import com.example.deliverystarter.application.ports.events.Condition;
import com.example.deliverystarter.application.ports.events.ConditionalAppendResult;
import com.example.deliverystarter.application.ports.events.DomainEvent;
import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.events.EventVisitor;
import com.example.deliverystarter.application.ports.events.TagQuery;
import com.example.deliverystarter.application.ports.events.TaggedRead;
import com.example.deliverystarter.application.ports.events.TagsOf;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

/**
 * The in-memory event store.
 *
 * <p>For a quickstart with no infrastructure, and for tests that do not need to prove concurrency.
 * {@code make verify} runs the shared contract suite against this one, which is why the repository gate
 * needs no Docker.
 *
 * <p>It satisfies the port's contract, but understand what it cannot do: every call is serialised behind
 * one lock, so it <strong>cannot</strong> prove that two concurrent appends at the same version produce
 * exactly one winner — nor that two conditional appends against one boundary do. Those guarantees live in
 * a real store's unique constraint and isolation level, and {@code make test-integration} is where they are
 * proved. Ship on Postgres, demo on memory.
 *
 * <p>Data is lost when the process ends, which for an event-sourced system means the entire truth is lost.
 * Never production.
 *
 * <p>Not a CDI bean, deliberately, and neither is any other adapter here. Which store this application uses
 * is a composition decision, and with several adapters on the classpath a bean per adapter would be an
 * ambiguous injection point rather than a choice. The first slice that needs one writes the producer:
 *
 * <pre>{@code
 * @Produces
 * @ApplicationScoped
 * EventStore eventStore() {
 *     return new InMemoryEventStore();
 * }
 * }</pre>
 */
public final class InMemoryEventStore implements EventStore {

    private final InMemoryDatabase database;
    private TagsOf tagsOf;

    /** An empty store, tagging events by their own stream. */
    public InMemoryEventStore() {
        this(TagsOf.byStream(), new InMemoryDatabase());
    }

    /**
     * A store over {@code database}, indexing each event by what {@code tagsOf} returns for it.
     *
     * <p>Both arguments matter to the read side: {@code tagsOf} is what this project's events are findable
     * by, and passing the same database to {@code new InMemoryCheckpointStore(this)} is what puts a
     * checkpoint in the same unit of work as the events it accounts for.
     */
    public InMemoryEventStore(TagsOf tagsOf, InMemoryDatabase database) {
        this.tagsOf = tagsOf;
        this.database = database;
    }

    /**
     * The store's own database, for the sibling adapter to be built from — the equivalent of two SQL
     * adapters sharing one connection.
     */
    public InMemoryDatabase sharedDatabase() {
        return database;
    }

    @Override
    public List<CommittedEvent> read(String streamId) {
        return database.atomically(() -> streamLocked(streamId));
    }

    @Override
    public AppendResult append(String streamId, int expectedVersion, List<DomainEvent> events) {
        return database.inUnitOfWork(() -> database.atomically(() -> {
            List<CommittedEvent> stream = streamLocked(streamId);
            int actualVersion = EventStore.currentVersion(stream);
            if (actualVersion != expectedVersion) {
                return AppendResult.versionConflict(actualVersion);
            }
            int version = actualVersion;
            for (DomainEvent event : events) {
                version++;
                recordLocked(event, streamId, version);
            }
            return AppendResult.appended(version);
        }));
    }

    @Override
    public void readAll(long fromPosition, EventVisitor visit) {
        List<CommittedEvent> snapshot = database.atomically(() -> List.copyOf(database.log));
        for (CommittedEvent event : snapshot) {
            if (event.globalPosition() < fromPosition) {
                continue;
            }
            if (!visit.visit(event)) {
                return;
            }
        }
    }

    @Override
    public <T> T inUnitOfWork(Supplier<T> work) {
        return database.inUnitOfWork(work);
    }

    @Override
    public long head() {
        return database.atomically(database::headLocked);
    }

    @Override
    public TaggedRead readTagged(TagQuery query, long after, long until) {
        return database.atomically(() -> readTaggedLocked(query, after, until));
    }

    @Override
    public ConditionalAppendResult appendIf(Condition condition, List<DomainEvent> events) {
        return database.inUnitOfWork(() -> database.atomically(() -> {
            if (!readTaggedLocked(condition.query(), condition.after(), 0).events().isEmpty()) {
                return ConditionalAppendResult.conditionConflict(database.headLocked());
            }
            for (DomainEvent event : events) {
                // Each event still lands at the next version of the stream it names, so a conditionally
                // appended event is readable by everything written against read and append. The boundary
                // changed; the log did not.
                int at = EventStore.currentVersion(streamLocked(event.streamId()));
                recordLocked(event, event.streamId(), at + 1);
            }
            return ConditionalAppendResult.recorded(database.headLocked());
        }));
    }

    @Override
    public int reindexTags(long fromPosition) {
        return database.inUnitOfWork(() -> database.atomically(() -> {
            int indexed = 0;
            for (CommittedEvent event : database.log) {
                if (event.globalPosition() < fromPosition
                        || database.tags.containsKey(event.globalPosition())) {
                    continue;
                }
                List<String> tags = tagsOf.tagsOf(event.event());
                if (tags.isEmpty()) {
                    continue;
                }
                database.tags.put(event.globalPosition(), List.copyOf(tags));
                indexed++;
            }
            return indexed;
        }));
    }

    @Override
    public int retag(TagsOf next) {
        return database.inUnitOfWork(() -> {
            database.atomically(() -> {
                tagsOf = next;
                database.tags.clear();
                return Boolean.TRUE;
            });
            return reindexTags(0);
        });
    }

    private TaggedRead readTaggedLocked(TagQuery query, long after, long until) {
        long ceiling = until == 0 ? database.headLocked() : until;
        List<CommittedEvent> found = new ArrayList<>();
        for (CommittedEvent event : database.log) {
            if (event.globalPosition() <= after || event.globalPosition() > ceiling) {
                continue;
            }
            if (query.matches(event, database.tags.getOrDefault(event.globalPosition(), List.of()))) {
                found.add(event);
            }
        }
        return new TaggedRead(found, ceiling);
    }

    /**
     * Append one event and index it, with the lock already held.
     *
     * <p>The tags go in here rather than in a pass of their own, which is the whole design: an index
     * written after the append could be missing when the next conditional append checks it, and that append
     * would then be guarded by a boundary with a hole in it.
     */
    private void recordLocked(DomainEvent event, String streamId, int version) {
        DomainEvent inStream = event.inStream(streamId);
        long position = database.nextGlobalPosition;
        database.log.add(new CommittedEvent(inStream, version, position, Instant.now().toString()));
        // No entry at all when the tagging function returns nothing, rather than an empty one: the SQL
        // adapters give such an event no rows, and "indexed" has to mean the same thing in every adapter
        // or reindexTags answers differently depending on the store.
        List<String> tags = tagsOf.tagsOf(inStream);
        if (!tags.isEmpty()) {
            database.tags.put(position, List.copyOf(tags));
        }
        database.nextGlobalPosition++;
    }

    private List<CommittedEvent> streamLocked(String streamId) {
        List<CommittedEvent> stream = new ArrayList<>();
        for (CommittedEvent event : database.log) {
            if (event.streamId().equals(streamId)) {
                stream.add(event);
            }
        }
        return stream;
    }
}
