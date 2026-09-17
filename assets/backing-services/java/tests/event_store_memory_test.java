package com.example.deliverystarter.adapters.driven.eventstorememory;

import com.example.deliverystarter.application.ports.events.EventStore;
import com.example.deliverystarter.application.ports.events.TagsOf;
import com.example.deliverystarter.eventstorecontract.EventStoreContract;

/**
 * The contract, against the fake.
 *
 * <p>This runs in {@code make verify} and needs no Docker, which is the whole reason the fake exists.
 * {@code make test-integration} runs the same contract against Postgres.
 */
class InMemoryEventStoreTest extends EventStoreContract {

    @Override
    protected EventStore newStore(TagsOf tagsOf) {
        return new InMemoryEventStore(tagsOf, new InMemoryDatabase());
    }
}
