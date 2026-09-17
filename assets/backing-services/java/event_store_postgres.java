package com.example.deliverystarter.adapters.driven.eventstorepostgres;

import com.example.deliverystarter.application.ports.events.Actor;
import com.example.deliverystarter.application.ports.events.AppendResult;
import com.example.deliverystarter.application.ports.events.CausationId;
import com.example.deliverystarter.application.ports.events.CommittedEvent;
import com.example.deliverystarter.application.ports.events.Condition;
import com.example.deliverystarter.application.ports.events.ConditionalAppendResult;
import com.example.deliverystarter.application.ports.events.CorrelationId;
import com.example.deliverystarter.application.ports.events.DomainEvent;
import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.events.EventStoreException;
import com.example.deliverystarter.application.ports.events.EventVisitor;
import com.example.deliverystarter.application.ports.events.TagQuery;
import com.example.deliverystarter.application.ports.events.TaggedRead;
import com.example.deliverystarter.application.ports.events.TagsOf;
import com.example.deliverystarter.adapters.driven.sql.Transactions;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Supplier;

/**
 * The Postgres event store — the only class that knows the event log is SQL.
 *
 * <p>Concurrency is enforced twice over, deliberately:
 *
 * <ol>
 *   <li>Each insert carries a {@code WHERE (SELECT MAX(version) ...) = expected} guard, which catches a
 *       stale expectation — a caller that decided against version 3 while the stream moved to 5.
 *   <li>The {@code (stream_id, version)} unique constraint catches the true race, where two transactions
 *       both pass the guard and then try to write the same version.
 * </ol>
 *
 * <p>The guard alone is insufficient (two concurrent transactions see the same MAX under READ COMMITTED),
 * and the constraint alone is insufficient (a stale expectation could write a valid later version without
 * conflict). Both are needed.
 *
 * <p>{@code appendIf} can use neither, because there is no version to compare: what it must prove is that
 * <em>nothing matching a query</em> arrived since the caller read. It asks Postgres for SERIALIZABLE and
 * lets the database prove it. The cost is a real one and it is the caller's: a serialisation failure is
 * reported as a conflict, and the caller re-reads and re-decides exactly as it does for a stale version.
 *
 * <p>It takes {@link Transactions} — the framework's transaction manager, as a port — and holds no
 * connection of its own. That is load-bearing rather than tidy. Two simultaneous appends need two
 * connections to genuinely race, which is what makes the concurrency guarantee observable at all; the pool
 * and its transaction semantics are the framework's to maintain rather than this repository's; and, most of
 * all, a store that took a connection could never be enlisted in anybody else's transaction. Because this
 * one asks the framework per call, a service method annotated {@code @Transactional} gets the append and
 * its own repository's writes in one transaction, and an {@code inline} read model is that annotation
 * rather than a wiring trick.
 *
 * <p>Not a bean, on purpose. Which store this application uses is a composition decision, and with several
 * adapters on the classpath a bean per adapter would be an ambiguous injection point rather than a choice.
 * The first slice that needs one writes the producer, taking the transactions bean the framework already
 * has:
 *
 * <pre>{@code
 * @Produces
 * @ApplicationScoped
 * EventStore eventStore(Transactions transactions) {
 *     return new PostgresEventStore(transactions);
 * }
 * }</pre>
 *
 * <p>A sibling adapter that has to commit in this store's transaction — the checkpoint store is the one
 * the read side ships — is given the same {@code Transactions}, not this store. There is nothing to thread
 * through: both ask the framework which connection the current transaction is on, and so does the
 * project's own repository.
 */
public final class PostgresEventStore implements EventStore {

    /** Postgres' SQLSTATE for a unique-constraint violation. */
    private static final String UNIQUE_VIOLATION = "23505";

    /**
     * Postgres' SQLSTATE for a SERIALIZABLE transaction that could not be ordered against a concurrent
     * one. For a conditional append it means the same thing a broken condition does, and asks the same
     * thing of the caller: read again, decide again.
     */
    private static final String SERIALIZATION_FAILURE = "40001";

