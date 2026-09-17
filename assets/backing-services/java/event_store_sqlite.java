package com.example.deliverystarter.adapters.driven.eventstoresqlite;

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
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Types;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Supplier;
import org.sqlite.SQLiteDataSource;

/**
 * The SQLite event store — a real append-only log in one file, with no container to run.
 *
 * <p>Chosen when durability matters and infrastructure does not: a single-process service, a CLI, a
 * long-running worker, or a demo that must survive a restart.
 *
 * <p>Understand the one thing it cannot do before adopting it: SQLite serialises writers. It proves
 * durability and it proves the append-only rule, but it <strong>cannot</strong> prove concurrent behaviour,
 * because it never genuinely races. If the never-write-the-same-version-twice guarantee matters to your
 * product, prove it on Postgres — {@code make test-integration} there races two appends at one version and
 * requires exactly one winner.
 *
 * <p>This adapter opens its own {@link SQLiteDataSource} rather than injecting Agroal's, and that is the one
 * place in this project where the framework's integration is deliberately not used. Quarkus publishes no
 * first-party SQLite JDBC extension, and the Quarkiverse one tracks Quarkus 3.0 — thirty-odd minor versions
 * behind this project's LTS — so adopting it would pin the whole build to a two-year-old platform. There is
 * also nothing to pool: SQLite serialises writers, so one connection at a time is the correct
 * configuration rather than a limitation.
 *
 * <p>Unlike Postgres, the schema ships with the adapter rather than as a migration: an embedded database is
 * created by the process that opens it, so there is no separate {@code make migrate} step and nothing to
 * run before the first test. The three tables below are the same three the Postgres migrations create — the
 * log, the projection checkpoints, and the derived tag index — because two spellings of one schema drift
 * and nothing notices.
 */
public final class SqliteEventStore implements EventStore, AutoCloseable {

    /**
     * {@code global_position} is INTEGER PRIMARY KEY, which in SQLite aliases the monotonic rowid — the
     * {@code readAll} ordering the port promises. The append-only guarantee is enforced in the database
     * rather than in this file, because a rule the application enforces is a rule the next process to open
     * the file will not.
     */
    private static final List<String> SCHEMA = List.of(
            """
            CREATE TABLE IF NOT EXISTS events (
              global_position INTEGER PRIMARY KEY,
              stream_id       TEXT    NOT NULL,
              version         INTEGER NOT NULL,
              event_type      TEXT    NOT NULL,
              schema_version  INTEGER NOT NULL,
              payload         TEXT    NOT NULL,
              actor           TEXT    NOT NULL,
              -- SQLite has no UUID type, so the canonical text form is what is stored. Postgres uses a
              -- real uuid column; both round-trip through the same value type, and the adapter is where
              -- that difference stops.
              correlation_id  TEXT    NOT NULL,
              causation_id    TEXT,
              occurred_at     TEXT    NOT NULL,
              recorded_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              CONSTRAINT events_stream_version_unique UNIQUE (stream_id, version),
              CONSTRAINT events_version_non_negative CHECK (version >= 0)
            )
            """,
            "CREATE INDEX IF NOT EXISTS events_stream_id_version ON events (stream_id, version)",
            """
            CREATE TRIGGER IF NOT EXISTS events_reject_update
            BEFORE UPDATE ON events
            BEGIN
              SELECT RAISE(ABORT, 'events is append-only: UPDATE is rejected');
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS events_reject_delete
            BEFORE DELETE ON events
            BEGIN
              SELECT RAISE(ABORT, 'events is append-only: DELETE is rejected');
            END
            """,
            """
            -- Where each projection has got to. Mutable by design, and deliberately with no trigger: a
            -- checkpoint is a position that moves, and everything derived from the log can be thrown
            -- away and rebuilt. The lease columns are how exactly one worker advances it, with an expiry
            -- so that survives the worker dying.
            CREATE TABLE IF NOT EXISTS projection_checkpoints (
              projection        TEXT    PRIMARY KEY,
              position          INTEGER NOT NULL DEFAULT 0,
              lease_owner       TEXT,
              lease_expires_at  TEXT,
              updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              CONSTRAINT projection_checkpoints_position_non_negative CHECK (position >= 0),
              CONSTRAINT projection_checkpoints_lease_is_whole CHECK (
                (lease_owner IS NULL) = (lease_expires_at IS NULL)
              )
            )
            """,
            """
            -- The tag index — the Dynamic Consistency Boundary's half of the log. Derived from the events
            -- by this project's tagging function, written inside the append's own transaction, and
            -- rebuildable at any time, which is what lets a running project adopt tags without rewriting
            -- a log it is forbidden to rewrite.
            CREATE TABLE IF NOT EXISTS event_tags (
              tag             TEXT    NOT NULL,
              global_position INTEGER NOT NULL REFERENCES events (global_position),
              PRIMARY KEY (tag, global_position)
            )
            """,
            "CREATE INDEX IF NOT EXISTS event_tags_global_position ON event_tags (global_position)");

