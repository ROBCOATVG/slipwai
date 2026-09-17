package com.example.deliverystarter.adapters.driven.checkpointstoresqlite;

import com.example.deliverystarter.adapters.driven.eventstoresqlite.SqliteEventStore;
import com.example.deliverystarter.checkpointstorecontract.CheckpointStoreContract;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.AfterEach;

/**
 * The checkpoint contract, against SQLite — one file, one connection, real transactions.
 *
 * <p>This is the cheapest place the transactional checkpoint is genuinely proved: the in-memory adapter
 * rolls back by restoring a copy, whereas here a failed unit of work is a real ROLLBACK issued by a real
 * database. {@code :memory:} because the contract is about behaviour and a fresh database per case is what
 * keeps the cases independent.
 */
class SqliteCheckpointStoreTest extends CheckpointStoreContract {

    private final List<SqliteEventStore> opened = new ArrayList<>();

    @AfterEach
    void closeWhatWasOpened() {
        opened.forEach(SqliteEventStore::close);
        opened.clear();
    }

    @Override
    protected Stores stores() {
        SqliteEventStore store = new SqliteEventStore(":memory:");
        opened.add(store);
        return new Stores(store, new SqliteCheckpointStore(store));
    }
}