    private static final String INSERT_GUARDED = """
              INSERT INTO events (
                stream_id, version, event_type, schema_version, payload, actor,
                correlation_id, causation_id, occurred_at
              )
              SELECT ?, ?, ?, ?, CAST(? AS jsonb), CAST(? AS jsonb), CAST(? AS uuid), CAST(? AS uuid),
                     CAST(? AS timestamptz)
              WHERE (SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = ?) = ?
              RETURNING global_position
            """;

    /**
     * The timestamps come back as text in one fixed shape, rather than as a driver-specific temporal type
     * mapped through the JVM's default zone. An event's time is a fact about when something happened, and a
     * value that reads differently depending on the reader's zone is not one fact.
     */
    private static final String EVENT_COLUMNS = """
              global_position, stream_id, version, event_type, schema_version, payload, actor,
              -- Cast to text and parsed back into the value type below, the same way every other
              -- adapter reads them. The column is a real uuid; what crosses this boundary is text either
              -- way, and doing it in one place keeps the driver's UUID mapping out of this file.
              correlation_id::text AS correlation_id, causation_id::text AS causation_id,
              to_char(occurred_at, 'YYYY-MM-DD"T"HH24:MI:SS.USOF') AS occurred_at,
              to_char(recorded_at, 'YYYY-MM-DD"T"HH24:MI:SS.USOF') AS recorded_at
            """;

    private static final String STORE_HEAD = "SELECT COALESCE(MAX(global_position), 0) FROM events";

    /**
     * The log's own advisory lock, which is how a reader learns that a position is settled.
     *
     * <p>A global position is assigned when a row is inserted and becomes visible when its transaction
     * commits, and those are not the same moment: two appends overlapping can take 5 and 6 and commit 6
     * first. A reader that sees 6 and records "next is 7" has skipped 5 for good, because 5 arrives behind
     * a checkpoint that has already passed it. Nothing in the log is wrong afterwards, and the view is
     * missing a row nothing will ever put back.
     *
     * <p>So an append takes this lock in <strong>shared</strong> mode before its first insert, which costs
     * nothing because shared holders do not block each other, and {@code readAll} takes it
     * <strong>exclusively</strong> for one {@code MAX(global_position)} query. Acquiring it exclusively
     * means no append is between its insert and its commit, so every position at or below that maximum is
     * final: committed and visible, or aborted and gone for good. Reading no further than that is what
     * makes a single number a safe place for a projection to resume from.
     *
     * <p>The number is arbitrary and only has to be the same in every adapter that opens this log. It must
     * not be reused for anything else in the same database, which is why it lives here.
     */
    private static final long EVENTS_LOCK = 8_317_231L;

    /** Take the log's lock in shared mode, so appends never block each other. */
    private static final String LOCK_SHARED = "SELECT pg_advisory_xact_lock_shared(?)";

    /** Take it exclusively, which waits for every append in flight to finish. */
    private static final String LOCK_EXCLUSIVE = "SELECT pg_advisory_xact_lock(?)";

    private static final String INSERT_TAG = """
              INSERT INTO event_tags (tag, global_position) VALUES (?, ?)
              ON CONFLICT DO NOTHING
            """;

    private static final String DELETE_TAGS = "DELETE FROM event_tags";

    private static final String CURRENT_VERSION =
            "SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = ?";

    private static final String UNINDEXED_EVENTS = "SELECT " + EVENT_COLUMNS + """
              FROM events
              WHERE global_position >= ?
                AND NOT EXISTS (SELECT 1 FROM event_tags WHERE global_position = events.global_position)
              ORDER BY global_position ASC
              LIMIT ?
            """;

    /** Keeps a rebuild over a long log from materialising the whole thing in memory. */
    private static final int READ_ALL_BATCH_SIZE = 500;

    private static final ObjectMapper JSON = new ObjectMapper();

    private final Transactions transactions;
    private TagsOf tagsOf;