    private static final String INSERT_GUARDED = """
              INSERT INTO events (
                stream_id, version, event_type, schema_version, payload, actor,
                correlation_id, causation_id, occurred_at
              )
              SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
              WHERE (SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = ?) = ?
            """;

    private static final String EVENT_COLUMNS = """
              global_position, stream_id, version, event_type, schema_version, payload, actor,
              correlation_id, causation_id, occurred_at, recorded_at
            """;

    private static final String CURRENT_VERSION =
            "SELECT COALESCE(MAX(version), -1) FROM events WHERE stream_id = ?";

    private static final String STORE_HEAD = "SELECT COALESCE(MAX(global_position), 0) FROM events";

    private static final String LAST_POSITION = "SELECT last_insert_rowid()";

    private static final String INSERT_TAG =
            "INSERT OR IGNORE INTO event_tags (tag, global_position) VALUES (?, ?)";

    private static final String DELETE_TAGS = "DELETE FROM event_tags";

    private static final String UNINDEXED_EVENTS = "SELECT " + EVENT_COLUMNS + """
              FROM events
              WHERE global_position >= ?
                AND NOT EXISTS (SELECT 1 FROM event_tags WHERE global_position = events.global_position)
              ORDER BY global_position ASC
            """;

    /** Keeps a rebuild over a long log from materialising the whole thing in memory. */
    private static final int READ_ALL_BATCH_SIZE = 500;

    private static final ObjectMapper JSON = new ObjectMapper();

    private final Connection connection;
    private TagsOf tagsOf;
    private int depth;

    /**
     * Open, or create, a SQLite-backed event store, tagging events by their own stream.
     *
     * @param location a file path, or {@code :memory:} for a store that exists only as long as the process —
     *     which is what the contract suite uses, so the same SQL runs in {@code make verify} with nothing
     *     installed
     */
    public SqliteEventStore(String location) {
        this(location, TagsOf.byStream());
    }

    /**
     * Open, or create, a SQLite-backed event store with this project's own tagging function — what its
     * events are findable by beyond their stream.
     */
    public SqliteEventStore(String location, TagsOf tagsOf) {
        this.tagsOf = tagsOf;
        SQLiteDataSource dataSource = new SQLiteDataSource();
        dataSource.setUrl("jdbc:sqlite:" + location);
        // WAL lets readers run while a writer holds the write lock, and is a no-op for ":memory:". FULL
        // synchronous is the default and is what makes a committed append survive a power loss; anything
        // weaker trades the D in ACID for throughput, which an event log cannot afford.
        dataSource.setJournalMode("WAL");
        try {
            // One connection, deliberately, held open for the life of the adapter. For ":memory:" a second
            // connection would open a second, empty database — which reads as data loss.
            this.connection = dataSource.getConnection();
            try (Statement statement = connection.createStatement()) {
                // One statement per call, because JDBC executes one statement per call — and a trigger
                // body carries its own semicolons, so splitting a single script on `;` is a parser
                // nobody wants to own. The list above is already split.
                for (String ddl : SCHEMA) {
                    statement.executeUpdate(ddl);
                }
            }
        } catch (SQLException failure) {
            throw new EventStoreException("open sqlite at " + location, failure);
        }
    }

