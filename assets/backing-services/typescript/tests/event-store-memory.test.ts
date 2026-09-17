import { createInMemoryEventStore } from '../../src/adapters/driven/event-store-memory.js';
import { defaultTagsOf } from '../../src/application/ports/events.js';
import { eventStoreContract } from './event-store-contract.js';

/**
 * The contract, against the fake. This runs in `make verify` and needs no Docker, which is the whole
 * reason the fake exists. `make test-integration` runs the same contract against Postgres.
 */
eventStoreContract('the in-memory event store', async (tagsOf = defaultTagsOf) =>
  createInMemoryEventStore(tagsOf),
);
