package com.example.deliverystarter.adapters.driven.checkpointstoresqlite;

import com.example.deliverystarter.adapters.driven.eventstoresqlite.SqliteEventStore;
import com.example.deliverystarter.application.ports.events.EventStoreException;
import com.example.deliverystarter.application.ports.readmodels.CheckpointStore;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Optional;

/**
 * The SQLite checkpoint store, on the event store's own connection.
 *
 * <p>Built from the store rather than from a location, and that is the point: {@code record} has to commit
 * in the same transaction as the view rows it accounts for, so it has to be the same connection. Two
 * adapters opening the same file are two connections and two transactions, and a checkpoint in its own
 * transaction is a race with a number in it.
 *
 * <p>The lease is claimed inside the store's unit of work, which takes SQLite's single write lock, so the
 * read-then-write is atomic without anything clever. What SQLite cannot do here is prove that two
 * <em>processes</em> contend correctly, because it serialises them; {@code make test-integration} proves
 * that against Postgres.
 */
public final class SqliteCheckpointStore implements CheckpointStore {

    private static final String POSITION_OF =
            "SELECT position FROM projection_checkpoints WHERE projection = ?";

    /**
     * {@code updated_at} moves with the position, so "is this projection stuck" is answerable from the
     * table rather than from a log somewhere.
     */
    private static final String RECORD_POSITION = """
              INSERT INTO projection_checkpoints (projection, position)
              VALUES (?, ?)
              ON CONFLICT (projection) DO UPDATE
                SET position = excluded.position,
                    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            """;

    /**
     * Take the lease when nobody holds it, when this owner already holds it (which is how a long catch-up
     * renews), or when the holder's lease has lapsed. Refuse otherwise — and the refusal is the
     * {@code WHERE} on the update, so the whole decision is one statement and cannot be split.
     */
    private static final String CLAIM_LEASE = """
              INSERT INTO projection_checkpoints (projection, position, lease_owner, lease_expires_at)
              VALUES (?, 0, ?, ?)
              ON CONFLICT (projection) DO UPDATE
                SET lease_owner = excluded.lease_owner,
                    lease_expires_at = excluded.lease_expires_at
                WHERE projection_checkpoints.lease_owner IS NULL
                   OR projection_checkpoints.lease_owner = excluded.lease_owner
                   OR projection_checkpoints.lease_expires_at <= ?
            """;

    private static final String RELEASE_LEASE = """
              UPDATE projection_checkpoints
              SET lease_owner = NULL, lease_expires_at = NULL
              WHERE projection = ? AND lease_owner = ?
            """;

    /**
     * A fixed-width UTC instant, because SQLite compares these as strings.
     *
     * <p>Same width, same zone, always — that is what makes {@code lease_expires_at <= ?} a chronological
     * comparison rather than an alphabetical one that is right until an offset or a shorter fraction turns
     * up. Postgres has {@code timestamptz} and needs none of this; the adapter is where the difference
     * stops.
     */
    private static final DateTimeFormatter INSTANT =
            DateTimeFormatter.ofPattern("uuuu-MM-dd'T'HH:mm:ss.SSSSSSSSS'Z'").withZone(ZoneOffset.UTC);

    private final SqliteEventStore events;
    private final Connection connection;

    /** Take the event store's own connection, so both adapters are inside one unit of work. */
    public SqliteCheckpointStore(SqliteEventStore events) {
        this.events = events;
        this.connection = events.sharedConnection();
    }

    @Override
    public long positionOf(String projection) {
        try (PreparedStatement statement = connection.prepareStatement(POSITION_OF)) {
            statement.setString(1, projection);
            try (ResultSet rows = statement.executeQuery()) {
                return rows.next() ? rows.getLong(1) : FROM_THE_BEGINNING;
            }
        } catch (SQLException failure) {
            throw new EventStoreException("read the position of " + projection, failure);
        }
    }

    /**
     * No commit here. Call it inside the store's unit of work, with the writes it accounts for; outside
     * one, SQLite commits it on its own, which is the mistake this comment names.
     */
    @Override
    public void record(String projection, long position) {
        try (PreparedStatement statement = connection.prepareStatement(RECORD_POSITION)) {
            statement.setString(1, projection);
            statement.setLong(2, position);
            statement.executeUpdate();
        } catch (SQLException failure) {
            throw new EventStoreException("record the position of " + projection, failure);
        }
    }

    @Override
    public Optional<Lease> claim(String projection, String owner, Instant now, Duration ttl) {
        Instant expiresAt = now.plus(ttl);
        boolean taken = events.inUnitOfWork(() -> {
            try (PreparedStatement statement = connection.prepareStatement(CLAIM_LEASE)) {
                statement.setString(1, projection);
                statement.setString(2, owner);
                statement.setString(3, INSTANT.format(expiresAt));
                statement.setString(4, INSTANT.format(now));
                return statement.executeUpdate() != 0;
            } catch (SQLException failure) {
                throw new EventStoreException("claim " + projection, failure);
            }
        });
        return taken ? Optional.of(new Lease(projection, owner, expiresAt)) : Optional.empty();
    }

    @Override
    public void release(Lease lease) {
        events.inUnitOfWork(() -> {
            try (PreparedStatement statement = connection.prepareStatement(RELEASE_LEASE)) {
                statement.setString(1, lease.projection());
                statement.setString(2, lease.owner());
                statement.executeUpdate();
            } catch (SQLException failure) {
                throw new EventStoreException("release " + lease.projection(), failure);
            }
        });
    }
}