    /** Binds the adapter to the framework's transactions, tagging events by their own stream. */
    public PostgresEventStore(Transactions transactions) {
        this(transactions, TagsOf.byStream());
    }

    /**
     * Binds the adapter to the framework's transactions with this project's own tagging function — what
     * its events are findable by beyond their stream.
     */
    public PostgresEventStore(Transactions transactions, TagsOf tagsOf) {
        this.transactions = transactions;
        this.tagsOf = tagsOf;
    }

    private <T> T onConnection(String what, Transactions.SqlWork<T> work) {
        return transactions.onConnection(what, work);
    }

    @Override
    public <T> T inUnitOfWork(Supplier<T> work) {
        return transactions.inTransaction(Transactions.Isolation.DEFAULT, work);
    }

    @Override
    public List<CommittedEvent> read(String streamId) {
        String query =
                "SELECT " + EVENT_COLUMNS + " FROM events WHERE stream_id = ? ORDER BY version ASC";
        return onConnection("read stream " + streamId, connection -> {
            try (PreparedStatement statement = connection.prepareStatement(query)) {
                statement.setString(1, streamId);
                try (ResultSet rows = statement.executeQuery()) {
                    List<CommittedEvent> stream = new ArrayList<>();
                    while (rows.next()) {
                        stream.add(scanEvent(rows));
                    }
                    return stream;
                }
            }
        });
    }

    @Override
    public AppendResult append(String streamId, int expectedVersion, List<DomainEvent> events) {
        if (events.isEmpty()) {
            return AppendResult.appended(expectedVersion);
        }
        try {
            return inUnitOfWork(() -> {
                holdTheLog();
                int version = expectedVersion;
                for (DomainEvent event : events) {
                    int guardAgainst = version;
                    version++;
                    insertEvent(streamId, version, guardAgainst, event);
                }
                return AppendResult.appended(version);
            });
        } catch (Refused refused) {
            // The guard failed: the stream is not where the caller thought it was. A conflict is a value
            // rather than an exception, because contention is expected under load, not exceptional.
            return AppendResult.versionConflict(currentVersion(streamId));
        } catch (EventStoreException failure) {
            // The true race: another transaction committed the same version between our guard and our
            // insert. Reported the same way.
            if (failure.getCause() instanceof SQLException sql
                    && UNIQUE_VIOLATION.equals(sql.getSQLState())) {
                return AppendResult.versionConflict(currentVersion(streamId));
            }
            throw failure;
        }
    }

    /**
     * Hold the log in shared mode until this transaction ends — see {@link #EVENTS_LOCK}.
     *
     * <p>Before the first insert, always, and re-entrant: taking it twice in one transaction is free.
     * Shared, so two appends never wait for each other; what waits is a reader asking whether a position
     * has settled.
     */
    private void holdTheLog() {
        onConnection("hold the log", connection -> {
            try (PreparedStatement statement = connection.prepareStatement(LOCK_SHARED)) {
                statement.setLong(1, EVENTS_LOCK);
                statement.execute();
            }
            return Boolean.TRUE;
        });
    }

    /**
     * The highest position nothing earlier can still be committed behind — see {@link #EVENTS_LOCK}.
     *
     * <p>Its own transaction, so the exclusive hold lasts microseconds: long enough to prove nothing is in
     * flight, short enough that the appends queueing behind it barely notice. Two statements rather than
     * one, because the order in which Postgres evaluates a lock function beside an aggregate is not
     * something to rely on.
     */
    private long settledPosition() {
        return inUnitOfWork(() -> onConnection("wait for the log to settle", connection -> {
            try (PreparedStatement statement = connection.prepareStatement(LOCK_EXCLUSIVE)) {
                statement.setLong(1, EVENTS_LOCK);
                statement.execute();
            }
            return head(connection);
        }));
    }