    @Override
    public void close() {
        try {
            connection.close();
        } catch (SQLException failure) {
            throw new EventStoreException("close sqlite", failure);
        }
    }

    /**
     * The one connection, for the sibling adapter to write through.
     *
     * <p>Public deliberately: an inline read model and a projection's checkpoint have to land in the same
     * transaction as the append, and a second connection cannot do that however carefully it is called.
     * {@code new SqliteCheckpointStore(store)} takes this.
     */
    public Connection sharedConnection() {
        return connection;
    }

    /**
     * One transaction, shared by this store and anything else on its connection.
     *
     * <p>Nesting uses a SAVEPOINT rather than a counter that shrugs: an inner block that fails has to undo
     * its own writes and no more, and the alternative — leaving them in the outer transaction — would let a
     * refused append pollute a transaction that goes on to commit.
     */
    @Override
    public <T> T inUnitOfWork(Supplier<T> work) {
        return depth > 0 ? inSavepoint(work) : inTransaction(work);
    }

    private <T> T inSavepoint(Supplier<T> work) {
        depth++;
        String savepoint = "uow_" + depth;
        execute("SAVEPOINT " + savepoint);
        // A flag and a finally rather than a catch of everything: what has to happen is "undo unless it
        // succeeded", and that is what this says.
        boolean done = false;
        try {
            T result = work.get();
            execute("RELEASE SAVEPOINT " + savepoint);
            done = true;
            return result;
        } finally {
            if (!done) {
                execute("ROLLBACK TO SAVEPOINT " + savepoint);
            }
            depth--;
        }
    }

    private <T> T inTransaction(Supplier<T> work) {
        try {
            connection.setAutoCommit(false);
        } catch (SQLException failure) {
            throw new EventStoreException("begin a unit of work", failure);
        }
        // Incremented and decremented rather than set and cleared, so the two halves are obviously each
        // other's opposite — and so that what reads it is visible: `work` re-enters inUnitOfWork, and this
        // is the depth that tells it to take a savepoint instead of a transaction.
        depth++;
        boolean committed = false;
        try {
            T result = work.get();
            connection.commit();
            committed = true;
            return result;
        } catch (SQLException failure) {
            throw new EventStoreException("commit a unit of work", failure);
        } finally {
            depth--;
            end(committed);
        }
    }

    /** Roll back what was not committed, and hand the connection back to autocommit either way. */
    private void end(boolean committed) {
        try {
            if (!committed) {
                connection.rollback();
            }
            connection.setAutoCommit(true);
        } catch (SQLException failure) {
            throw new EventStoreException("end a unit of work", failure);
        }
    }

    private void execute(String statement) {
        try (Statement handle = connection.createStatement()) {
            handle.executeUpdate(statement);
        } catch (SQLException failure) {
            throw new EventStoreException(statement, failure);
        }
    }

    @Override
    public List<CommittedEvent> read(String streamId) {
        String query =
                "SELECT " + EVENT_COLUMNS + " FROM events WHERE stream_id = ? ORDER BY version ASC";
        try (PreparedStatement statement = connection.prepareStatement(query)) {
            statement.setString(1, streamId);
            try (ResultSet rows = statement.executeQuery()) {
                List<CommittedEvent> stream = new ArrayList<>();
                while (rows.next()) {
                    stream.add(scanEvent(rows));
                }
                return stream;
            }
        } catch (SQLException failure) {
            throw new EventStoreException("read stream " + streamId, failure);
        }
    }

