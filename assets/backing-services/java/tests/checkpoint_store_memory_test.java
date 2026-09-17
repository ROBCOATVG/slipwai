package com.example.deliverystarter.adapters.driven.checkpointstorememory;

import com.example.deliverystarter.adapters.driven.eventstorememory.InMemoryEventStore;
import com.example.deliverystarter.checkpointstorecontract.CheckpointStoreContract;

/**
 * The checkpoint contract, against the fake.
 *
 * <p>Runs in {@code make verify} with no Docker, which is the whole reason the in-memory adapters exist.
 * What it cannot prove is two workers genuinely racing for one lease — this one serialises them — and
 * {@code make test-integration} is where that is proved.
 */
class InMemoryCheckpointStoreTest extends CheckpointStoreContract {

    @Override
    protected Stores stores() {
        InMemoryEventStore store = new InMemoryEventStore();
        return new Stores(store, new InMemoryCheckpointStore(store));
    }
}
