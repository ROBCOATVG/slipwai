package com.example.deliverystarter.adapters.driven.eventstoresqlite;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.deliverystarter.application.ports.events.AppendResult;
import com.example.deliverystarter.application.ports.events.CommittedEvent;
import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.events.TagsOf;
import com.example.deliverystarter.eventstorecontract.EventStoreContract;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The shared contract, against SQLite, plus the two things only a file-backed store can prove.
 *
 * <p>This runs in {@code make verify} and needs no Docker — an embedded database is created by the process
 * that opens it, so there is nothing to start and nothing to migrate.
 *
 * <p>{@code :memory:} for the contract, because the contract is about behaviour and a fresh database per
 * case is what keeps the cases independent.
 */
class SqliteEventStoreTest extends EventStoreContract {

    @TempDir
    Path directory;

    @Override
    protected EventStore newStore(TagsOf tagsOf) {
        return new SqliteEventStore(":memory:", tagsOf);
    }

    /** The whole reason to choose SQLite over the in-memory adapter. */
    @Test
    void keepsTheLogAcrossACloseAndReopen() {
        String location = directory.resolve("events.sqlite3").toString();

        try (SqliteEventStore first = new SqliteEventStore(location)) {
            first.append("order-1", EventStore.NO_STREAM, List.of(event("order-1", "Placed")));
        }

        try (SqliteEventStore reopened = new SqliteEventStore(location)) {
            List<CommittedEvent> recorded = reopened.read("order-1");

            assertThat(recorded).hasSize(1);
            assertThat(recorded.get(0).type()).isEqualTo("Placed");
            assertThat(recorded.get(0).version()).isZero();

            // A caller that has not noticed the restart is still refused, by the same rule as before it.
            assertThat(reopened.append(
                            "order-1", EventStore.NO_STREAM, List.of(event("order-1", "Raced"))))
                    .isEqualTo(AppendResult.versionConflict(0));
        }
    }

    /**
     * The append-only rule lives in the database, not in the adapter.
     *
     * <p>A rule the application enforces is a rule the next process to open the file — a migration script, a
     * {@code sqlite3} shell, a well-meaning fix in production — will not. So this test goes around the
     * adapter entirely and asks the database directly.
     */
    @Test
    void refusesToRewriteOrEraseWhatHasBeenRecorded() throws SQLException {
        String location = directory.resolve("events.sqlite3").toString();
        try (SqliteEventStore store = new SqliteEventStore(location)) {
            store.append("order-1", EventStore.NO_STREAM, List.of(event("order-1", "Placed")));
        }

        try (Connection raw = DriverManager.getConnection("jdbc:sqlite:" + location);
                Statement statement = raw.createStatement()) {
            for (String forbidden :
                    List.of("UPDATE events SET event_type = 'Rewritten'", "DELETE FROM events")) {
                assertThatThrownBy(() -> statement.executeUpdate(forbidden))
                        .as(forbidden)
                        .isInstanceOf(SQLException.class)
                        .hasMessageContaining("append-only");
            }
            assertThat(statement.executeQuery("SELECT event_type FROM events").getString(1))
                    .isEqualTo("Placed");
        }
    }
}