    @Override
    public void readAll(long fromPosition, EventVisitor visit) {
        String query = "SELECT " + EVENT_COLUMNS
                + " FROM events WHERE global_position >= ? AND global_position <= ?"
                + " ORDER BY global_position ASC LIMIT ?";
        // The ceiling is taken once, at the start: an event appended while a long replay is running
        // belongs to the next pass, and a checkpoint that stopped short of it loses nothing.
        long settled = settledPosition();
        long position = fromPosition;
        while (position <= settled) {
            long from = position;
            List<CommittedEvent> batch = onConnection("replay from " + from, connection -> {
                try (PreparedStatement statement = connection.prepareStatement(query)) {
                    statement.setLong(1, from);
                    statement.setLong(2, settled);
                    statement.setInt(3, READ_ALL_BATCH_SIZE);
                    try (ResultSet rows = statement.executeQuery()) {
                        List<CommittedEvent> read = new ArrayList<>();
                        while (rows.next()) {
                            read.add(scanEvent(rows));
                        }
                        return read;
                    }
                }
            });
            if (batch.isEmpty()) {
                return;
            }
            for (CommittedEvent event : batch) {
                if (!visit.visit(event)) {
                    return;
                }
            }
            position = batch.get(batch.size() - 1).globalPosition() + 1;
        }
    }

    /**
     * The last <strong>settled</strong> position, which is the only kind a decision may be guarded at.
     *
     * <p>The same protocol {@code readAll} uses, and for a reason that took a reproduction to see: a
     * boundary past an event still in flight is a boundary the guard cannot check. Two appends take 5 and
     * 6, 6 commits first, a decision reads a head of 6 while 5 is invisible — and {@code appendIf} then
     * looks for anything matching <em>after</em> 6 and never sees 5, because 5 sits below its own
     * boundary. The append is allowed and the constraint it was meant to hold is broken, with a
     * correct-looking log to show for it.
     *
     * <p>Waiting for the appends in flight fixes it twice over: the boundary is one nothing can arrive
     * behind, and the read that follows sees the very events the decision has to know about.
     *
     * <p>Inside a transaction, the answer is that transaction's own view instead — a caller reading its
     * own writes rather than drawing a boundary, which is what an inline read model does. Asking for the
     * settled position there would wait on a lock the transaction is itself holding.
     */
    @Override
    public long head() {
        if (transactions.isActive()) {
            return onConnection("read the store head", this::head);
        }
        return settledPosition();
    }