    @Override
    public AppendResult append(String streamId, int expectedVersion, List<DomainEvent> events) {
        if (events.isEmpty()) {
            return AppendResult.appended(expectedVersion);
        }
        try {
            return inUnitOfWork(() -> {
                int version = expectedVersion;
                for (DomainEvent event : events) {
                    int guardAgainst = version;
                    version++;
                    insert(streamId, version, guardAgainst, event);
                }
                return AppendResult.appended(version);
            });
        } catch (Refused refused) {
            // A conflict is a value rather than an exception, because contention is expected under load,
            // not exceptional. The transaction has already unwound.
            return AppendResult.versionConflict(currentVersion(streamId));
        } catch (EventStoreException failure) {
            // The unique constraint caught what the guard could not. On SQLite that is close to
            // unreachable — one writer at a time — but it is reported the way Postgres reports it, so
            // moving to Postgres is a change of adapter rather than of caller.
            if (failure.getCause() instanceof SQLException sql && isConstraintViolation(sql)) {
                return AppendResult.versionConflict(currentVersion(streamId));
            }
            throw failure;
        }
    }

    @Override
    public void readAll(long fromPosition, EventVisitor visit) {
        String query = "SELECT " + EVENT_COLUMNS
                + " FROM events WHERE global_position >= ? ORDER BY global_position ASC LIMIT ?";
        long position = fromPosition;
        while (true) {
            List<CommittedEvent> batch = new ArrayList<>();
            try (PreparedStatement statement = connection.prepareStatement(query)) {
                statement.setLong(1, position);
                statement.setInt(2, READ_ALL_BATCH_SIZE);
                try (ResultSet rows = statement.executeQuery()) {
                    while (rows.next()) {
                        batch.add(scanEvent(rows));
                    }
                }
            } catch (SQLException failure) {
                throw new EventStoreException("replay from " + position, failure);
            }
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
     * Write one event, plus its tags, inside whatever transaction is open.
     *
     * <p>The tags go in here rather than in a pass of their own, which is the whole design: an index
     * written after the append could be missing when the next conditional append checks it, and that append
     * would then be guarded by a boundary with a hole in it.
     */
    private void insert(String streamId, int version, int guardAgainst, DomainEvent event) {
        if (insertGuarded(streamId, version, guardAgainst, event) == 0) {
            throw new Refused();
        }
        long position = lastPosition();
        for (String tag : tagsOf.tagsOf(event.inStream(streamId))) {
            try (PreparedStatement statement = connection.prepareStatement(INSERT_TAG)) {
                statement.setString(1, tag);
                statement.setLong(2, position);
                statement.executeUpdate();
            } catch (SQLException failure) {
                throw new EventStoreException("index " + tag, failure);
            }
        }
    }

    private long lastPosition() {
        try (Statement statement = connection.createStatement();
                ResultSet rows = statement.executeQuery(LAST_POSITION)) {
            return rows.next() ? rows.getLong(1) : 0;
        } catch (SQLException failure) {
            throw new EventStoreException("read the last inserted position", failure);
        }
    }

    private int insertGuarded(String streamId, int version, int guardAgainst, DomainEvent event) {
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
            return statement.executeUpdate();
        } catch (SQLException failure) {
            throw new EventStoreException("append to " + streamId, failure);
        }
    }

    @Override
    public long head() {
        return headOfTheLog();
    }

    @Override
    public TaggedRead readTagged(TagQuery query, long after, long until) {
        Predicate predicate = tagQuerySql(query);
        long ceiling = until == 0 ? headOfTheLog() : until;
        String sql = "SELECT " + EVENT_COLUMNS + " FROM events e WHERE e.global_position > ?"
                + " AND e.global_position <= ? AND " + predicate.sql()
                + " ORDER BY e.global_position ASC";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, after);
            statement.setLong(2, ceiling);
            predicate.bind(statement, 3);
            try (ResultSet rows = statement.executeQuery()) {
                List<CommittedEvent> found = new ArrayList<>();
                while (rows.next()) {
                    found.add(scanEvent(rows));
                }
                return new TaggedRead(found, ceiling);
            }
        } catch (SQLException failure) {
            throw new EventStoreException("read by tag query", failure);
        }
    }

    /**
     * The conditional append. SQLite gives the isolation for free.
     *
     * <p>The transaction takes the write lock before the condition is checked and holds it through the
     * inserts, and SQLite has one writer at a time, so the check and the write cannot be split by another
     * transaction. Postgres has to ask for SERIALIZABLE to get the same thing, and pays for it with a retry
     * path; here there is nothing to retry.
     */
    @Override
    public ConditionalAppendResult appendIf(Condition condition, List<DomainEvent> events) {
        try {
            return inUnitOfWork(() -> {
                if (anythingMatching(condition)) {
                    throw new Refused();
                }
                for (DomainEvent event : events) {
                    // Each event still lands at the next version of the stream it names, so everything
                    // written against read and append keeps working: what the condition replaced is the
                    // guard, not the shape of the log.
                    int at = currentVersion(event.streamId());
                    insert(event.streamId(), at + 1, at, event);
                }
                return ConditionalAppendResult.recorded(head());
            });
        } catch (Refused refused) {
            return ConditionalAppendResult.conditionConflict(head());
        }
    }

    @Override
    public int reindexTags(long fromPosition) {
        return inUnitOfWork(() -> {
            List<CommittedEvent> unindexed = new ArrayList<>();
            try (PreparedStatement statement = connection.prepareStatement(UNINDEXED_EVENTS)) {
                statement.setLong(1, fromPosition);
                try (ResultSet rows = statement.executeQuery()) {
                    while (rows.next()) {
                        unindexed.add(scanEvent(rows));
                    }
                }
            } catch (SQLException failure) {
                throw new EventStoreException("read the unindexed events", failure);
            }
            int written = 0;
            for (CommittedEvent event : unindexed) {
                List<String> tags = tagsOf.tagsOf(event.event());
                if (tags.isEmpty()) {
                    // Counted only when it made the event findable. An event this project's tagging
                    // function has nothing to say about stays unindexed for good, so a run that counted
                    // it would promise an index with nothing in it and never settle at zero.
                    continue;
                }
                for (String tag : tags) {
                    try (PreparedStatement statement = connection.prepareStatement(INSERT_TAG)) {
                        statement.setString(1, tag);
                        statement.setLong(2, event.globalPosition());
                        statement.executeUpdate();
                    } catch (SQLException failure) {
                        throw new EventStoreException("index " + tag, failure);
                    }
                }
                written++;
            }
            return written;
        });
    }

    @Override
    public int retag(TagsOf next) {
        return inUnitOfWork(() -> {
            tagsOf = next;
            execute(DELETE_TAGS);
            // Inside this unit of work, so the old index is never visible as gone: either the whole
            // re-index commits or the old one stands.
            return reindexTags(0);
        });
    }

    private boolean anythingMatching(Condition condition) {
        Predicate predicate = tagQuerySql(condition.query());
        String sql = "SELECT 1 FROM events e WHERE e.global_position > ? AND " + predicate.sql()
                + " LIMIT 1";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setLong(1, condition.after());
            predicate.bind(statement, 2);
            try (ResultSet rows = statement.executeQuery()) {
                return rows.next();
            }
        } catch (SQLException failure) {
            throw new EventStoreException("check a condition", failure);
        }
    }

    private long headOfTheLog() {
        try (Statement statement = connection.createStatement();
                ResultSet rows = statement.executeQuery(STORE_HEAD)) {
            return rows.next() ? rows.getLong(1) : 0;
        } catch (SQLException failure) {
            throw new EventStoreException("read the store head", failure);
        }
    }

    /**
     * A tag query as a SQL predicate over {@code e}, plus the arguments it binds.
     *
     * <p>{@code TagQuery.Filter.matches} in the port is the definition; this is a translation of it, and
     * the contract suite is what holds the two to each other. Every branch here has a case there:
     *
     * <ul>
     *   <li>a filter's tags are a <strong>conjunction</strong>, so the count of its tags found against the
     *       event must equal how many it named — {@code IN} alone would be an "any of", which is a
     *       different and much weaker guard;
     *   <li>a filter's types narrow within that filter, never across the query;
     *   <li>a filter naming neither matches nothing, and a query with no filters matches nothing.
     *       {@code 1 = 0} rather than an omitted predicate, because an absent guard would match everything
     *       and a conditional append that matched everything would refuse every write in the system.
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
        return String.join(", ", java.util.Collections.nCopies(count, "?"));
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
     * half-written append it is refusing.
     */
    private static final class Refused extends RuntimeException {

        private static final long serialVersionUID = 1L;

        Refused() {
            super("refused", null, false, false);
        }
    }

    private int currentVersion(String streamId) {
        try (PreparedStatement statement = connection.prepareStatement(CURRENT_VERSION)) {
            statement.setString(1, streamId);
            try (ResultSet rows = statement.executeQuery()) {
                return rows.next() ? rows.getInt(1) : EventStore.NO_STREAM;
            }
        } catch (SQLException failure) {
            throw new EventStoreException("read current version of " + streamId, failure);
        }
    }

    private static boolean isConstraintViolation(SQLException failure) {
        // Matched on the message rather than a typed code: the driver reports a constraint failure as a
        // plain SQLException, and the alternative is importing driver internals into an adapter that has no
        // other reason to know which driver it is using.
        String message = failure.getMessage();
        return message != null && message.contains("constraint failed");
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
     * <p>Events are validated on read as well as on write, because stored events outlive the code that
     * wrote them — a compile-time type says nothing about a row written eighteen months ago. This is a
     * tolerant reader on purpose: unknown payload fields written by a newer version are carried through
     * rather than rejected, which is what makes a rolling deploy possible. Only the envelope itself is
     * required.
     */
    private static CommittedEvent scanEvent(ResultSet row) throws SQLException {
        long globalPosition = row.getLong("global_position");
        int schemaVersion = row.getInt("schema_version");
        if (schemaVersion != 1) {
            throw new EventStoreException("event at global_position " + globalPosition
                    + " is schema version " + schemaVersion
                    + "; add an upcaster for it before reading it as version 1");
        }
        Map<String, Object> payload = decodePayload(globalPosition, row.getString("payload"));
        Actor actor = decodeActor(globalPosition, row.getString("actor"));
        String causationId = row.getString("causation_id");
        DomainEvent event = new DomainEvent(
                row.getString("event_type"),
                schemaVersion,
                row.getString("stream_id"),
                payload,
                row.getString("occurred_at"),
                actor,
                // Parsed rather than passed through, so a row SQLite was happy to store cannot enter the
                // domain as an identifier nothing can correlate.
                CorrelationId.of(row.getString("correlation_id")),
                Optional.ofNullable(causationId).map(CausationId::of));
        return new CommittedEvent(
                event, row.getInt("version"), globalPosition, row.getString("recorded_at"));
    }

    private static Map<String, Object> decodePayload(long globalPosition, String encoded) {
        try {
            return JSON.readValue(encoded, new TypeReference<Map<String, Object>>() {});
        } catch (JsonProcessingException failure) {
            throw new EventStoreException(
                    "event at global_position " + globalPosition + " has an unreadable payload", failure);
        }
    }

    private static Actor decodeActor(long globalPosition, String encoded) {
        Map<String, Object> decoded = decodePayload(globalPosition, encoded);
        Object kind = decoded.get("kind");
        if (kind == null || kind.toString().isEmpty()) {
            throw new EventStoreException(
                    "event at global_position " + globalPosition + " has no usable actor");
        }
        Object id = decoded.get("id");
        return new Actor(kind.toString(), id == null ? "" : id.toString());
    }
}
