package com.example.deliverystarter.adapters.driven.checkpointstorepostgres;

import com.example.deliverystarter.adapters.driven.sql.Transactions;
import com.example.deliverystarter.application.ports.readmodels.CheckpointStore;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Timestamp;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;

/**
 * The Postgres checkpoint store, in the same transaction as the events it accounts for.
 *
 * <p>Built from {@link Transactions} rather than from a {@code DataSource}, and that is the point:
 * {@code record} has to commit in the same transaction as the view rows it accounts for. A second pool
 * connection is a second transaction, and a checkpoint in its own transaction is a race with a number in
 * it — either the view is written and the checkpoint is lost, or the checkpoint moves past rows that were
 * rolled back. Because the framework's transaction manager is what answers "which connection", handing
 * this adapter the same bean the event store has is all it takes; so does a project's own repository,
 * without being told.
 *
 * <p>The claim is <strong>one statement</strong>. An {@code INSERT ... ON CONFLICT DO UPDATE ... WHERE}
 * decides whether the lease is takeable and takes it in the same breath, so there is no window between
 * reading who holds it and writing that you do. {@code make test-integration} is where two connections race
 * for it for real, which is the one thing no single-writer store — an in-memory fake, a file-backed
 * one — can prove.
 */
public final class PostgresCheckpointStore implements CheckpointStore {

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
                SET position = EXCLUDED.position, updated_at = now()
            """;

    /**
     * Take the lease when nobody holds it, when this owner already holds it (which is how a long catch-up
     * renews), or when the holder's has lapsed. Refuse otherwise — and the refusal is the {@code WHERE} on
     * the update, so the whole decision is one statement and cannot be split by another worker doing the
     * same thing a microsecond later.
     */
    private static final String CLAIM_LEASE = """
              INSERT INTO projection_checkpoints (projection, position, lease_owner, lease_expires_at)
              VALUES (?, 0, ?, ?)
              ON CONFLICT (projection) DO UPDATE
                SET lease_owner = EXCLUDED.lease_owner,
                    lease_expires_at = EXCLUDED.lease_expires_at
                WHERE projection_checkpoints.lease_owner IS NULL
                   OR projection_checkpoints.lease_owner = EXCLUDED.lease_owner
                   OR projection_checkpoints.lease_expires_at <= ?
            """;

    private static final String RELEASE_LEASE = """
              UPDATE projection_checkpoints
              SET lease_owner = NULL, lease_expires_at = NULL
              WHERE projection = ? AND lease_owner = ?
            """;

    private final Transactions transactions;

    /** Take the framework's transactions, the same ones the event store was given. */
    public PostgresCheckpointStore(Transactions transactions) {
        this.transactions = transactions;
    }

    @Override
    public long positionOf(String projection) {
        return transactions.onConnection("read the position of " + projection, connection -> {
            try (PreparedStatement statement = connection.prepareStatement(POSITION_OF)) {
                statement.setString(1, projection);
                try (ResultSet rows = statement.executeQuery()) {
                    return rows.next() ? rows.getLong(1) : FROM_THE_BEGINNING;
                }
            }
        });
    }

    /**
     * No commit here. Call it inside the store's unit of work, with the writes it accounts for; outside one
     * it takes a pool connection of its own and commits alone, which is the mistake this comment names.
     */
    @Override
    public void record(String projection, long position) {
        transactions.onConnection("record the position of " + projection, connection -> {
            try (PreparedStatement statement = connection.prepareStatement(RECORD_POSITION)) {
                statement.setString(1, projection);
                statement.setLong(2, position);
                statement.executeUpdate();
            }
            return Boolean.TRUE;
        });
    }

    @Override
    public Optional<Lease> claim(String projection, String owner, Instant now, Duration ttl) {
        Instant expiresAt = now.plus(ttl);
        boolean taken = transactions.inTransaction(Transactions.Isolation.DEFAULT, () ->
                transactions.onConnection("claim " + projection, connection -> {
                    try (PreparedStatement statement = connection.prepareStatement(CLAIM_LEASE)) {
                        statement.setString(1, projection);
                        statement.setString(2, owner);
                        statement.setTimestamp(3, Timestamp.from(expiresAt));
                        statement.setTimestamp(4, Timestamp.from(now));
                        return statement.executeUpdate() != 0;
                    }
                }));
        return taken ? Optional.of(new Lease(projection, owner, expiresAt)) : Optional.empty();
    }

    @Override
    public void release(Lease lease) {
        transactions.inTransaction(Transactions.Isolation.DEFAULT, () ->
                transactions.onConnection("release " + lease.projection(), connection -> {
                    try (PreparedStatement statement = connection.prepareStatement(RELEASE_LEASE)) {
                        statement.setString(1, lease.projection());
                        statement.setString(2, lease.owner());
                        statement.executeUpdate();
                    }
                    return Boolean.TRUE;
                }));
    }
}