    @Override
    public TaggedRead readTagged(TagQuery query, long after, long until) {
        Predicate predicate = tagQuerySql(query);
        // Before the read rather than inside it, so the ceiling is one number the rows are bounded by
        // rather than a second connection's opinion of where the log ends.
        long ceiling = until == 0 ? head() : until;
        String sql = "SELECT " + EVENT_COLUMNS + " FROM events e WHERE e.global_position > ?"
                + " AND e.global_position <= ? AND " + predicate.sql()
                + " ORDER BY e.global_position ASC";
        return onConnection("read by tag query", connection -> {
            List<CommittedEvent> found = new ArrayList<>();
            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setLong(1, after);
                statement.setLong(2, ceiling);
                predicate.bind(statement, 3);
                try (ResultSet rows = statement.executeQuery()) {
                    while (rows.next()) {
                        found.add(scanEvent(rows));
                    }
                }
            }
            return new TaggedRead(found, ceiling);
        });
    }

    /**
     * Append only if nothing matching the condition arrived since the caller read.
     *
     * <p>SERIALIZABLE, not a clever {@code WHERE NOT EXISTS}: the guard is the <em>absence</em> of rows,
     * and absence is what no lock in a row-locking database can hold. Postgres detects the conflict at
     * commit and raises a serialisation failure, which is reported here as a conflict — because for the
     * caller it is the same fact and the same next move, re-read and re-decide.
     */
    @Override
    public ConditionalAppendResult appendIf(Condition condition, List<DomainEvent> events) {
        try {
            return transactions.inTransaction(Transactions.Isolation.SERIALIZABLE, () -> {
                holdTheLog();
                if (anythingMatching(condition)) {
                    throw new Refused();
                }
                for (DomainEvent event : events) {
                    // Each event still lands at the next version of the stream it names, so everything
                    // written against read and append keeps working: what the condition replaced is the
                    // guard, not the shape of the log.
                    int at = currentVersion(event.streamId());
                    insertEvent(event.streamId(), at + 1, at, event);
                }
                return ConditionalAppendResult.recorded(head());
            });
        } catch (Refused refused) {
            return ConditionalAppendResult.conditionConflict(head());
        } catch (EventStoreException failure) {
            if (failure.getCause() instanceof SQLException sql
                    && SERIALIZATION_FAILURE.equals(sql.getSQLState())) {
                return ConditionalAppendResult.conditionConflict(head());
            }
            throw failure;
        }
    }

    /**
     * Index what this store's tagging function has not indexed yet, a batch at a time.
     *
     * <p>Resumable on purpose: a project adopting tags runs this over a log that may be very long, and a
     * run that died halfway is continued by running it again rather than started over.
     */
    @Override
    public int reindexTags(long fromPosition) {
        int indexed = 0;
        long position = fromPosition;
        while (true) {
            long from = position;
            Reindexed batch = inUnitOfWork(() -> onConnection(
                    "read the unindexed events", connection -> {
                        List<CommittedEvent> read = new ArrayList<>();
                        try (PreparedStatement statement =
                                connection.prepareStatement(UNINDEXED_EVENTS)) {
                            statement.setLong(1, from);
                            statement.setInt(2, READ_ALL_BATCH_SIZE);
                            try (ResultSet rows = statement.executeQuery()) {
                                while (rows.next()) {
                                    read.add(scanEvent(rows));
                                }
                            }
                        }
                        int written = 0;
                        for (CommittedEvent event : read) {
                            if (indexTags(connection, event.globalPosition(), event.event())) {
                                written++;
                            }
                        }
                        return new Reindexed(read, written);
                    }));
            if (batch.read().isEmpty()) {
                return indexed;
            }
            indexed += batch.written();
            position = batch.read().get(batch.read().size() - 1).globalPosition() + 1;
        }
    }

    @Override
    public int retag(TagsOf next) {
        return inUnitOfWork(() -> {
            tagsOf = next;
            onConnection("empty the tag index", connection -> {
                try (PreparedStatement statement = connection.prepareStatement(DELETE_TAGS)) {
                    statement.executeUpdate();
                }
                return Boolean.TRUE;
            });
            // Inside this unit of work, so the old index is never visible as gone: either the whole
            // re-index commits or the old one stands.
            return reindexTags(0);
        });
    }

    private boolean anythingMatching(Condition condition) {
        Predicate predicate = tagQuerySql(condition.query());
        String sql = "SELECT 1 FROM events e WHERE e.global_position > ? AND " + predicate.sql()
                + " LIMIT 1";
        return onConnection("check a condition", connection -> {
            try (PreparedStatement statement = connection.prepareStatement(sql)) {
                statement.setLong(1, condition.after());
                predicate.bind(statement, 2);
                try (ResultSet rows = statement.executeQuery()) {
                    return rows.next();
                }
            }
        });
    }

    private long head(Connection connection) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(STORE_HEAD);
                ResultSet rows = statement.executeQuery()) {
            return rows.next() ? rows.getLong(1) : 0;
        }
    }

    private int currentVersion(String streamId) {
        return onConnection(
                "read current version of " + streamId,
                connection -> currentVersion(connection, streamId));
    }

    /**
     * Write one event, plus its tags, inside whatever transaction is open.
     *
     * <p>The tags go in here rather than in a pass of their own, which is the whole design: an index
     * written after the append could be missing when the next conditional append checks it, and that append
     * would then be guarded by a boundary with a hole in it.
     */
    private void insertEvent(String streamId, int version, int guardAgainst, DomainEvent event) {
        onConnection("append to " + streamId, connection -> {
            long position = insert(connection, streamId, version, guardAgainst, event);
            indexTags(connection, position, event.inStream(streamId));
            return Boolean.TRUE;
        });
    }

    /**
     * Index one event's tags, reporting whether it now has any.
     *
     * <p>The answer is what {@code reindexTags} counts: an event this project's tagging function has
     * nothing to say about stays unindexed for good, so a run that counted it would promise an index with
     * nothing in it and never settle at zero.
     */
    private boolean indexTags(Connection connection, long position, DomainEvent event)
            throws SQLException {
        List<String> tags = tagsOf.tagsOf(event);
        for (String tag : tags) {
            try (PreparedStatement statement = connection.prepareStatement(INSERT_TAG)) {
                statement.setString(1, tag);
                statement.setLong(2, position);
                statement.executeUpdate();
            }
        }
        return !tags.isEmpty();
    }

    /** One batch of a reindex: what it read, and how many of those it made findable. */
    private record Reindexed(List<CommittedEvent> read, int written) {
    }

    /**
     * A tag query as a SQL predicate over {@code e}, plus the arguments it binds.
     *
     * <p>{@code TagQuery.Filter.matches} in the port is the definition; this is its translation, and the
     * contract suite is what holds the two to each other. Every SQL adapter carries its own copy of this
     * translation, deliberately duplicated rather than shared: an adapter that imports another adapter is
     * two adapters that cannot be pruned apart.
     *
     * <ul>
     *   <li>a filter's tags are a <strong>conjunction</strong> — the number of its tags found against the
     *       event must equal how many it named, because {@code IN} on its own is an "any of" and a much
     *       weaker guard than the caller asked for;
     *   <li>its types narrow within that filter only;
     *   <li>a filter naming neither, and a query with no filters at all, match nothing: {@code 1 = 0}
     *       rather than a missing predicate, because an absent guard matches everything and a conditional
     *       append that matched everything would refuse every write in the system.
     * </ul>
     */
    private static Predicate tagQuerySql(TagQuery query) {
        if (query.filters().isEmpty()) {
            return new Predicate("1 = 0", List.of());
        }
        List<String> predicates = new ArrayList<>();
        List<Object> arguments = new ArrayList<>();
        for (TagQuery.Filter filter : query.filters()) {
            if (filter.tags().isEmpty() && filter.types().isEmpty()) {
                predicates.add("1 = 0");
                continue;
            }
            List<String> parts = new ArrayList<>();
            if (!filter.tags().isEmpty()) {
                parts.add("(SELECT COUNT(*) FROM event_tags t WHERE t.global_position = e.global_position"
                        + " AND t.tag IN (" + placeholders(filter.tags().size()) + ")) = ?");
                arguments.addAll(filter.tags());
                arguments.add(Set.copyOf(filter.tags()).size());
            }
            if (!filter.types().isEmpty()) {
                parts.add("e.event_type IN (" + placeholders(filter.types().size()) + ")");
                arguments.addAll(filter.types());
            }
            predicates.add("(" + String.join(" AND ", parts) + ")");
        }
        return new Predicate("(" + String.join(" OR ", predicates) + ")", arguments);
    }

    private static String placeholders(int count) {
        return String.join(", ", Collections.nCopies(count, "?"));
    }

    /** A SQL fragment and the arguments it binds, so the two cannot drift apart. */
    private record Predicate(String sql, List<Object> arguments) {

        void bind(PreparedStatement statement, int from) throws SQLException {
            int index = from;
            for (Object argument : arguments) {
                if (argument instanceof Integer count) {
                    statement.setInt(index, count);
                } else {
                    statement.setString(index, argument.toString());
                }
                index++;
            }
        }
    }

    /**
     * The stream is not where the caller thought it was, or the condition no longer holds.
     *
     * <p>Thrown inside the unit of work so the transaction unwinds, and caught immediately outside it and
     * turned back into a conflict <em>value</em>. Returning from inside the block would commit the
     * half-written append it is refusing — and in Postgres a failed statement poisons the transaction until
     * something rolls back, so this is not only tidier, it is the only correct shape.
     */
    private static final class Refused extends RuntimeException {

        private static final long serialVersionUID = 1L;

        Refused() {
            super("refused", null, false, false);
        }
    }

    private static long insert(
            Connection connection, String streamId, int version, int guardAgainst, DomainEvent event)
            throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(INSERT_GUARDED)) {
            statement.setString(1, streamId);
            statement.setInt(2, version);
            statement.setString(3, event.type());
            statement.setInt(4, event.schemaVersion());
            statement.setString(5, encode(event.payload()));
            statement.setString(6, encodeActor(event.actor()));
            statement.setString(7, event.correlationId().toString());
            if (event.causationId().isEmpty()) {
                statement.setNull(8, Types.VARCHAR);
            } else {
                statement.setString(8, event.causationId().get().toString());
            }
            statement.setString(9, event.occurredAt());
            statement.setString(10, streamId);
            statement.setInt(11, guardAgainst);
            try (ResultSet rows = statement.executeQuery()) {
                if (!rows.next()) {
                    throw new Refused();
                }
                return rows.getLong(1);
            }
        }
    }

    private static int currentVersion(Connection connection, String streamId) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(CURRENT_VERSION)) {
            statement.setString(1, streamId);
            try (ResultSet rows = statement.executeQuery()) {
                return rows.next() ? rows.getInt(1) : EventStore.NO_STREAM;
            }
        }
    }

    private static String encode(Map<String, Object> payload) {
        try {
            return JSON.writeValueAsString(payload);
        } catch (JsonProcessingException failure) {
            throw new EventStoreException("encode payload", failure);
        }
    }

    private static String encodeActor(Actor actor) {
        return encode(new LinkedHashMap<>(Map.of("kind", actor.kind(), "id", actor.id())));
    }

    /**
     * Parse a stored row back into a {@link CommittedEvent}.
     *
     * <p>Events are validated on read as well as on write, because stored events outlive the code that wrote
     * them. A tolerant reader on purpose: unknown payload fields written by a newer version are carried
     * through rather than rejected, which is what makes a rolling deploy possible. Only the envelope itself
     * is required.
     */
    private static CommittedEvent scanEvent(ResultSet row) throws SQLException {
        long globalPosition = row.getLong("global_position");
        int schemaVersion = row.getInt("schema_version");
        if (schemaVersion != 1) {
            throw new EventStoreException("event at global_position " + globalPosition
                    + " is schema version " + schemaVersion
                    + "; add an upcaster for it before reading it as version 1");
        }
        Map<String, Object> payload = decode(globalPosition, row.getString("payload"));
        Actor actor = decodeActor(globalPosition, row.getString("actor"));
        String causationId = row.getString("causation_id");
        DomainEvent event = new DomainEvent(
                row.getString("event_type"),
                schemaVersion,
                row.getString("stream_id"),
                payload,
                row.getString("occurred_at"),
                actor,
                // Parsed rather than passed through, so a row written by something that was not this
                // adapter cannot enter the domain as an identifier nothing can correlate.
                CorrelationId.of(row.getString("correlation_id")),
                Optional.ofNullable(causationId).map(CausationId::of));
        return new CommittedEvent(
                event, row.getInt("version"), globalPosition, row.getString("recorded_at"));
    }

    private static Map<String, Object> decode(long globalPosition, String encoded) {
        try {
            return JSON.readValue(encoded, new TypeReference<Map<String, Object>>() {});
        } catch (JsonProcessingException failure) {
            throw new EventStoreException(
                    "event at global_position " + globalPosition + " has an unreadable payload", failure);
        }
    }

    private static Actor decodeActor(long globalPosition, String encoded) {
        Map<String, Object> decoded = decode(globalPosition, encoded);
        Object kind = decoded.get("kind");
        if (kind == null || kind.toString().isEmpty()) {
            throw new EventStoreException(
                    "event at global_position " + globalPosition + " has no usable actor");
        }
        Object id = decoded.get("id");
        return new Actor(kind.toString(), id == null ? "" : id.toString());
    }
}
